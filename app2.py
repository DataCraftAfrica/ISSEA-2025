from flask import Flask
from config import Config
from models import db, Etudiant

app = Flask(__name__)
app.config.from_object(Config)

# Initialisation de SQLAlchemy
db.init_app(app)

@app.route("/")
def index():
    return "Bienvenue sur l'application ISSEA-CEMAC 🎓"



@app.route("/tables")
def show_tables():
    inspector = db.inspect(db.engine)
    tables = inspector.get_table_names()
    return {"tables": tables}

if __name__ == "__main__":
    app.run(debug=True)
