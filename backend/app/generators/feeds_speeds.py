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

# Material Cutting Constants calibrated for belt-driven desktop CNCs (X-Carve, Shapeoko)
# powered by trim routers (DeWalt DWP611, Makita RT0701) running at 16,000 - 27,000 RPM.
# Matched against Inventables Easel safe & conservative factory recommendations.
MATERIAL_PHYSICS_CATALOG = {
    "softwood_pine": {
        "name": "Softwood (Pine, Cedar, Spruce)",
        "smm_range": (150, 250),
        "base_chipload_mm": 0.038,  # ~1200 mm/min @ 16k RPM (1/4" 2F), ~950 mm/min (1/8" 2F)
        "recommended_stepdown_ratio": 0.30,  # ~1.0mm (1/8"), ~1.8mm (1/4")
        "unit_power_kp": 0.00035,
        "hardness_desc": "Soft, low cutting resistance, safe conservative feed prevents belt flex",
    },
    "hardwood_oak": {
        "name": "Hardwood (Oak, Maple, Walnut)",
        "smm_range": (130, 220),
        "base_chipload_mm": 0.028,  # ~900-1000 mm/min @ 18k RPM (1/4" 2F), ~750 mm/min (1/8" 2F)
        "recommended_stepdown_ratio": 0.25,  # ~0.8mm (1/8"), ~1.5mm (1/4")
        "unit_power_kp": 0.00065,
        "hardness_desc": "Medium-hard, moderate feed & shallow stepdowns to prevent chatter and motor stalling",
    },
    "mdf_plywood": {
        "name": "MDF / Baltic Birch Plywood",
        "smm_range": (140, 240),
        "base_chipload_mm": 0.036,  # ~1150 mm/min @ 16k RPM (1/4" 2F), ~900 mm/min (1/8" 2F)
        "recommended_stepdown_ratio": 0.30,  # ~1.0mm (1/8"), ~1.8mm (1/4")
        "unit_power_kp": 0.00050,
        "hardness_desc": "Abrasive binders, moderate speed prevents burning while avoiding gantry flex",
    },
    "acrylic_plastics": {
        "name": "Cast Acrylic (PMMA) / Polycarbonate",
        "smm_range": (100, 180),
        "base_chipload_mm": 0.026,  # ~850 mm/min @ 16k RPM (1/4" 2F), ~600 mm/min (1/8" 2F)
        "recommended_stepdown_ratio": 0.20,  # ~0.6mm (1/8"), ~1.2mm (1/4")
        "unit_power_kp": 0.00075,
        "hardness_desc": "Melting risk: run at lowest router dial (Dial 1 / 16k RPM) with single or 2-flute",
    },
    "delrin_acetal": {
        "name": "Delrin / Acetal (POM)",
        "smm_range": (120, 220),
        "base_chipload_mm": 0.030,  # ~960 mm/min @ 16k RPM (1/4" 2F), ~700 mm/min (1/8" 2F)
        "recommended_stepdown_ratio": 0.25,  # ~0.8mm (1/8"), ~1.5mm (1/4")
        "unit_power_kp": 0.00060,
        "hardness_desc": "Excellent machinability, clean chips, generous chip clearance",
    },
    "aluminum_6061": {
        "name": "Aluminum (6061-T6 / Mic-6)",
        "smm_range": (60, 120),
        "base_chipload_mm": 0.011,  # ~350 mm/min @ 16k RPM Dial 1 (1/4" 2F), ~250 mm/min (1/8" 2F)
        "recommended_stepdown_ratio": 0.05,  # ~0.15mm (1/8"), ~0.25mm (1/4") shallow passes
        "unit_power_kp": 0.0022,
        "hardness_desc": "Requires very shallow stepdowns (0.15-0.25mm) and lubrication to prevent belt stretch and bit grab",
    },
    "brass_360": {
        "name": "Free-Cutting Brass (C360)",
        "smm_range": (70, 140),
        "base_chipload_mm": 0.013,  # ~420 mm/min @ 16k RPM Dial 1 (1/4" 2F), ~300 mm/min (1/8" 2F)
        "recommended_stepdown_ratio": 0.06,  # ~0.20mm (1/8"), ~0.35mm (1/4")
        "unit_power_kp": 0.0025,
        "hardness_desc": "Short brittle chips, shallow stepdowns yield clean burr-free edges",
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
    min_spindle_rpm: int = 16000,
    machine_rigidity: str = "belt_driven",
) -> Dict[str, Any]:
    """
    Computes conservative, physics-based feeds, speeds, radial chip thinning compensation,
    MRR, and spindle power requirements tailored for belt-driven CNC routers.
    """
    if tool_diameter_mm <= 0:
        raise ValueError("Tool diameter must be positive.")
    if num_flutes <= 0:
        raise ValueError("Number of flutes must be at least 1.")

    mat = MATERIAL_PHYSICS_CATALOG.get(material_key, MATERIAL_PHYSICS_CATALOG["softwood_pine"])

    # 1. Surface Speed (SMM) -> Ideal RPM (respecting trim router min speed 16k RPM)
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
        # Clamped to max 2.0x for belt machine rigidity safety
        rctf = min(2.0, 1.0 / (2.0 * math.sqrt(max(0.01, stepover_ratio - (stepover_ratio ** 2)))))

    compensated_chipload = base_chipload * rctf

    # 4. Cutting Feed Rate (mm/min)
    feed_rate_xy = actual_rpm * num_flutes * compensated_chipload
    feed_rate_xy = round(feed_rate_xy, 1)

    # Plunge Feed Rate: on belt machines with leadscrew/threaded rod Z, keep plunge conservative (20-30% of XY feed, max 250 mm/min)
    plunge_ratio = 0.20 if "aluminum" in material_key or "brass" in material_key else 0.25
    plunge_feed = round(min(250.0, max(50.0, feed_rate_xy * plunge_ratio)), 1)

    # 5. Recommended Stepdown (mm)
    recommended_stepdown = round(tool_diameter_mm * mat.get("recommended_stepdown_ratio", 0.25), 2)
    eff_stepdown = stepdown_mm if (stepdown_mm is not None and stepdown_mm > 0) else recommended_stepdown

    # 6. Material Removal Rate (MRR in cm3/min)
    mrr_cm3_min = (eff_stepover * eff_stepdown * feed_rate_xy) / 1000.0

    # 7. Spindle Cutting Power (kW & HP)
    power_kw = mrr_cm3_min * mat["unit_power_kp"]
    power_hp = power_kw * 1.34102

    # 8. Tool Deflection & Machine Rigidity Safety Advisories
    warnings = []
    stickout = tool_stickout_mm if tool_stickout_mm is not None else (tool_diameter_mm * 3.5)
    stickout_ratio = stickout / tool_diameter_mm

    if stickout_ratio > 4.5:
        warnings.append(
            f"Long tool stickout ({stickout:.1f}mm = {stickout_ratio:.1f}x diameter). "
            f"High tool deflection risk on belt-driven machines; reduce stepdown to avoid chatter."
        )

    if stepdown_mm and stepdown_mm > (recommended_stepdown * 1.5):
        warnings.append(
            f"Stepdown ({stepdown_mm:.2f}mm) exceeds conservative recommendation ({recommended_stepdown:.2f}mm) for {mat['name']}. "
            f"Belt-driven gantries may flex or lose steps."
        )

    if power_kw > 0.65:
        warnings.append(
            f"Estimated spindle load ({power_kw:.2f} kW / {power_hp:.2f} HP) is heavy for a desktop trim router & belt drive. "
            f"Consider lighter depth of cut."
        )

    return {
        "material_name": mat["name"],
        "tool_diameter_mm": tool_diameter_mm,
        "num_flutes": num_flutes,
        "recommended_rpm": actual_rpm,
        "recommended_feed_xy": feed_rate_xy,
        "recommended_plunge_feed": plunge_feed,
        "recommended_stepdown_mm": recommended_stepdown,
        "surface_speed_smm": round(actual_smm, 1),
        "nominal_chipload_mm": round(base_chipload, 4),
        "compensated_chipload_mm": round(compensated_chipload, 4),
        "rctf_multiplier": round(rctf, 3),
        "mrr_cm3_min": round(mrr_cm3_min, 2),
        "estimated_power_kw": round(power_kw, 3),
        "estimated_power_hp": round(power_hp, 3),
        "warnings": warnings,
    }

