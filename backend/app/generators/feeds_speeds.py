"""
Physics-Based Speeds & Feeds & Chip Load Engine (Phase 7).
Features:
- Surface speed (SFM / SMM) to Spindle RPM calculation
- Chip load (IPT / mm per tooth) to Feed Rate calculation
- Radial Chip Thinning Factor (RCTF) compensation for light stepovers (< 50% tool diameter)
- Material Removal Rate (MRR) calculation
- Spindle Cutting Power & Torque Estimation (kW / HP)
- Tool Deflection & Rigidity Warning advisor
"""
import math
from typing import Dict, Any, Optional

# Material Cutting Constants:
# - smm_range: recommended Surface Meters per Minute (m/min) for carbide tooling
# - base_chipload_mm: baseline chip load per tooth (mm) for 1/4" (6.35mm) endmill
# - unit_power_kp: Specific cutting power (kW per cm3/min)
MATERIAL_PHYSICS_CATALOG = {
    "softwood_pine": {
        "name": "Softwood (Pine, Cedar, Spruce)",
        "smm_range": (300, 700),
        "base_chipload_mm": 0.10,
        "unit_power_kp": 0.00035,
        "hardness_desc": "Soft, low cutting resistance, high chip clearance recommended",
    },
    "hardwood_oak": {
        "name": "Hardwood (Oak, Maple, Walnut)",
        "smm_range": (250, 500),
        "base_chipload_mm": 0.07,
        "unit_power_kp": 0.00065,
        "hardness_desc": "Medium-hard, moderate power, avoid burning at high RPM",
    },
    "mdf_plywood": {
        "name": "MDF / Baltic Birch Plywood",
        "smm_range": (300, 600),
        "base_chipload_mm": 0.08,
        "unit_power_kp": 0.00050,
        "hardness_desc": "Abrasive glues, high RPM + fast feed prevents cutter dulling",
    },
    "acrylic_plastics": {
        "name": "Cast Acrylic (PMMA) / Polycarbonate",
        "smm_range": (150, 350),
        "base_chipload_mm": 0.06,
        "unit_power_kp": 0.00075,
        "hardness_desc": "Melting risk, sharp 1-flute / 2-flute cutter recommended",
    },
    "delrin_acetal": {
        "name": "Delrin / Acetal (POM)",
        "smm_range": (200, 450),
        "base_chipload_mm": 0.08,
        "unit_power_kp": 0.00060,
        "hardness_desc": "Excellent machinability, clean chips, generous chip load",
    },
    "aluminum_6061": {
        "name": "Aluminum (6061-T6 / Mic-6)",
        "smm_range": (120, 300),
        "base_chipload_mm": 0.035,
        "unit_power_kp": 0.0022,
        "hardness_desc": "Requires aggressive chip load to avoid gummy re-welding",
    },
    "brass_360": {
        "name": "Free-Cutting Brass (C360)",
        "smm_range": (100, 250),
        "base_chipload_mm": 0.04,
        "unit_power_kp": 0.0025,
        "hardness_desc": "Short brittle chips, excellent dimensional stability",
    },
}


def calculate_feeds_and_speeds(
    material_key: str,
    tool_diameter_mm: float,
    num_flutes: int = 2,
    stepover_mm: Optional[float] = None,
    stepdown_mm: Optional[float] = None,
    tool_stickout_mm: Optional[float] = None,
    target_smm: Optional[float] = None,
    target_chipload_mm: Optional[float] = None,
    max_spindle_rpm: int = 27000,
    min_spindle_rpm: int = 10000,
) -> Dict[str, Any]:
    """
    Computes optimal feeds, speeds, radial chip thinning compensation,
    MRR, and spindle power requirements.
    """
    if tool_diameter_mm <= 0:
        raise ValueError("Tool diameter must be positive.")
    if num_flutes <= 0:
        raise ValueError("Number of flutes must be at least 1.")

    mat = MATERIAL_PHYSICS_CATALOG.get(material_key, MATERIAL_PHYSICS_CATALOG["softwood_pine"])

    # 1. Surface Speed (SMM) -> Ideal RPM
    smm = target_smm if target_smm is not None else (mat["smm_range"][0] + mat["smm_range"][1]) / 2.0
    ideal_rpm = (smm * 1000.0) / (math.pi * tool_diameter_mm)
    actual_rpm = max(min_spindle_rpm, min(max_spindle_rpm, int(round(ideal_rpm))))
    actual_smm = (math.pi * tool_diameter_mm * actual_rpm) / 1000.0

    # 2. Scale baseline chip load with tool diameter (reference = 6.35mm / 1/4")
    dia_scale = math.sqrt(tool_diameter_mm / 6.35)
    base_chipload = target_chipload_mm if target_chipload_mm is not None else (mat["base_chipload_mm"] * dia_scale)

    # 3. Radial Chip Thinning Factor (RCTF)
    # When stepover < 50% tool diameter, chips are thinner than nominal feed per tooth.
    eff_stepover = stepover_mm if (stepover_mm is not None and stepover_mm > 0) else tool_diameter_mm
    stepover_ratio = min(1.0, eff_stepover / tool_diameter_mm)

    rctf = 1.0
    if stepover_ratio < 0.5:
        # Chip thinning formula: RCTF = 1 / (2 * sqrt( (W/D) - (W/D)^2 ))
        rctf = 1.0 / (2.0 * math.sqrt(stepover_ratio - (stepover_ratio ** 2)))

    compensated_chipload = base_chipload * rctf

    # 4. Cutting Feed Rate (mm/min)
    feed_rate_xy = actual_rpm * num_flutes * compensated_chipload
    feed_rate_xy = round(feed_rate_xy, 1)

    # Plunge Feed Rate (usually 25% - 40% of XY feed)
    plunge_feed = round(max(50.0, feed_rate_xy * 0.3), 1)

    # 5. Material Removal Rate (MRR in cm3/min)
    eff_stepdown = stepdown_mm if (stepdown_mm is not None and stepdown_mm > 0) else (tool_diameter_mm * 0.5)
    mrr_cm3_min = (eff_stepover * eff_stepdown * feed_rate_xy) / 1000.0

    # 6. Spindle Cutting Power (kW & HP)
    power_kw = mrr_cm3_min * mat["unit_power_kp"]
    power_hp = power_kw * 1.34102

    # 7. Tool Deflection & Rigidity Safety Advisories
    warnings = []
    stickout = tool_stickout_mm if tool_stickout_mm is not None else (tool_diameter_mm * 3.5)
    stickout_ratio = stickout / tool_diameter_mm

    if stickout_ratio > 4.5:
        warnings.append(
            f"Long tool stickout ({stickout:.1f}mm = {stickout_ratio:.1f}x diameter). "
            f"High tool deflection risk; reduce stepdown or stepover to avoid chatter."
        )

    if power_kw > 0.85:
        warnings.append(
            f"Estimated spindle power ({power_kw:.2f} kW / {power_hp:.2f} HP) exceeds typical hobby trim router capacity (~0.75-0.9 kW). "
            f"Reduce feed rate or depth of cut."
        )

    return {
        "material_name": mat["name"],
        "tool_diameter_mm": tool_diameter_mm,
        "num_flutes": num_flutes,
        "recommended_rpm": actual_rpm,
        "recommended_feed_xy": feed_rate_xy,
        "recommended_plunge_feed": plunge_feed,
        "surface_speed_smm": round(actual_smm, 1),
        "nominal_chipload_mm": round(base_chipload, 4),
        "compensated_chipload_mm": round(compensated_chipload, 4),
        "rctf_multiplier": round(rctf, 3),
        "mrr_cm3_min": round(mrr_cm3_min, 2),
        "estimated_power_kw": round(power_kw, 3),
        "estimated_power_hp": round(power_hp, 3),
        "warnings": warnings,
    }
