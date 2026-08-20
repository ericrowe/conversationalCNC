import pytest
from app import create_app
from app.config import TestingConfig
from app.models import db, MachineProfile, Tool, MaterialPreset

@pytest.fixture
def app():
    app = create_app(TestingConfig)
    with app.app_context():
        db.create_all()

        # Seed test data
        xcarve = MachineProfile(
            name="Test X-Carve",
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
        )

        shapeoko = MachineProfile(
            name="Test Shapeoko",
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
        )

        tool = Tool(
            tool_number=1,
            name="1/8in Drill Bit",
            tool_type="drill",
            diameter=3.175,
            flute_length=25.4,
            overall_length=50.8,
        )

        db.session.add_all([xcarve, shapeoko, tool])
        db.session.flush()

        preset = MaterialPreset(
            tool_id=tool.id,
            material_name="MDF",
            spindle_speed=12000,
            feed_rate_xy=0.0,
            plunge_rate_z=400.0,
            pass_depth=5.0,
        )
        db.session.add(preset)
        db.session.commit()

        yield app

        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()
