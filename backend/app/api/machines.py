from flask import Blueprint, request, jsonify
from pydantic import ValidationError
from ..models import db, MachineProfile
from ..schemas import MachineProfileCreateSchema, MachineProfileUpdateSchema

machines_bp = Blueprint("machines", __name__, url_prefix="/api/machines")

@machines_bp.route("", methods=["GET"])
def get_machines():
    profiles = MachineProfile.query.order_by(MachineProfile.id).all()
    return jsonify([p.to_dict() for p in profiles]), 200

@machines_bp.route("/active", methods=["GET"])
def get_active_machine():
    profile = MachineProfile.query.filter_by(is_active=True).first()
    if not profile:
        profile = MachineProfile.query.first()
    if not profile:
        return jsonify({"error": "No machine profiles found"}), 404
    return jsonify(profile.to_dict()), 200

@machines_bp.route("/<int:profile_id>/activate", methods=["POST"])
def activate_machine(profile_id):
    profile = db.session.get(MachineProfile, profile_id)
    if not profile:
        return jsonify({"error": f"Machine profile {profile_id} not found"}), 404
    
    # Deactivate all others
    MachineProfile.query.update({MachineProfile.is_active: False})
    profile.is_active = True
    db.session.commit()
    return jsonify(profile.to_dict()), 200

@machines_bp.route("", methods=["POST"])
def create_machine():
    data = request.get_json() or {}
    try:
        validated = MachineProfileCreateSchema(**data)
    except ValidationError as e:
        error_details = [{"loc": err.get("loc"), "msg": err.get("msg"), "type": err.get("type")} for err in e.errors()]
        return jsonify({"error": "Validation error", "details": error_details}), 400

    if validated.is_active:
        MachineProfile.query.update({MachineProfile.is_active: False})

    profile = MachineProfile(**validated.model_dump())
    db.session.add(profile)
    db.session.commit()
    return jsonify(profile.to_dict()), 201

@machines_bp.route("/<int:profile_id>", methods=["GET"])
def get_machine(profile_id):
    profile = db.session.get(MachineProfile, profile_id)
    if not profile:
        return jsonify({"error": f"Machine profile {profile_id} not found"}), 404
    return jsonify(profile.to_dict()), 200

@machines_bp.route("/<int:profile_id>", methods=["PUT"])
def update_machine(profile_id):
    profile = db.session.get(MachineProfile, profile_id)
    if not profile:
        return jsonify({"error": f"Machine profile {profile_id} not found"}), 404

    data = request.get_json() or {}
    try:
        validated = MachineProfileUpdateSchema(**data)
    except ValidationError as e:
        error_details = [{"loc": err.get("loc"), "msg": err.get("msg"), "type": err.get("type")} for err in e.errors()]
        return jsonify({"error": "Validation error", "details": error_details}), 400

    update_data = validated.model_dump(exclude_unset=True)
    if update_data.get("is_active"):
        MachineProfile.query.filter(MachineProfile.id != profile_id).update({MachineProfile.is_active: False})

    for key, value in update_data.items():
        setattr(profile, key, value)

    db.session.commit()
    return jsonify(profile.to_dict()), 200

@machines_bp.route("/<int:profile_id>", methods=["DELETE"])
def delete_machine(profile_id):
    profile = db.session.get(MachineProfile, profile_id)
    if not profile:
        return jsonify({"error": f"Machine profile {profile_id} not found"}), 404

    db.session.delete(profile)
    db.session.commit()
    return jsonify({"message": f"Machine profile {profile_id} deleted successfully"}), 200
