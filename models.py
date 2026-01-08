# models.py
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

favorites = db.Table(
    "favorites",
    db.Column("user_id", db.Integer, db.ForeignKey("user.id"), primary_key=True),
    db.Column("pattern_id", db.Integer, db.ForeignKey("pattern.id"), primary_key=True),
)

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    username = db.Column(db.String(50), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)

    favorites = db.relationship(
        "Pattern",
        secondary=favorites,
        backref="liked_by",
        lazy="select",
    )

    def set_password(self, pw: str) -> None:
        self.password_hash = generate_password_hash(pw)

    def check_password(self, pw: str) -> bool:
        return check_password_hash(self.password_hash, pw)

class Pattern(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(180), nullable=False, index=True)
    craft = db.Column(db.String(20), nullable=False)  # "knit" or "crochet"
    difficulty = db.Column(db.String(20))             # optional
    instructions_md = db.Column(db.Text, nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    author = db.relationship("User", backref="patterns")
    image_path = db.Column(db.String(255))

class PatternRating(db.Model):
    __tablename__ = "pattern_rating"
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), primary_key=True)
    pattern_id = db.Column(db.Integer, db.ForeignKey("pattern.id"), primary_key=True)
    rating = db.Column(db.Integer, nullable=False)  # 1..5
    created_at = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now(), nullable=False)

    user = db.relationship("User", backref="pattern_ratings")
    pattern = db.relationship("Pattern", backref="ratings")

class PatternView(db.Model):
    __tablename__ = "pattern_view"
    id         = db.Column(db.Integer, primary_key=True)
    pattern_id = db.Column(db.Integer, db.ForeignKey("pattern.id"), index=True, nullable=False)
    user_id    = db.Column(db.Integer, db.ForeignKey("user.id"), index=True, nullable=True)
    created_at = db.Column(db.DateTime, server_default=db.func.now(), index=True, nullable=False)

    pattern = db.relationship("Pattern", backref="views")
    user    = db.relationship("User", backref="pattern_views")
