from app import create_app, db


def test_home_page():
    app = create_app(
        {"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"}
    )

    with app.app_context():
        db.create_all()
        with app.test_client() as client:
            response = client.get("/")

        assert response.status_code == 200
        assert b"Lab Equipment Booking System is running!" in response.data

        db.session.remove()
        db.drop_all()
        db.engine.dispose()
