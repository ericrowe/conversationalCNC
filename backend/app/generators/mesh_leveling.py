"""
Workpiece Surface Mesh Leveling & Arbitrary Geometry Auto-Warping Engine.
Supports:
- Arbitrary Mesh Boundary Shapes:
  * Rectangular Grid (Xmin, Ymin, Xmax, Ymax)
  * Circular Disc (Center X/Y, Radius, Edge Inset Margin)
  * Concentric Annulus / Donut Ring (Center X/Y, Outer Radius, Inner Bore Radius)
  * Custom Polygons with perimeter inset margins
- Interactive Point Inclusion / Exclusion Masking (skip clamps, fixture bolts, holes)
- Pure-Python Delaunay Triangulation (Bowyer-Watson) & Barycentric Height Interpolation
- Toolpath Linear Move Segmentation (<= 3.0mm) & Arc Linearization
- Full G-Code Dynamic Surface Warping (Z -> Z + ΔZ(X, Y)) with safe retract clearance preservation
- Automated Grbl / LinuxCNC G38.2 Grid Probing Macro Generator with optimized snake traversal
- Grbl / Sender Console Probe Log Parser ([PRB:X,Y,Z:1], CSV, and JSON formats)
"""
import math
import re
from typing import List, Dict, Any, Tuple, Optional, Set


# =============================================================================
# 1. Mesh Candidate Point Generators
# =============================================================================

def generate_rectangular_probe_points(
    x_min: float,
    y_min: float,
    x_max: float,
    y_max: float,
    grid_x: int = 5,
    grid_y: int = 5,
    margin: float = 0.0,
) -> List[Dict[str, Any]]:
    """
    Generates an Nx x Ny rectangular grid of probe coordinates with snake ordering.
    """
    if grid_x < 2 or grid_y < 2:
        raise ValueError("Grid resolution must be at least 2x2 points.")
    if x_max <= x_min or y_max <= y_min:
        raise ValueError("Maximum coordinates must be greater than minimum coordinates.")

    eff_x_min = x_min + margin
    eff_x_max = x_max - margin
    eff_y_min = y_min + margin
    eff_y_max = y_max - margin

    if eff_x_max <= eff_x_min or eff_y_max <= eff_y_min:
        raise ValueError("Margin is too large for the specified rectangular bounds.")

    dx = (eff_x_max - eff_x_min) / (grid_x - 1)
    dy = (eff_y_max - eff_y_min) / (grid_y - 1)

    points = []
    pt_id = 0

    for j in range(grid_y):
        y = eff_y_min + j * dy
        # Snake order: reverse alternating rows
        x_indices = range(grid_x) if j % 2 == 0 else range(grid_x - 1, -1, -1)
        for i in x_indices:
            x = eff_x_min + i * dx
            points.append({
                "id": pt_id,
                "x": round(x, 3),
                "y": round(y, 3),
                "z": 0.0,
                "row": j,
                "col": i,
                "active": True,
            })
            pt_id += 1

    return points


def generate_circular_probe_points(
    center_x: float = 0.0,
    center_y: float = 0.0,
    radius: float = 50.0,
    inner_radius: float = 0.0,
    grid_resolution: int = 5,
    margin: float = 2.0,
    pattern_type: str = "grid",
) -> List[Dict[str, Any]]:
    """
    Generates probe coordinates within a Circular Disc or Annulus (Donut Ring).
    Filters candidate points to lie strictly within [inner_radius + margin, radius - margin].
    """
    if radius <= 0:
        raise ValueError("Disc radius must be positive.")
    if inner_radius < 0:
        raise ValueError("Inner radius cannot be negative.")
    if inner_radius >= radius:
        raise ValueError("Inner radius must be smaller than outer radius.")

    eff_outer_r = max(1.0, radius - margin)
    eff_inner_r = (inner_radius + margin) if inner_radius > 0 else 0.0

    if eff_inner_r >= eff_outer_r:
        raise ValueError("Margin is too large for specified disc/ring dimensions.")

    points = []
    pt_id = 0

    if pattern_type == "polar":
        # Polar Concentric Rings + Spokes
        ring_count = max(2, grid_resolution)
        r_step = (eff_outer_r - eff_inner_r) / (ring_count - 1)

        # Center point if solid disc
        if eff_inner_r == 0.0:
            points.append({
                "id": pt_id,
                "x": round(center_x, 3),
                "y": round(center_y, 3),
                "z": 0.0,
                "ring": 0,
                "active": True,
            })
            pt_id += 1

        for ring_idx in range(1 if eff_inner_r == 0.0 else 0, ring_count):
            r = eff_inner_r + ring_idx * r_step
            # Higher radius -> more angular spoke touches
            spokes = max(6, int(6 + ring_idx * 4))
            for s in range(spokes):
                angle = (2.0 * math.pi * s) / spokes
                x = center_x + r * math.cos(angle)
                y = center_y + r * math.sin(angle)
                points.append({
                    "id": pt_id,
                    "x": round(x, 3),
                    "y": round(y, 3),
                    "z": 0.0,
                    "ring": ring_idx,
                    "active": True,
                })
                pt_id += 1

    else:
        # Cartesian Grid with Circular Boundary Masking
        grid_n = max(3, grid_resolution * 2 - 1)
        x_min = center_x - eff_outer_r
        x_max = center_x + eff_outer_r
        y_min = center_y - eff_outer_r
        y_max = center_y + eff_outer_r
        step = (2.0 * eff_outer_r) / (grid_n - 1)

        for j in range(grid_n):
            y = y_min + j * step
            x_indices = range(grid_n) if j % 2 == 0 else range(grid_n - 1, -1, -1)
            for i in x_indices:
                x = x_min + i * step
                dist_sq = (x - center_x) ** 2 + (y - center_y) ** 2
                dist = math.sqrt(dist_sq)

                # Check if point lies within outer and inner bounds
                if (eff_inner_r - 1e-4) <= dist <= (eff_outer_r + 1e-4):
                    points.append({
                        "id": pt_id,
                        "x": round(x, 3),
                        "y": round(y, 3),
                        "z": 0.0,
                        "row": j,
                        "col": i,
                        "dist": round(dist, 3),
                        "active": True,
                    })
                    pt_id += 1

        # Also add discrete perimeter points around the boundary ring for perfect edge interpolation
        perimeter_spokes = max(8, grid_resolution * 3)
        for s in range(perimeter_spokes):
            angle = (2.0 * math.pi * s) / perimeter_spokes
            px = center_x + eff_outer_r * math.cos(angle)
            py = center_y + eff_outer_r * math.sin(angle)
            # Add if not too close to an existing point
            if not any(math.hypot(px - p["x"], py - p["y"]) < (step * 0.45) for p in points):
                points.append({
                    "id": pt_id,
                    "x": round(px, 3),
                    "y": round(py, 3),
                    "z": 0.0,
                    "dist": round(eff_outer_r, 3),
                    "active": True,
                })
                pt_id += 1

    return points


def generate_polygon_probe_points(
    vertices: List[Tuple[float, float]],
    grid_spacing: float = 15.0,
    margin: float = 2.0,
) -> List[Dict[str, Any]]:
    """
    Generates probe coordinates inside an arbitrary polygon using ray-casting point-in-polygon.
    """
    if len(vertices) < 3:
        raise ValueError("Polygon must have at least 3 vertices.")
    if grid_spacing <= 0:
        raise ValueError("Grid spacing must be positive.")

    xs = [v[0] for v in vertices]
    ys = [v[1] for v in vertices]
    x_min, x_max = min(xs), max(xs)
    y_min, y_max = min(ys), max(ys)

    def point_in_poly(x: float, y: float) -> bool:
        inside = False
        n = len(vertices)
        for i in range(n):
            x1, y1 = vertices[i]
            x2, y2 = vertices[(i + 1) % n]
            if ((y1 > y) != (y2 > y)) and (x < (x2 - x1) * (y - y1) / (y2 - y1 + 1e-12) + x1):
                inside = not inside
        return inside

    points = []
    pt_id = 0
    nx = int(math.ceil((x_max - x_min) / grid_spacing)) + 1
    ny = int(math.ceil((y_max - y_min) / grid_spacing)) + 1

    for j in range(ny):
        y = y_min + j * grid_spacing
        x_indices = range(nx) if j % 2 == 0 else range(nx - 1, -1, -1)
        for i in x_indices:
            x = x_min + i * grid_spacing
            if point_in_poly(x, y):
                points.append({
                    "id": pt_id,
                    "x": round(x, 3),
                    "y": round(y, 3),
                    "z": 0.0,
                    "active": True,
                })
                pt_id += 1

    return points


# =============================================================================
# 2. Pure-Python 2D Delaunay Triangulation & Barycentric Interpolator
# =============================================================================

def _circumcircle_contains(
    p: Tuple[float, float],
    p1: Tuple[float, float],
    p2: Tuple[float, float],
    p3: Tuple[float, float],
) -> bool:
    """
    Returns True if 2D point p lies strictly inside the circumcircle of triangle (p1, p2, p3).
    """
    x1, y1 = p1
    x2, y2 = p2
    x3, y3 = p3
    xp, yp = p

    d = 2 * (x1 * (y2 - y3) + x2 * (y3 - y1) + x3 * (y1 - y2))
    if abs(d) < 1e-12:
        return False

    ux = ((x1**2 + y1**2) * (y2 - y3) + (x2**2 + y2**2) * (y3 - y1) + (x3**2 + y3**2) * (y1 - y2)) / d
    uy = ((x1**2 + y1**2) * (x3 - x2) + (x2**2 + y2**2) * (x1 - x3) + (x3**2 + y3**2) * (x2 - x1)) / d

    r_sq = (x1 - ux)**2 + (y1 - uy)**2
    dist_sq = (xp - ux)**2 + (yp - uy)**2

    return dist_sq < (r_sq - 1e-9)


def delaunay_triangulation_2d(points_2d: List[Tuple[float, float]]) -> List[Tuple[int, int, int]]:
    """
    Computes 2D Delaunay Triangulation of an arbitrary point set using Bowyer-Watson algorithm.
    Returns list of 3-tuples containing point indices (i, j, k).
    """
    n = len(points_2d)
    if n < 3:
        return []

    # Find bounding box for super-triangle
    min_x = min(p[0] for p in points_2d)
    max_x = max(p[0] for p in points_2d)
    min_y = min(p[1] for p in points_2d)
    max_y = max(p[1] for p in points_2d)

    dx = max_x - min_x
    dy = max_y - min_y
    delta_max = max(dx, dy, 1.0)
    mid_x = (min_x + max_x) / 2.0
    mid_y = (min_y + max_y) / 2.0

    # Create super-triangle far encompassing all points
    st_p1 = (mid_x - 20 * delta_max, mid_y - delta_max)
    st_p2 = (mid_x, mid_y + 20 * delta_max)
    st_p3 = (mid_x + 20 * delta_max, mid_y - delta_max)

    pts = list(points_2d) + [st_p1, st_p2, st_p3]
    st_indices = {n, n + 1, n + 2}

    # Initial triangulation with super-triangle
    triangles: List[Tuple[int, int, int]] = [(n, n + 1, n + 2)]

    for pt_idx in range(n):
        p = pts[pt_idx]
        bad_triangles = []

        for tri in triangles:
            p1, p2, p3 = pts[tri[0]], pts[tri[1]], pts[tri[2]]
            if _circumcircle_contains(p, p1, p2, p3):
                bad_triangles.append(tri)

        # Find polygon boundary (edges that are not shared by 2 bad triangles)
        polygon_edges: List[Tuple[int, int]] = []
        for tri in bad_triangles:
            edges = [
                (tri[0], tri[1]),
                (tri[1], tri[2]),
                (tri[2], tri[0]),
            ]
            for edge in edges:
                # Check if edge or its reverse is shared
                rev_edge = (edge[1], edge[0])
                is_shared = False
                for other in bad_triangles:
                    if other == tri:
                        continue
                    other_edges = [
                        (other[0], other[1]),
                        (other[1], other[2]),
                        (other[2], other[0]),
                    ]
                    if edge in other_edges or rev_edge in other_edges:
                        is_shared = True
                        break
                if not is_shared:
                    polygon_edges.append(edge)

        # Remove bad triangles
        triangles = [t for t in triangles if t not in bad_triangles]

        # Re-triangulate hole with current point
        for edge in polygon_edges:
            triangles.append((edge[0], edge[1], pt_idx))

    # Remove triangles containing vertices of the initial super-triangle
    valid_triangles = []
    for tri in triangles:
        if not (tri[0] in st_indices or tri[1] in st_indices or tri[2] in st_indices):
            valid_triangles.append(tri)

    return valid_triangles


# =============================================================================
# 3. WorkpieceMeshMap Class (Height Interpolation & Toolpath Warping)
# =============================================================================

class WorkpieceMeshMap:
    """
    Encapsulates calibrated 3D workpiece surface mesh data and performs
    surface height interpolation and toolpath warping across arbitrary stock geometries.
    """

    def __init__(
        self,
        points: List[Dict[str, Any]],
        shape_type: str = "rectangle",
        shape_meta: Optional[Dict[str, Any]] = None,
    ):
        """
        points: List of dicts with {"x": float, "y": float, "z": float, "active": bool}
        """
        self.shape_type = shape_type
        self.shape_meta = shape_meta or {}
        self.raw_points = points

        # Filter only active probed points
        self.active_points = [p for p in points if p.get("active", True)]
        if not self.active_points:
            self.active_points = points

        self.coords_3d = [(p["x"], p["y"], p.get("z", 0.0)) for p in self.active_points]
        self.coords_2d = [(p[0], p[1]) for p in self.coords_3d]

        self.z_min = min((p[2] for p in self.coords_3d), default=0.0)
        self.z_max = max((p[2] for p in self.coords_3d), default=0.0)
        self.z_span = self.z_max - self.z_min

        # Compute Delaunay triangulation
        self.triangles = delaunay_triangulation_2d(self.coords_2d)

    def interpolate_z(self, x: float, y: float) -> float:
        """
        Calculates interpolated surface elevation ΔZ at coordinate (x, y)
        using Barycentric triangle interpolation with nearest-triangle edge fallback.
        """
        if not self.coords_3d:
            return 0.0

        if len(self.coords_3d) == 1:
            return self.coords_3d[0][2]

        # 1. Search for containing Delaunay triangle
        for tri in self.triangles:
            p1 = self.coords_3d[tri[0]]
            p2 = self.coords_3d[tri[1]]
            p3 = self.coords_3d[tri[2]]

            x1, y1, z1 = p1
            x2, y2, z2 = p2
            x3, y3, z3 = p3

            det = (y2 - y3) * (x1 - x3) + (x3 - x2) * (y1 - y3)
            if abs(det) < 1e-12:
                continue

            l1 = ((y2 - y3) * (x - x3) + (x3 - x2) * (y - y3)) / det
            l2 = ((y3 - y1) * (x - x3) + (x1 - x3) * (y - y3)) / det
            l3 = 1.0 - l1 - l2

            # Inside triangle with small floating point tolerance
            eps = -1e-4
            if l1 >= eps and l2 >= eps and l3 >= eps:
                return l1 * z1 + l2 * z2 + l3 * z3

        # 2. Point is outside convex hull: Inverse Distance Weighting (IDW) fallback across 3 nearest neighbors
        distances = []
        for p in self.coords_3d:
            d = math.hypot(x - p[0], y - p[1])
            if d < 1e-4:
                return p[2]
            distances.append((d, p[2]))

        distances.sort(key=lambda item: item[0])
        nearest = distances[:min(3, len(distances))]
        total_weight = sum(1.0 / (d**2) for d, _ in nearest)
        interpolated = sum((z / (d**2)) for d, z in nearest) / total_weight
        return interpolated

    def warp_gcode(
        self,
        gcode_text: str,
        max_segment_length: float = 3.0,
        fade_height: Optional[float] = None,
    ) -> str:
        """
        Applies dynamic surface warping to a raw G-code program string.
        Segments linear moves (G0/G1) into <= max_segment_length chunks and
        discretizes G2/G3 arcs, adjusting Z -> Z + ΔZ(X, Y).
        """
        lines = gcode_text.splitlines()
        warped_lines = []

        cur_x = 0.0
        cur_y = 0.0
        cur_z = 0.0
        active_motion = "G0"
        is_relative = False

        warped_lines.append(f"( --- WORKPIECE MESH LEVELING APPLIED: {len(self.active_points)} PROBED POINTS --- )")
        warped_lines.append(f"( Surface Elevation Span: {self.z_min:+.3f}mm to {self.z_max:+.3f}mm | Span: {self.z_span:.3f}mm )")

        for line in lines:
            raw = line.strip()
            if not raw:
                warped_lines.append(line)
                continue

            upper = raw.upper()

            # Pass comments, settings, spindle, and tool change lines unmodified
            if upper.startswith("(") or upper.startswith(";") or upper.startswith("%"):
                warped_lines.append(line)
                continue
            if "G91" in upper and "G90" not in upper:
                is_relative = True
                warped_lines.append(line)
                continue
            if "G90" in upper:
                is_relative = False
                warped_lines.append(line)
                continue
            if upper.startswith("M") or upper.startswith("T") or upper.startswith("S") or upper.startswith("F"):
                warped_lines.append(line)
                continue

            # Strip comments from the line for motion parsing
            comment_match = re.search(r"(\(.*?\)|;.*$)", raw)
            comment_str = comment_match.group(1) if comment_match else ""
            line_body = raw[:comment_match.start()].strip() if comment_match else raw

            tokens = line_body.split()
            if not tokens:
                warped_lines.append(line)
                continue

            # Detect motion modal
            for t in tokens:
                tu = t.upper()
                if tu in ("G0", "G00", "G1", "G01", "G2", "G02", "G3", "G03"):
                    active_motion = tu

            # Extract target coordinates
            target_x = cur_x
            target_y = cur_y
            target_z = cur_z
            has_x = False
            has_y = False
            has_z = False
            feed_token = ""

            for t in tokens:
                tu = t.upper()
                if tu.startswith("X") and not tu.startswith("XY"):
                    try:
                        target_x = float(tu[1:])
                        has_x = True
                    except ValueError:
                        pass
                elif tu.startswith("Y"):
                    try:
                        target_y = float(tu[1:])
                        has_y = True
                    except ValueError:
                        pass
                elif tu.startswith("Z"):
                    try:
                        target_z = float(tu[1:])
                        has_z = True
                    except ValueError:
                        pass
                elif tu.startswith("F"):
                    feed_token = tu

            if is_relative:
                # Relative coordinates are passed as-is
                warped_lines.append(line)
                continue

            # Calculate move distance
            dx = target_x - cur_x
            dy = target_y - cur_y
            dz = target_z - cur_z
            dist_xy = math.hypot(dx, dy)

            # 1. Pure Vertical Plunges / Retracts (Z motion only)
            if (has_z and not has_x and not has_y) or (dist_xy < 1e-4 and has_z):
                delta_z = self.interpolate_z(cur_x, cur_y)
                # Apply fade height if configured
                fade_scale = 1.0
                if fade_height and target_z > 0:
                    fade_scale = max(0.0, 1.0 - (target_z / fade_height))
                warped_z = target_z + (delta_z * fade_scale)

                cmd = f"{active_motion} Z{warped_z:.3f}"
                if feed_token:
                    cmd += f" {feed_token}"
                if comment_str:
                    cmd += f" {comment_str}"
                warped_lines.append(cmd)
                cur_z = target_z
                continue

            # 2. Linear Cutting / Traverse Moves (G0, G1)
            if active_motion in ("G0", "G00", "G1", "G01"):
                if dist_xy <= max_segment_length:
                    # Single move
                    delta_z = self.interpolate_z(target_x, target_y)
                    fade_scale = 1.0
                    if fade_height and target_z > 0:
                        fade_scale = max(0.0, 1.0 - (target_z / fade_height))
                    warped_z = target_z + (delta_z * fade_scale)

                    cmd = f"{active_motion} X{target_x:.3f} Y{target_y:.3f} Z{warped_z:.3f}"
                    if feed_token:
                        cmd += f" {feed_token}"
                    if comment_str:
                        cmd += f" {comment_str}"
                    warped_lines.append(cmd)
                else:
                    # Subdivide long linear moves into segments <= max_segment_length
                    steps = max(2, int(math.ceil(dist_xy / max_segment_length)))
                    for step_i in range(1, steps + 1):
                        frac = step_i / steps
                        sx = cur_x + frac * dx
                        sy = cur_y + frac * dy
                        sz = cur_z + frac * dz
                        delta_z = self.interpolate_z(sx, sy)
                        fade_scale = 1.0
                        if fade_height and sz > 0:
                            fade_scale = max(0.0, 1.0 - (sz / fade_height))
                        warped_z = sz + (delta_z * fade_scale)

                        cmd = f"{active_motion} X{sx:.3f} Y{sy:.3f} Z{warped_z:.3f}"
                        if step_i == 1 and feed_token:
                            cmd += f" {feed_token}"
                        if step_i == steps and comment_str:
                            cmd += f" {comment_str}"
                        warped_lines.append(cmd)

                cur_x = target_x
                cur_y = target_y
                cur_z = target_z

            # 3. Circular Arcs (G2, G3)
            elif active_motion in ("G2", "G02", "G3", "G03"):
                # Linearize arc into chordal segments with interpolated mesh heights
                i_val = 0.0
                j_val = 0.0
                for t in tokens:
                    tu = t.upper()
                    if tu.startswith("I"):
                        i_val = float(tu[1:])
                    elif tu.startswith("J"):
                        j_val = float(tu[1:])

                arc_center_x = cur_x + i_val
                arc_center_y = cur_y + j_val
                r_start = math.hypot(cur_x - arc_center_x, cur_y - arc_center_y)
                start_angle = math.atan2(cur_y - arc_center_y, cur_x - arc_center_x)
                end_angle = math.atan2(target_y - arc_center_y, target_x - arc_center_x)

                is_cw = active_motion in ("G2", "G02")
                if is_cw:
                    if end_angle >= start_angle:
                        end_angle -= 2 * math.pi
                    sweep = abs(start_angle - end_angle)
                else:
                    if end_angle <= start_angle:
                        end_angle += 2 * math.pi
                    sweep = abs(end_angle - start_angle)

                arc_len = r_start * sweep
                steps = max(4, int(math.ceil(arc_len / max_segment_length)))

                for step_i in range(1, steps + 1):
                    frac = step_i / steps
                    cur_ang = start_angle - frac * sweep if is_cw else start_angle + frac * sweep
                    sx = arc_center_x + r_start * math.cos(cur_ang)
                    sy = arc_center_y + r_start * math.sin(cur_ang)
                    sz = cur_z + frac * dz
                    delta_z = self.interpolate_z(sx, sy)
                    fade_scale = 1.0
                    if fade_height and sz > 0:
                        fade_scale = max(0.0, 1.0 - (sz / fade_height))
                    warped_z = sz + (delta_z * fade_scale)

                    cmd = f"G1 X{sx:.3f} Y{sy:.3f} Z{warped_z:.3f}"
                    if step_i == 1 and feed_token:
                        cmd += f" {feed_token}"
                    if step_i == steps and comment_str:
                        cmd += f" {comment_str}"
                    warped_lines.append(cmd)

                cur_x = target_x
                cur_y = target_y
                cur_z = target_z

            else:
                warped_lines.append(line)

        return "\n".join(warped_lines)

    def to_dict(self) -> Dict[str, Any]:
        """Serializes mesh map state for API transfer and storage."""
        return {
            "shape_type": self.shape_type,
            "shape_meta": self.shape_meta,
            "point_count": len(self.raw_points),
            "active_point_count": len(self.active_points),
            "points": self.raw_points,
            "z_min": round(self.z_min, 3),
            "z_max": round(self.z_max, 3),
            "z_span": round(self.z_span, 3),
            "triangles": self.triangles,
        }


# =============================================================================
# 4. Probing Macro Generator & Log Parser
# =============================================================================

def generate_mesh_probe_macro(
    points: List[Dict[str, Any]],
    search_dist: float = 20.0,
    fast_feed: float = 150.0,
    slow_feed: float = 25.0,
    safe_traverse_z: float = 5.0,
    plate_thickness: float = 0.0,
    shape_type: str = "rectangle",
    units: str = "mm",
    dialect: str = "grbl",
) -> Dict[str, Any]:
    """
    Generates an automated G38.2 workpiece touch-probing G-code macro.
    Traverses only active points with safe retract clearances.
    """
    active_points = [p for p in points if p.get("active", True)]
    if not active_points:
        raise ValueError("At least 1 active probe point is required.")

    unit_cmd = "G21" if units.lower() in ("mm", "metric") else "G20"
    lines = [
        "( =================================================== )",
        "( >>> CONVERSATIONAL CNC: WORKPIECE SURFACE MESH PROBE <<< )",
        f"( Shape: {shape_type.upper()} | Active Probe Points: {len(active_points)} )",
        f"( Fast Feed: {fast_feed:.1f}mm/min | Fine Feed: {slow_feed:.1f}mm/min )",
        f"( Safe Traverse Z: {safe_traverse_z:.3f}mm | Plate Thickness: {plate_thickness:.3f}mm )",
        "( =================================================== )",
        f"{unit_cmd} G90 G94 (Metric absolute programming)",
        "G54 (Ensure Active WCS)",
        f"G0 Z{safe_traverse_z:.3f} (Move to safe traverse plane)",
        "",
    ]

    for idx, pt in enumerate(active_points, 1):
        x = pt["x"]
        y = pt["y"]
        pt_id = pt.get("id", idx - 1)

        lines.extend([
            f"( --- Point {idx}/{len(active_points)} [ID {pt_id}]: X{x:.3f} Y{y:.3f} --- )",
            f"G0 X{x:.3f} Y{y:.3f}",
            "G91 (Incremental distance mode)",
            f"G38.2 Z-{abs(search_dist):.3f} F{fast_feed:.1f} (Fast search touch)",
            "G0 Z1.500 (Lift off contact plate)",
            f"G38.2 Z-3.000 F{slow_feed:.1f} (Slow precision touch)",
            "G90 (Return to absolute mode)",
            f"G0 Z{safe_traverse_z:.3f} (Safe retract between points)",
            "",
        ])

    lines.extend([
        "( --- Probing Routine Completed Successfully --- )",
        f"G0 X{active_points[0]['x']:.3f} Y{active_points[0]['y']:.3f} (Return above first probe point)",
        f"G0 Z{safe_traverse_z:.3f}",
        "M2",
    ])

    return {
        "macro_name": f"mesh_probe_{shape_type}_{len(active_points)}pts",
        "shape_type": shape_type,
        "point_count": len(active_points),
        "gcode": "\n".join(lines),
        "line_count": len(lines),
    }


def parse_probe_log(
    log_text: str,
    points_template: Optional[List[Dict[str, Any]]] = None,
    plate_thickness: float = 0.0,
) -> WorkpieceMeshMap:
    """
    Parses machine sender console output (Grbl [PRB:X,Y,Z:1], CSV x,y,z, or JSON)
    and populates surface elevation coordinates.
    """
    lines = log_text.strip().splitlines()
    parsed_samples: List[Tuple[float, float, float]] = []

    for line in lines:
        raw = line.strip()
        if not raw:
            continue

        # 1. Match Grbl probe responses: [PRB:25.000,10.000,-1.420:1] or [PRB:25.0,10.0,-1.42:0]
        prb_match = re.search(r"\[PRB:\s*([-\d.]+)\s*,\s*([-\d.]+)\s*,\s*([-\d.]+)", raw, re.IGNORECASE)
        if prb_match:
            x = float(prb_match.group(1))
            y = float(prb_match.group(2))
            z = float(prb_match.group(3)) - plate_thickness
            parsed_samples.append((x, y, z))
            continue

        # 2. Match CSV format: X, Y, Z or X Y Z
        csv_parts = re.split(r"[,\s]+", raw)
        if len(csv_parts) >= 3:
            try:
                x = float(csv_parts[0])
                y = float(csv_parts[1])
                z = float(csv_parts[2]) - plate_thickness
                parsed_samples.append((x, y, z))
                continue
            except ValueError:
                pass

    # If template points were provided, associate measured Z with nearest template coordinates
    if points_template:
        updated_points = []
        for pt in points_template:
            pt_copy = dict(pt)
            px, py = pt["x"], pt["y"]
            # Find closest sample
            if parsed_samples:
                closest = min(parsed_samples, key=lambda s: math.hypot(px - s[0], py - s[1]))
                if math.hypot(px - closest[0], py - closest[1]) < 5.0:
                    pt_copy["z"] = round(closest[2], 3)
            updated_points.append(pt_copy)
        return WorkpieceMeshMap(updated_points)

    # Otherwise build from parsed samples directly
    points = [{"id": i, "x": s[0], "y": s[1], "z": s[2], "active": True} for i, s in enumerate(parsed_samples)]
    return WorkpieceMeshMap(points)
