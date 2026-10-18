from flask import Flask
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def create_app(test_config=None):
    app = Flask(__name__)

    app.config["SECRET_KEY"] = "local-development-key"
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///lab_equipment.db"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    if test_config:
        app.config.update(test_config)

    db.init_app(app)

    from app import models  # noqa: F401
    from app.auth import auth_bp

    app.register_blueprint(auth_bp)

    with app.app_context():
        db.create_all()

    @app.route("/")
    def home():
        return "Lab Equipment Booking System is running!"

    return app