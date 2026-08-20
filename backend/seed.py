from app import create_app
from app.models import db, MachineProfile, Tool, MaterialPreset

def seed_database():
    app = create_app()
    with app.app_context():
        # Clear existing data for fresh seed
        db.drop_all()
        db.create_all()

        print("Seeding Machine Profiles...")
        xcarve = MachineProfile(
            name="Inventables X-Carve 1000mm",
            is_active=True,
            controller_dialect="grbl",
            spindle_type="router",
            router_model="dewalt_611",
            work_area_x=750.0,
            work_area_y=750.0,
            work_area_z=65.0,
            max_feed_xy=8000.0,
            max_feed_z=500.0,
            rapid_feed_rate=5000.0,
            min_spindle_rpm=16000,
            max_spindle_rpm=27000,
            spindle_dwell_seconds=2.0,
            z_probe_thickness=14.85,
            safe_z_retract=5.0,
            notes="Arduino/gShield Grbl setup with DeWalt DWP611 trim router (Dial 1=16k, Dial 6=27k)",
        )

        shapeoko = MachineProfile(
            name="Shapeoko Pro Standard",
            is_active=False,
            controller_dialect="grbl",
            spindle_type="vfd_spindle",
            router_model=None,
            work_area_x=838.0,
            work_area_y=838.0,
            work_area_z=95.0,
            max_feed_xy=10000.0,
            max_feed_z=1000.0,
            rapid_feed_rate=6000.0,
            min_spindle_rpm=6000,
            max_spindle_rpm=24000,
            spindle_dwell_seconds=2.0,
            z_probe_thickness=15.0,
            safe_z_retract=10.0,
            notes="VFD water-cooled spindle configuration (6,000 - 24,000 RPM continuous)",
        )

        db.session.add_all([xcarve, shapeoko])
        db.session.flush()

        print("Seeding Tool Library...")
        tool1 = Tool(
            tool_number=1,
            name='1/8" (3.175mm) 2-Flute Upcut Endmill',
            tool_type="endmill",
            diameter=3.175,
            flute_length=12.7,
            overall_length=38.1,
            flute_count=2,
            notes="General purpose wood/plastic endmill",
        )

        tool2 = Tool(
            tool_number=2,
            name='1/4" (6.35mm) 2-Flute Downcut Endmill',
            tool_type="endmill",
            diameter=6.35,
            flute_length=19.05,
            overall_length=50.8,
            flute_count=2,
            notes="Clean top surface cuts in plywood/laminates",
        )

        tool3 = Tool(
            tool_number=3,
            name='1/8" (3.175mm) High-Speed Steel Drill Bit',
            tool_type="drill",
            diameter=3.175,
            flute_length=25.4,
            overall_length=50.8,
            flute_count=2,
            notes="Straight plunge drilling",
        )

        tool4 = Tool(
            tool_number=4,
            name='1/4" 60-Degree V-Bit',
            tool_type="v-bit",
            diameter=6.35,
            flute_length=12.7,
            overall_length=38.1,
            flute_count=1,
            notes="Chamfering and lettering",
        )

        tool5 = Tool(
            tool_number=5,
            name='Single-Point 60° Thread Mill (4.5mm Cutter / 1/4" Shank)',
            tool_type="threadmill",
            diameter=4.5,
            flute_length=12.0,
            overall_length=50.8,
            flute_count=1,
            notes="Single-point thread milling for internal M6+ and 1/4\"+ threads or external threads",
        )

        tool6 = Tool(
            tool_number=6,
            name='1" (25.4mm) 3-Wing Surfacing & Spoilboard Flycutter',
            tool_type="endmill",
            diameter=25.4,
            flute_length=6.35,
            overall_length=50.8,
            flute_count=3,
            notes="Fast spoilboard flattening and stock facing",
        )

        db.session.add_all([tool1, tool2, tool3, tool4, tool5, tool6])
        db.session.flush()

        print("Seeding Material Presets (Easel-Calibrated for Belt-Driven Machines)...")
        presets = [
            # Tool 1: 1/8" (3.175mm) 2-Flute Upcut Endmill
            MaterialPreset(
                tool_id=tool1.id,
                material_name="Softwood (Pine)",
                spindle_speed=16000,
                feed_rate_xy=950.0,
                plunge_rate_z=230.0,
                pass_depth=1.0,
                notes="Easel safe baseline for pine/cedar/spruce on belt-driven X-Carve",
            ),
            MaterialPreset(
                tool_id=tool1.id,
                material_name="MDF / Plywood",
                spindle_speed=16000,
                feed_rate_xy=900.0,
                plunge_rate_z=230.0,
                pass_depth=1.0,
                notes="Clean cut without burning, keeps tool engagement within belt flex limits",
            ),
            MaterialPreset(
                tool_id=tool1.id,
                material_name="Hardwood (Oak/Maple)",
                spindle_speed=18000,
                feed_rate_xy=750.0,
                plunge_rate_z=200.0,
                pass_depth=0.8,
                notes="Prevents chatter and gantry flex on dense timbers",
            ),
            MaterialPreset(
                tool_id=tool1.id,
                material_name="Cast Acrylic",
                spindle_speed=16000,
                feed_rate_xy=650.0,
                plunge_rate_z=180.0,
                pass_depth=0.5,
                notes="Run at lowest router dial (Dial 1=16k RPM) to prevent chip melting",
            ),
            MaterialPreset(
                tool_id=tool1.id,
                material_name="6061 Aluminum",
                spindle_speed=16000,
                feed_rate_xy=250.0,
                plunge_rate_z=80.0,
                pass_depth=0.15,
                notes="Shallow conservative passes with lubrication to prevent bit grab",
            ),
            MaterialPreset(
                tool_id=tool1.id,
                material_name="360 Brass (Free-Cutting)",
                spindle_speed=16000,
                feed_rate_xy=300.0,
                plunge_rate_z=100.0,
                pass_depth=0.20,
                notes="Light cuts, excellent chip clearance",
            ),

            # Tool 2: 1/4" (6.35mm) 2-Flute Downcut Endmill
            MaterialPreset(
                tool_id=tool2.id,
                material_name="Softwood (Pine)",
                spindle_speed=16000,
                feed_rate_xy=1250.0,
                plunge_rate_z=250.0,
                pass_depth=1.8,
                notes="Easel conservative profile cut for 1/4in bit",
            ),
            MaterialPreset(
                tool_id=tool2.id,
                material_name="MDF / Plywood",
                spindle_speed=16000,
                feed_rate_xy=1200.0,
                plunge_rate_z=250.0,
                pass_depth=1.5,
                notes="Clean top surface in sheet stock",
            ),
            MaterialPreset(
                tool_id=tool2.id,
                material_name="Hardwood (Oak/Maple)",
                spindle_speed=18000,
                feed_rate_xy=950.0,
                plunge_rate_z=220.0,
                pass_depth=1.2,
                notes="Smooth finish without excessive cutting force",
            ),
            MaterialPreset(
                tool_id=tool2.id,
                material_name="Cast Acrylic",
                spindle_speed=16000,
                feed_rate_xy=850.0,
                plunge_rate_z=200.0,
                pass_depth=0.8,
                notes="Dial 1 minimum speed",
            ),
            MaterialPreset(
                tool_id=tool2.id,
                material_name="6061 Aluminum",
                spindle_speed=16000,
                feed_rate_xy=350.0,
                plunge_rate_z=100.0,
                pass_depth=0.25,
                notes="Shallow skimming passes",
            ),
            MaterialPreset(
                tool_id=tool2.id,
                material_name="360 Brass (Free-Cutting)",
                spindle_speed=16000,
                feed_rate_xy=420.0,
                plunge_rate_z=120.0,
                pass_depth=0.30,
                notes="Free-cutting brass with 1/4in endmill",
            ),

            # Tool 3: 1/8" (3.175mm) Drill Bit
            MaterialPreset(
                tool_id=tool3.id,
                material_name="Softwood (Pine)",
                spindle_speed=16000,
                feed_rate_xy=0.0,
                plunge_rate_z=250.0,
                pass_depth=3.0,
                notes="Straight plunge or peck drilling",
            ),
            MaterialPreset(
                tool_id=tool3.id,
                material_name="MDF / Plywood",
                spindle_speed=16000,
                feed_rate_xy=0.0,
                plunge_rate_z=230.0,
                pass_depth=3.0,
            ),
            MaterialPreset(
                tool_id=tool3.id,
                material_name="Hardwood (Oak)",
                spindle_speed=16000,
                feed_rate_xy=0.0,
                plunge_rate_z=200.0,
                pass_depth=2.0,
            ),
            MaterialPreset(
                tool_id=tool3.id,
                material_name="6061 Aluminum",
                spindle_speed=16000,
                feed_rate_xy=0.0,
                plunge_rate_z=80.0,
                pass_depth=0.8,
                notes="Peck drilling with frequent retracts",
            ),
            MaterialPreset(
                tool_id=tool3.id,
                material_name="360 Brass (Free-Cutting)",
                spindle_speed=16000,
                feed_rate_xy=0.0,
                plunge_rate_z=100.0,
                pass_depth=1.0,
            ),

            # Tool 4: 1/4" 60-Degree V-Bit
            MaterialPreset(
                tool_id=tool4.id,
                material_name="Hardwood (Oak/Walnut)",
                spindle_speed=18000,
                feed_rate_xy=750.0,
                plunge_rate_z=200.0,
                pass_depth=0.5,
                notes="Crisp text engraving in hardwood",
            ),
            MaterialPreset(
                tool_id=tool4.id,
                material_name="Softwood (Pine)",
                spindle_speed=16000,
                feed_rate_xy=850.0,
                plunge_rate_z=220.0,
                pass_depth=0.8,
                notes="Clean V-carving in softwoods",
            ),
            MaterialPreset(
                tool_id=tool4.id,
                material_name="Cast Acrylic",
                spindle_speed=16000,
                feed_rate_xy=600.0,
                plunge_rate_z=180.0,
                pass_depth=0.3,
                notes="Clean plastic sign engraving without melting",
            ),
            MaterialPreset(
                tool_id=tool4.id,
                material_name="360 Brass (Free-Cutting)",
                spindle_speed=16000,
                feed_rate_xy=320.0,
                plunge_rate_z=100.0,
                pass_depth=0.15,
                notes="Chamfering and fine lettering in brass plaques and badges",
            ),
            MaterialPreset(
                tool_id=tool4.id,
                material_name="6061 Aluminum",
                spindle_speed=16000,
                feed_rate_xy=250.0,
                plunge_rate_z=80.0,
                pass_depth=0.10,
                notes="Light chamfering and engraving in aluminum plates",
            ),

            # Tool 5: Single-Point Thread Mill
            MaterialPreset(
                tool_id=tool5.id,
                material_name="6061 Aluminum",
                spindle_speed=16000,
                feed_rate_xy=200.0,
                plunge_rate_z=100.0,
                pass_depth=0.20,
                notes="Helical thread milling in aluminum with safe conservative feed",
            ),
            MaterialPreset(
                tool_id=tool5.id,
                material_name="360 Brass (Free-Cutting)",
                spindle_speed=16000,
                feed_rate_xy=250.0,
                plunge_rate_z=120.0,
                pass_depth=0.25,
                notes="Excellent crisp thread formation in free-cutting brass",
            ),
            MaterialPreset(
                tool_id=tool5.id,
                material_name="Hardwood (Oak/Maple)",
                spindle_speed=18000,
                feed_rate_xy=320.0,
                plunge_rate_z=150.0,
                pass_depth=0.40,
                notes="Thread milling wooden fixtures and threaded inserts",
            ),
            MaterialPreset(
                tool_id=tool5.id,
                material_name="Delrin / Acetal",
                spindle_speed=16000,
                feed_rate_xy=380.0,
                plunge_rate_z=150.0,
                pass_depth=0.40,
                notes="Very clean plastic internal threads",
            ),

            # Tool 6: 1" (25.4mm) Surfacing Flycutter
            MaterialPreset(
                tool_id=tool6.id,
                material_name="MDF / Spoilboard",
                spindle_speed=16000,
                feed_rate_xy=1400.0,
                plunge_rate_z=200.0,
                pass_depth=0.40,
                notes="Safe spoilboard resurfacing without gantry shudder or stepper stall",
            ),
            MaterialPreset(
                tool_id=tool6.id,
                material_name="Softwood (Pine)",
                spindle_speed=16000,
                feed_rate_xy=1300.0,
                plunge_rate_z=200.0,
                pass_depth=0.35,
                notes="Slab flattening on belt-driven machine",
            ),
            MaterialPreset(
                tool_id=tool6.id,
                material_name="Hardwood (Oak)",
                spindle_speed=16000,
                feed_rate_xy=1100.0,
                plunge_rate_z=150.0,
                pass_depth=0.25,
                notes="Stock facing and slab flattening with light passes",
            ),
        ]


        db.session.add_all(presets)
        db.session.commit()
        print("Database seeded successfully!")

if __name__ == "__main__":
    seed_database()
