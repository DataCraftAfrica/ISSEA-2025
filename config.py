import os

class Config:
    # Récupère la variable d'environnement (Render fournit DATABASE_URL)
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "postgresql://issea_bd_user:lXY4PBK3bFXaiAw1bBOpvWK8kA2UEpoA@dpg-d379mv7fte5s73b33uug-a.oregon-postgres.render.com/issea_bd")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = os.environ.get("SECRET_KEY", "upersecret")  # pour les sessions
