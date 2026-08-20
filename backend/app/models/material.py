from datetime import datetime, timezone
from .machine import db

class MaterialPreset(db.Model):
    __tablename__ = "material_presets"

    id = db.Column(db.Integer, primary_key=True)
    material_name = db.Column(db.String(100), nullable=False)  # e.g., "MDF", "6061 Aluminum", "Hardwood (Oak)"
    tool_id = db.Column(db.Integer, db.ForeignKey("tools.id"), nullable=False)
    spindle_speed = db.Column(db.Integer, nullable=False, default=16000)  # RPM
    feed_rate_xy = db.Column(db.Float, nullable=False, default=1000.0)  # mm/min
    plunge_rate_z = db.Column(db.Float, nullable=False, default=300.0)  # mm/min
    pass_depth = db.Column(db.Float, nullable=False, default=1.5)  # mm
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    tool = db.relationship("Tool", back_populates="material_presets")

    def to_dict(self):
        return {
            "id": self.id,
            "material_name": self.material_name,
            "tool_id": self.tool_id,
            "spindle_speed": self.spindle_speed,
            "feed_rate_xy": self.feed_rate_xy,
            "plunge_rate_z": self.plunge_rate_z,
            "pass_depth": self.pass_depth,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
