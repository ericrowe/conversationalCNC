import enum
from datetime import datetime, timezone
from typing import Optional
from flask_sqlalchemy import SQLAlchemy
from ..postprocessors.router_speed_tables import (
    ROUTER_SPECS,
    get_router_spec,
    interpolate_router_dial,
    normalize_router_model,
)

db = SQLAlchemy()


class SpindleType(str, enum.Enum):
    MANUAL_ROUTER = "manual_router"
    ROUTER = "router"
    VFD_AUTO = "vfd_auto"
    VFD_SPINDLE = "vfd_spindle"

    @classmethod
    def is_manual(cls, value: Optional[str]) -> bool:
        if not value:
            return True
        val = str(value).lower().strip().replace("-", "_")
        return val in ("manual_router", "router", "manual", "trim_router", "dewalt", "makita", "bosch")

    @classmethod
    def is_vfd(cls, value: Optional[str]) -> bool:
        return not cls.is_manual(value)


class RouterModel(str, enum.Enum):
    DEWALT_DWP611 = "dewalt_611"
    MAKITA_RT0701C = "makita_rt0701"
    BOSCH_COLT = "bosch_colt"
    GENERIC = "generic"


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
        k: v.dial_points for k, v in ROUTER_SPECS.items()
    }

    def get_dial_for_rpm(self, target_rpm: int):
        """Returns (dial_setting, mapped_rpm) for router models."""
        if not SpindleType.is_manual(self.spindle_type) or not self.router_model:
            return None, target_rpm
        info = interpolate_router_dial(self.router_model, target_rpm)
        return info.dial_setting, info.actual_rpm

    def to_dict(self):
        dial_options = None
        if SpindleType.is_manual(self.spindle_type):
            spec = get_router_spec(self.router_model)
            dial_options = [
                {"dial": d, "rpm": rpm}
                for d, rpm in sorted(spec.dial_points.items())
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
