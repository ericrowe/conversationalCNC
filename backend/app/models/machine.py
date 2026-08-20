from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class MachineProfile(db.Model):
    __tablename__ = "machine_profiles"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    is_active = db.Column(db.Boolean, default=False, nullable=False)
    controller_dialect = db.Column(db.String(50), default="grbl", nullable=False)
    work_area_x = db.Column(db.Float, nullable=False, default=750.0)
    work_area_y = db.Column(db.Float, nullable=False, default=750.0)
    work_area_z = db.Column(db.Float, nullable=False, default=65.0)
    max_feed_xy = db.Column(db.Float, nullable=False, default=8000.0)
    max_feed_z = db.Column(db.Float, nullable=False, default=500.0)
    rapid_feed_rate = db.Column(db.Float, nullable=False, default=5000.0)
    spindle_type = db.Column(db.String(50), nullable=False, default="router")  # "router" or "vfd_spindle"
    router_model = db.Column(db.String(50), nullable=True, default="dewalt_611")  # "dewalt_611", "makita_rt0701", "generic"
    min_spindle_rpm = db.Column(db.Integer, nullable=False, default=16000)
    max_spindle_rpm = db.Column(db.Integer, nullable=False, default=27000)
    spindle_dwell_seconds = db.Column(db.Float, nullable=False, default=2.0)
    z_probe_thickness = db.Column(db.Float, nullable=False, default=14.85)
    safe_z_retract = db.Column(db.Float, nullable=False, default=5.0)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    ROUTER_DIAL_MAPS = {
        "dewalt_611": {
            1: 16000,
            2: 18200,
            3: 20400,
            4: 22600,
            5: 24800,
            6: 27000,
        },
        "makita_rt0701": {
            1: 10000,
            2: 12000,
            3: 17000,
            4: 22000,
            5: 27000,
            6: 30000,
        },
    }

    def get_dial_for_rpm(self, target_rpm: int):
        """Returns (dial_number, mapped_rpm) for router models."""
        if self.spindle_type != "router" or not self.router_model:
            return None, target_rpm
        dial_map = self.ROUTER_DIAL_MAPS.get(self.router_model)
        if not dial_map:
            return None, target_rpm
        
        # Find closest dial setting
        closest_dial = min(dial_map.keys(), key=lambda d: abs(dial_map[d] - target_rpm))
        return closest_dial, dial_map[closest_dial]

    def to_dict(self):
        dial_options = None
        if self.spindle_type == "router" and self.router_model in self.ROUTER_DIAL_MAPS:
            dial_options = [
                {"dial": d, "rpm": rpm}
                for d, rpm in self.ROUTER_DIAL_MAPS[self.router_model].items()
            ]

        return {
            "id": self.id,
            "name": self.name,
            "is_active": self.is_active,
            "controller_dialect": self.controller_dialect,
            "spindle_type": self.spindle_type,
            "router_model": self.router_model,
            "router_dial_options": dial_options,
            "work_area_x": self.work_area_x,
            "work_area_y": self.work_area_y,
            "work_area_z": self.work_area_z,
            "max_feed_xy": self.max_feed_xy,
            "max_feed_z": self.max_feed_z,
            "rapid_feed_rate": self.rapid_feed_rate,
            "min_spindle_rpm": self.min_spindle_rpm,
            "max_spindle_rpm": self.max_spindle_rpm,
            "spindle_dwell_seconds": self.spindle_dwell_seconds,
            "z_probe_thickness": self.z_probe_thickness,
            "safe_z_retract": self.safe_z_retract,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
