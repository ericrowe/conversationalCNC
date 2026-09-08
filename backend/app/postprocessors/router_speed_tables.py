"""
Router Speed Tables & Dial Interpolation Engine.

Provides RPM-to-dial position conversion, piecewise-linear interpolation,
and high-visibility G-code operator setup comments for manual trim routers
(e.g., Makita RT0701C, DeWalt DWP611, Bosch Colt PR20EVS).
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


@dataclass
class RouterSpec:
    model_id: str
    display_name: str
    dial_points: Dict[int, int]  # dial_number -> RPM
    min_rpm: int
    max_rpm: int
    description: str


ROUTER_SPECS: Dict[str, RouterSpec] = {
    "dewalt_611": RouterSpec(
        model_id="dewalt_611",
        display_name="DeWalt DWP611",
        dial_points={
            1: 16000,
            2: 18200,
            3: 20400,
            4: 22600,
            5: 24800,
            6: 27000,
        },
        min_rpm=16000,
        max_rpm=27000,
        description="DeWalt DWP611 / Porter-Cable 450 (1.25 HP, 16,000 - 27,000 RPM, 6-speed dial)",
    ),
    "makita_rt0701": RouterSpec(
        model_id="makita_rt0701",
        display_name="Makita RT0701C",
        dial_points={
            1: 10000,
            2: 12000,
            3: 17000,
            4: 22000,
            5: 27000,
            6: 30000,
        },
        min_rpm=10000,
        max_rpm=30000,
        description="Makita RT0701C / RT0700C (1.25 HP, 10,000 - 30,000 RPM, 6-speed dial)",
    ),
    "bosch_colt": RouterSpec(
        model_id="bosch_colt",
        display_name="Bosch Colt PR20EVS",
        dial_points={
            1: 16000,
            2: 18000,
            3: 22000,
            4: 26000,
            5: 30000,
            6: 35000,
        },
        min_rpm=16000,
        max_rpm=35000,
        description="Bosch Colt PR20EVS / GKF125CE (1.0-1.25 HP, 16,000 - 35,000 RPM, 6-speed dial)",
    ),
    "generic": RouterSpec(
        model_id="generic",
        display_name="Generic Trim Router",
        dial_points={
            1: 10000,
            2: 14000,
            3: 18000,
            4: 22000,
            5: 26000,
            6: 30000,
        },
        min_rpm=10000,
        max_rpm=30000,
        description="Generic Variable-Speed Router (10,000 - 30,000 RPM, 1-6 dial)",
    ),
}

# Model aliases for fuzzy/case-insensitive resolution
ROUTER_ALIASES: Dict[str, str] = {
    "dewalt_611": "dewalt_611",
    "dewalt_dwp611": "dewalt_611",
    "dewalt": "dewalt_611",
    "dwp611": "dewalt_611",
    "makita_rt0701": "makita_rt0701",
    "makita_rt0701c": "makita_rt0701",
    "makita": "makita_rt0701",
    "rt0701": "makita_rt0701",
    "rt0701c": "makita_rt0701",
    "bosch_colt": "bosch_colt",
    "bosch_pr20evs": "bosch_colt",
    "bosch": "bosch_colt",
    "colt": "bosch_colt",
    "generic": "generic",
    "generic_router": "generic",
    "router": "generic",
}


@dataclass
class RouterDialInfo:
    model_id: str
    display_name: str
    dial_setting: float
    dial_display: str
    target_rpm: int
    actual_rpm: int
    is_clamped: bool
    warning: Optional[str] = None


def is_manual_spindle(spindle_type: Optional[str]) -> bool:
    """Returns True if the spindle type represents a manual router (not software VFD)."""
    if not spindle_type:
        return True
    val = str(spindle_type).lower().strip().replace("-", "_")
    return val in ("manual_router", "router", "manual", "trim_router", "dewalt", "makita", "bosch")


def is_vfd_spindle(spindle_type: Optional[str]) -> bool:
    """Returns True if the spindle type represents an automatic VFD / PWM spindle."""
    return not is_manual_spindle(spindle_type)


def normalize_router_model(model_name: Optional[str]) -> str:
    """Normalizes router model identifier or returns 'dewalt_611' default."""
    if not model_name:
        return "dewalt_611"
    clean = str(model_name).lower().strip().replace("-", "_").replace(" ", "_")
    return ROUTER_ALIASES.get(clean, "dewalt_611")


def get_router_spec(model_name: Optional[str]) -> RouterSpec:
    """Returns the RouterSpec for a given router model name or alias."""
    norm_id = normalize_router_model(model_name)
    return ROUTER_SPECS.get(norm_id, ROUTER_SPECS["dewalt_611"])


def interpolate_router_dial(model_name: Optional[str], target_rpm: int) -> RouterDialInfo:
    """
    Computes continuous piecewise-linear dial setting (1.0 to 6.0) for a target RPM.
    Clamps to min/max RPM bounds and generates informative warnings if out-of-range.
    """
    spec = get_router_spec(model_name)
    sorted_dials = sorted(spec.dial_points.keys())
    
    is_clamped = False
    warning = None
    effective_rpm = int(target_rpm)

    if effective_rpm <= spec.min_rpm:
        effective_rpm = spec.min_rpm
        dial_float = float(sorted_dials[0])
        if target_rpm < spec.min_rpm:
            is_clamped = True
            warning = f"Target speed ({target_rpm:,} RPM) is below {spec.display_name} minimum ({spec.min_rpm:,} RPM). Clamped to Dial {sorted_dials[0]} ({spec.min_rpm:,} RPM)."
    elif effective_rpm >= spec.max_rpm:
        effective_rpm = spec.max_rpm
        dial_float = float(sorted_dials[-1])
        if target_rpm > spec.max_rpm:
            is_clamped = True
            warning = f"Target speed ({target_rpm:,} RPM) is above {spec.display_name} maximum ({spec.max_rpm:,} RPM). Clamped to Dial {sorted_dials[-1]} ({spec.max_rpm:,} RPM)."
    else:
        # Piecewise linear interpolation between adjacent dial points
        dial_float = float(sorted_dials[0])
        for i in range(len(sorted_dials) - 1):
            d1 = sorted_dials[i]
            d2 = sorted_dials[i + 1]
            rpm1 = spec.dial_points[d1]
            rpm2 = spec.dial_points[d2]
            if rpm1 <= effective_rpm <= rpm2:
                fraction = (effective_rpm - rpm1) / (rpm2 - rpm1)
                dial_float = d1 + fraction * (d2 - d1)
                break

    dial_float = round(dial_float, 1)
    dial_display = f"{dial_float:.1f}"

    return RouterDialInfo(
        model_id=spec.model_id,
        display_name=spec.display_name,
        dial_setting=dial_float,
        dial_display=dial_display,
        target_rpm=target_rpm,
        actual_rpm=effective_rpm,
        is_clamped=is_clamped,
        warning=warning,
    )


def format_manual_spindle_comment(
    router_model: Optional[str],
    target_rpm: int,
    router_dial: Optional[float] = None,
    require_pause: bool = False,
) -> List[str]:
    """
    Generates high-visibility setup comments and optional M0 confirmation pause
    for manual trim routers.
    """
    if router_dial is not None:
        spec = get_router_spec(router_model)
        dial_float = round(float(router_dial), 1)
        dial_display = f"{dial_float:.1f}"
        dial_info = RouterDialInfo(
            model_id=spec.model_id,
            display_name=spec.display_name,
            dial_setting=dial_float,
            dial_display=dial_display,
            target_rpm=target_rpm,
            actual_rpm=target_rpm,
            is_clamped=False,
        )
    else:
        dial_info = interpolate_router_dial(router_model, target_rpm)

    lines = [
        f"( *** MANUAL ROUTER: SET SPEED DIAL TO {dial_info.dial_display} (~{dial_info.target_rpm:,} RPM) *** )",
        f"( Spindle: {dial_info.display_name} - Set Speed Dial to {dial_info.dial_display} [~{dial_info.target_rpm:,} RPM] )",
        "( Operator Safety: Turn physical router switch ON before cycle start )",
    ]

    if require_pause:
        lines.append(f"M0 (Pause: Turn {dial_info.display_name} ON at Dial {dial_info.dial_display}, verify rotation, then resume)")

    return lines
