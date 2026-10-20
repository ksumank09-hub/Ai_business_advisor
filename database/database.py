"""
database/database.py
---------------------
Creates the single SQLAlchemy() instance shared across the whole app.
Import `db` from here in models.py and in app.py — never create a
second SQLAlchemy() instance, or Flask-SQLAlchemy will break.
"""

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def init_db(app):
    """Attach db to the Flask app and create tables if they don't exist."""
    db.init_app(app)
    with app.app_context():
        # Import models here (not at module top) to avoid circular imports
        from database import models  # noqa: F401
        db.create_all()
        try:
            from database.models import User, Conversation
            sanjan = User.query.filter_by(email="sanjankumarsk74@gmail.com").first()
            if sanjan and Conversation.query.filter_by(user_id=sanjan.id).count() == 0:
                orphan_convs = Conversation.query.filter(Conversation.user_id != sanjan.id).all()
                for c in orphan_convs:
                    c.user_id = sanjan.id
                db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(f"Migration notice: {e}")
