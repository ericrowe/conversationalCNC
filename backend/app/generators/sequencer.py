"""
Multi-Operation Job Program Sequencer / Builder Engine.
Bundles multiple conversational machining operations into a single cohesive, production-ready .nc job file.
Features:
- Single top-level safety header (G21 G90 G94 G17 G54) and program footer (M5, G0 Z, G0 XY, M2/M30)
- Intelligent Dependency-Safe Tool Change Optimization
- Safe inter-operation retract planes (G0 Z<safe_z> before M5) and manual router M0 pause safety
- Atomic failure on any invalid or unknown sub-operation (never emits partial executable G-code)
"""
import inspect
from typing import Dict, Any, List, Optional
from ..postprocessors import get_postprocessor
from ..postprocessors.router_speed_tables import is_manual_spindle
from .drilling import generate_straight_plunge, generate_peck_drilling, compute_grid_holes, compute_bolt_circle_holes
from .thread_milling import generate_helical_thread_milling
from .circular_pocket import generate_circular_pocket, generate_circular_boss
from .rectangular_pocket import generate_rectangular_pocket, generate_rectangular_boss
from .slotting import generate_linear_slot
from .chamfering import generate_rectangular_chamfer, generate_circular_chamfer
from .surfacing import generate_surfacing
from .engraving import generate_text_engraving
from .contouring import generate_contour_profile
from .base import strip_header_and_footer
from .mesh_leveling import WorkpieceMeshMap

_strip_header_and_footer = strip_header_and_footer

BARRIER_OP_TYPES = {"surfacing", "soft_jaw", "soft_jaw_fixture"}

GENERATOR_MAP = {
    "drilling": generate_straight_plunge,
    "straight_plunge": generate_straight_plunge,
    "peck_drilling": generate_peck_drilling,
    "thread_milling": generate_helical_thread_milling,
    "circular_pocket": generate_circular_pocket,
    "circular_boss": generate_circular_boss,
    "rectangular_pocket": generate_rectangular_pocket,
    "rectangular_boss": generate_rectangular_boss,
    "linear_slot": generate_linear_slot,
    "slotting": generate_linear_slot,
    "rectangular_chamfer": generate_rectangular_chamfer,
    "circular_chamfer": generate_circular_chamfer,
    "chamfering": generate_rectangular_chamfer,
    "surfacing": generate_surfacing,
    "engraving": generate_text_engraving,
    "contouring": generate_contour_profile,
    "profile": generate_contour_profile,
}


class SequenceGenerationError(ValueError):
    """Raised when any operation in a multi-operation sequence fails validation or generation."""

    def __init__(self, operation_index: int, op_name: str, op_type: str, reason: str):
        self.operation_index = operation_index
        self.op_name = op_name
        self.op_type = op_type
        self.reason = reason
        super().__init__(
            f"Operation {operation_index} ('{op_name}', type='{op_type}') failed: {reason}"
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "operation_index": self.operation_index,
            "op_name": self.op_name,
            "op_type": self.op_type,
            "reason": self.reason,
        }


def _order_operations_safely(operations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Reorders operations to minimize tool changes ONLY within dependency-safe boundaries:
    1. Stock-preparation barrier operations (e.g. 'surfacing', 'soft_jaw') and operations with
       'lock_order=True' or explicit 'depends_on' constraints act as ordering barriers so dependent
       operations are never hoisted ahead of stock preparation.
    2. Within each reorderable segment, operations are grouped by the order in which each tool
       first appears (rather than sorting by raw numeric tool_number T1 < T2), preserving the
       operator's primary tool progression while merging repeated uses of the same tool.
    """
    if len(operations) <= 1:
        return list(operations)

    # Check if any operation has explicit depends_on metadata
    if any(op.get("depends_on") is not None for op in operations):
        # Preserve strict topological order when explicit dependencies are declared
        return list(operations)

    segments: List[List[Dict[str, Any]]] = []
    current_segment: List[Dict[str, Any]] = []

    for op in operations:
        op_type = (op.get("op_type") or "drilling").lower().strip()
        is_barrier = op_type in BARRIER_OP_TYPES or bool(op.get("lock_order", False))
        if is_barrier:
            if current_segment:
                segments.append(current_segment)
                current_segment = []
            segments.append([op])
        else:
            current_segment.append(op)

    if current_segment:
        segments.append(current_segment)

    ordered: List[Dict[str, Any]] = []
    for seg in segments:
        if len(seg) <= 1:
            ordered.extend(seg)
        else:
            tool_first_seen: Dict[int, int] = {}
            for idx, item in enumerate(seg):
                t_num = int(item.get("tool_number", 1))
                if t_num not in tool_first_seen:
                    tool_first_seen[t_num] = idx
            ordered.extend(sorted(seg, key=lambda item: tool_first_seen[int(item.get("tool_number", 1))]))

    return ordered


def generate_job_sequence(
    job_name: str = "Multi-Op Job",
    operations: Optional[List[Dict[str, Any]]] = None,
    safe_z_retract: float = 5.0,
    units: str = "mm",
    dialect: str = "grbl",
    spindle_type: str = "router",
    router_model: Optional[str] = "dewalt_611",
    require_pause: bool = False,
    optimize_tool_order: bool = False,
    park_x: Optional[float] = 0.0,
    park_y: Optional[float] = 0.0,
    park_z: Optional[float] = 5.0,
    apply_mesh_leveling: bool = False,
    mesh_data: Optional[Dict[str, Any]] = None,
    mesh_max_segment_length: float = 3.0,
) -> Dict[str, Any]:
    """
    Stitches multiple conversational operations into a single unified .nc program.
    Supports dynamic workpiece surface mesh leveling across all follow-on operations.
    """
    if not operations:
        operations = []

    post = get_postprocessor(dialect)
    ops_to_process = list(operations)

    # CNC-011: Never silently ignore invalid mesh when mesh leveling is explicitly requested
    mesh_map_obj: Optional[WorkpieceMeshMap] = None
    if apply_mesh_leveling:
        if not mesh_data or not isinstance(mesh_data, dict) or not mesh_data.get("points"):
            raise ValueError(
                "Workpiece mesh leveling was requested (apply_mesh_leveling=True), "
                "but mesh_data with valid probe points was not provided."
            )
        try:
            mesh_map_obj = WorkpieceMeshMap(
                points=mesh_data["points"],
                shape_type=mesh_data.get("shape_type", "rectangle"),
                shape_meta=mesh_data.get("shape_meta", {}),
            )
        except Exception as exc:
            raise ValueError(f"Invalid workpiece surface mesh for leveling: {exc}") from exc

    if optimize_tool_order and len(ops_to_process) > 1:
        ops_to_process = _order_operations_safely(ops_to_process)

    full_lines: List[str] = []

    # 1. Top-Level Job Header
    job_comment = f"Job: {job_name} | {len(ops_to_process)} Operations"
    if mesh_map_obj:
        job_comment += f" | Mesh Leveling: ACTIVE ({mesh_map_obj.shape_type.upper()}, {len(mesh_map_obj.active_points)} pts)"

    header = post.format_header(
        units=units,
        absolute_mode=True,
        comment=job_comment,
    )
    full_lines.extend(header)
    if mesh_map_obj:
        full_lines.append(f"( Workpiece Surface Mesh Compensation: {mesh_map_obj.shape_type.upper()} )")
        full_lines.append(
            f"( Surface Elevation Span: {mesh_map_obj.z_min:+.3f}mm to {mesh_map_obj.z_max:+.3f}mm | Delta: {mesh_map_obj.z_span:.3f}mm )"
        )
    full_lines.append("")

    active_tool_number: Optional[int] = None
    active_spindle_rpm: Optional[int] = None
    tool_list: List[Dict[str, Any]] = []
    tool_change_count = 0

    all_holes = []
    all_pockets = []

    for idx, op in enumerate(ops_to_process, 1):
        op_name = op.get("op_name", f"Op {idx}")
        op_type = (op.get("op_type") or "drilling").lower().strip()
        t_num = int(op.get("tool_number", 1))
        t_name = op.get("tool_name", f"Tool T{t_num}")
        t_dia = float(op.get("tool_diameter", 3.175))
        rpm = int(op.get("spindle_speed", 16000))
        params = op.get("params", {}) or {}
        op_spindle_type = op.get("spindle_type") or spindle_type
        op_router_model = op.get("router_model") or router_model

        if not any(t["tool_number"] == t_num for t in tool_list):
            tool_list.append({"tool_number": t_num, "name": t_name, "diameter": t_dia})

        # Section Banner
        full_lines.append("( --------------------------------------------------- )")
        full_lines.append(f"( >>> OP {idx}/{len(ops_to_process)}: {op_name.upper()} [{op_type.upper()}] <<< )")
        full_lines.append(f"( Tool: T{t_num} ({t_name}) | Diameter: {t_dia:.3f}{units} )")
        full_lines.append("( --------------------------------------------------- )")

        # CNC-012: Safe Tool Change (retract Z BEFORE stopping spindle, and emit M0 pause on manual routers)
        if active_tool_number != t_num:
            tool_change_count += 1
            if active_tool_number is not None:
                full_lines.append(f"G0 Z{safe_z_retract:.3f} (Safe Retract for Tool Change)")
                full_lines.append("M5 (Spindle Stop for Tool Change)")
                if is_manual_spindle(op_spindle_type):
                    if park_x is not None or park_y is not None:
                        px = park_x if park_x is not None else 0.0
                        py = park_y if park_y is not None else 0.0
                        full_lines.append(f"G0 X{px:.3f} Y{py:.3f} (Park for Manual Tool Change)")
                    full_lines.append(
                        f"( MANUAL TOOL CHANGE: Switch OFF router, install T{t_num} [{t_name}], re-zero Z, switch ON router )"
                    )
                    full_lines.append(f"M0 (Pause for Manual Tool Change to T{t_num})")
                active_spindle_rpm = None

            tool_comments = post.format_tool_comment(t_num, t_name)
            full_lines.extend(tool_comments)
            active_tool_number = t_num

        # Spindle Speed Check
        if active_spindle_rpm != rpm:
            op_router_dial = op.get("router_dial")
            spindle_lines = post.format_spindle_start(
                rpm=rpm,
                clockwise=True,
                dwell_seconds=1.5,
                spindle_type=op_spindle_type,
                router_model=op_router_model,
                router_dial=op_router_dial,
                require_pause=require_pause,
            )
            full_lines.extend(spindle_lines)
            active_spindle_rpm = rpm

        # Generate or extract Operation Body (CNC-005: Fail atomically on any error)
        if "raw_gcode" in op and op["raw_gcode"]:
            op_lines = _strip_header_and_footer(op["raw_gcode"])
            if not op_lines:
                raise SequenceGenerationError(idx, op_name, op_type, "raw_gcode contained no executable motion lines.")
        else:
            gen_func = GENERATOR_MAP.get(op_type)
            if not gen_func and op_type in ("soft_jaw", "soft_jaw_fixture"):
                from .nesting import generate_soft_jaw_fixture
                gen_func = generate_soft_jaw_fixture

            if not gen_func:
                raise SequenceGenerationError(
                    idx, op_name, op_type, f"Unknown operation type '{op_type}'."
                )

            call_params = dict(params)
            call_params.setdefault("tool_number", t_num)
            call_params.setdefault("tool_name", t_name)
            call_params.setdefault("tool_diameter", t_dia)
            call_params.setdefault("spindle_speed", rpm)
            call_params.setdefault("units", units)
            call_params.setdefault("dialect", dialect)
            call_params.setdefault("safe_z_retract", safe_z_retract)

            # Normalize common conversational UI parameter aliases
            if "total_depth" in call_params and "total_depth_z" not in call_params and "target_depth_z" not in call_params:
                val = -abs(float(call_params["total_depth"]))
                call_params["total_depth_z"] = val
                call_params["target_depth_z"] = val
            if "target_depth" in call_params and "target_depth_z" not in call_params:
                call_params["target_depth_z"] = -abs(float(call_params["target_depth"]))
            if "depth_per_pass" in call_params and "stepdown_z" not in call_params:
                call_params["stepdown_z"] = abs(float(call_params["depth_per_pass"]))
            if op_type in ("circular_pocket", "circular_boss") and "pockets" not in call_params:
                if "center_x" in call_params or "center_y" in call_params:
                    call_params["pockets"] = [(float(call_params.get("center_x", 0.0)), float(call_params.get("center_y", 0.0)))]
                elif "diameter" in call_params:
                    call_params["pockets"] = [(0.0, 0.0)]
                if "diameter" in call_params and "pocket_diameter" not in call_params:
                    call_params["pocket_diameter"] = float(call_params["diameter"])
            if op_type in ("drilling", "straight_plunge", "peck_drilling") and "holes" not in call_params:
                pat = (call_params.get("hole_pattern_type") or "").lower()
                if pat == "grid":
                    call_params["holes"] = compute_grid_holes(
                        origin_x=float(call_params.get("origin_x", call_params.get("start_x", 0.0))),
                        origin_y=float(call_params.get("origin_y", call_params.get("start_y", 0.0))),
                        num_x=int(call_params.get("grid_cols", call_params.get("num_x", 2))),
                        num_y=int(call_params.get("grid_rows", call_params.get("num_y", 2))),
                        spacing_x=float(call_params.get("grid_spacing_x", call_params.get("spacing_x", 10.0))),
                        spacing_y=float(call_params.get("grid_spacing_y", call_params.get("spacing_y", 10.0))),
                    )
                elif pat in ("bolt_circle", "pcd"):
                    call_params["holes"] = compute_bolt_circle_holes(
                        center_x=float(call_params.get("center_x", 0.0)),
                        center_y=float(call_params.get("center_y", 0.0)),
                        diameter=float(call_params.get("pcd_diameter", call_params.get("diameter", 20.0))),
                        num_holes=int(call_params.get("num_holes", 4)),
                    )
            if op_type in ("linear_slot", "slotting") and "slot_width" not in call_params:
                call_params["slot_width"] = float(call_params.get("tool_diameter", t_dia))
            if op_type == "thread_milling":
                if "nominal_diameter" in call_params and "major_diameter" not in call_params:
                    call_params["major_diameter"] = float(call_params["nominal_diameter"])
                if "thread_length" in call_params and "target_depth_z" not in call_params:
                    call_params["target_depth_z"] = -abs(float(call_params["thread_length"]))

            sig = inspect.signature(gen_func)
            accepted_keys = set(sig.parameters.keys())
            has_var_kw = any(p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values())

            if not has_var_kw:
                filtered_params = {k: v for k, v in call_params.items() if k in accepted_keys}
            else:
                filtered_params = call_params

            if "retract_z" in accepted_keys and "retract_z" not in filtered_params and "safe_z_retract" in call_params:
                filtered_params["retract_z"] = call_params["safe_z_retract"]

            try:
                op_result = gen_func(**filtered_params)
            except Exception as exc:
                raise SequenceGenerationError(idx, op_name, op_type, str(exc)) from exc

            if hasattr(op_result, "gcode"):
                raw_gc = op_result.gcode
            elif isinstance(op_result, dict):
                raw_gc = op_result.get("gcode", "")
            else:
                raw_gc = ""

            if not raw_gc or not isinstance(raw_gc, str):
                raise SequenceGenerationError(
                    idx, op_name, op_type, "Generator returned empty or malformed G-code."
                )

            op_lines = _strip_header_and_footer(raw_gc)
            if not op_lines:
                raise SequenceGenerationError(
                    idx, op_name, op_type, "Operation produced no motion lines after header/footer stripping."
                )

            if isinstance(op_result, dict):
                if "holes" in op_result:
                    all_holes.extend(op_result["holes"])
                if "pockets" in op_result:
                    all_pockets.extend(op_result["pockets"])

        # Apply workpiece surface mesh warping if active
        if mesh_map_obj and op_lines:
            op_raw_str = "\n".join(op_lines)
            warped_str = mesh_map_obj.warp_gcode(op_raw_str, max_segment_length=mesh_max_segment_length)
            op_lines = warped_str.splitlines()

        full_lines.extend(op_lines)
        full_lines.append(f"G0 Z{safe_z_retract:.3f} (End of Op {idx} Retract)")
        full_lines.append("")

    # 3. Final Unified Program Footer
    footer = post.format_footer(park_z=park_z, park_x=park_x, park_y=park_y)
    full_lines.extend(footer)

    full_gcode = "\n".join(full_lines)

    return {
        "job_name": job_name,
        "operation_count": len(ops_to_process),
        "tool_change_count": tool_change_count,
        "tools_used": tool_list,
        "gcode": full_gcode,
        "line_count": len(full_lines),
        "holes": all_holes,
        "pockets": all_pockets,
        "mesh_leveling_applied": mesh_map_obj is not None,
        "mesh_summary": mesh_map_obj.to_dict() if mesh_map_obj else None,
    }
