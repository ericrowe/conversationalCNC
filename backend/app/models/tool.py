from datetime import datetime, timezone
from .machine import db

class Tool(db.Model):
    __tablename__ = "tools"

    id = db.Column(db.Integer, primary_key=True)
    tool_number = db.Column(db.Integer, nullable=False, unique=True)
    name = db.Column(db.String(100), nullable=False)
    tool_type = db.Column(db.String(50), nullable=False, default="endmill")  # endmill, drill, v-bit, chamfer, threadmill
    diameter = db.Column(db.Float, nullable=False)  # in mm
    flute_length = db.Column(db.Float, nullable=True)  # in mm
    overall_length = db.Column(db.Float, nullable=True)  # in mm
    flute_count = db.Column(db.Integer, default=2)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    material_presets = db.relationship(
        "MaterialPreset", back_populates="tool", cascade="all, delete-orphan", lazy="joined"
    )

    def to_dict(self, include_presets=True):
        data = {
            "id": self.id,
            "tool_number": self.tool_number,
            "name": self.name,
            "tool_type": self.tool_type,
            "diameter": self.diameter,
            "flute_length": self.flute_length,
            "overall_length": self.overall_length,
            "flute_count": self.flute_count,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_presets:
            data["material_presets"] = [p.to_dict() for p in self.material_presets]
        return data
