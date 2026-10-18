from flask import Flask, render_template
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
login_manager = LoginManager()


def create_app(test_config=None):
    app = Flask(__name__)

    app.config["SECRET_KEY"] = "local-development-key"
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///lab_equipment.db"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    if test_config:
        app.config.update(test_config)

    db.init_app(app)

    login_manager.login_view = "auth.login"
    login_manager.login_message = "Please log in to access this page."
    login_manager.login_message_category = "info"
    login_manager.init_app(app)

    from app import models
    from app.auth import auth_bp
    from app.bookings import bookings_bp

    @login_manager.user_loader
    def load_user(user_id):
        try:
            return db.session.get(models.User, int(user_id))
        except (ValueError, TypeError):
            return None

    app.register_blueprint(auth_bp)
    app.register_blueprint(bookings_bp)

    with app.app_context():
        db.create_all()

    @app.errorhandler(403)
    def forbidden_error(error):
        return render_template("errors/403.html"), 403

    @app.errorhandler(401)
    def unauthorized_error(error):
        return render_template("errors/401.html"), 401

    @app.route("/")
    def home():
        return "Lab Equipment Booking System is running!"

    return app