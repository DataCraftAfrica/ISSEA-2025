from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class Etudiant(db.Model):
    __tablename__ = "etudiants"

    email = db.Column(db.String(120), primary_key=True, unique=True, nullable=False)
    nom = db.Column(db.String(100), nullable=False)
    prenoms = db.Column(db.String(150), nullable=False)
    classe = db.Column(db.String(50), nullable=False)
    mpd = db.Column(db.String(200), nullable=False)  # mot de passe haché

    def set_password(self, password):
        self.mpd = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.mpd, password)
