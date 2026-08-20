import os
from flask import Flask, jsonify
from flask_cors import CORS
from .config import Config, DevelopmentConfig
from .models import db
from .api import (
    machines_bp,
    tools_bp,
    materials_bp,
    generate_bp,
    transform_bp,
    calculator_bp,
    probing_bp,
)
from .web import web_bp

def create_app(config_class=DevelopmentConfig):
    app_dir = os.path.dirname(os.path.abspath(__file__))
    templates_dir = os.path.join(app_dir, "templates")
    static_dir = os.path.join(app_dir, "static")

    app = Flask(
        __name__,
        template_folder=templates_dir,
        static_folder=static_dir
    )
    app.config.from_object(config_class)


    # Initialize extensions
    db.init_app(app)
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    # Register blueprints
    app.register_blueprint(machines_bp)
    app.register_blueprint(tools_bp)
    app.register_blueprint(materials_bp)
    app.register_blueprint(generate_bp)
    app.register_blueprint(transform_bp)
    app.register_blueprint(calculator_bp)
    app.register_blueprint(probing_bp)
    app.register_blueprint(web_bp)




    # Health check route
    @app.route("/api/health", methods=["GET"])
    def health_check():
        return jsonify({
            "status": "online",
            "service": "Conversational CNC Controller Backend",
            "version": "0.1.0"
        }), 200

    # Auto-create tables if they don't exist
    with app.app_context():
        db.create_all()

    return app
