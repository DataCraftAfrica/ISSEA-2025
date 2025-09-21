from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory,  jsonify, send_file, session, make_response, current_app
#from flask_mysqldb import MySQL
from flask_mail import Mail, Message
from werkzeug.utils import secure_filename
import psycopg2
import random
import string
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
import os
from werkzeug.security import check_password_hash, generate_password_hash
# models.py
from flask_sqlalchemy import SQLAlchemy
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
import pandas as pd
from werkzeug.security import generate_password_hash
from config import Config
from models import db, Etudiant
import os
from io import BytesIO
import json
import base64


###
### Bibliotheque

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY")
app.config.from_object(Config)
db.init_app(app)

# Mets directement ta config ici
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL") or "sqlite:///local.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False



# Configuration du serveur mail
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'appsrf42@gmail.com'  # Remplace par ton email
app.config['MAIL_PASSWORD'] = 'ywwp pevr iewf kwog '  # Génère un mot de passe d'application si tu utilises Gmail

mail = Mail(app)

classes = ['LGTSD', 'L2BD', 'MAP2', 'MSA2', 'M2SA', 'MDSMS2']

# 🔑 Fonction pour générer un mot de passe aléatoire
def generate_random_password(length=8):
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(length))


# Connexion Google Sheets
def get_gsheet_etudiant():
    scope = ["https://spreadsheets.google.com/feeds",
             "https://www.googleapis.com/auth/drive"]
    
    # 🔑 récupérer le JSON depuis l'env
    creds_json = os.environ.get("GOOGLE_CREDENTIALS")
    creds_dict = json.loads(base64.b64decode(creds_json))  

    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    
    # ⚠️ on ouvre le fichier Google Sheets 
    spreadsheet = client.open_by_key("1n4M4aMY6dv2LaYPnwW-LjRpfF0PDcNH4Qv6O_j7v5wk")
    return spreadsheet


def get_gsheet_gestion():
    scope = ["https://spreadsheets.google.com/feeds",
             "https://www.googleapis.com/auth/drive"]
    
    # 🔑 récupérer le JSON depuis l'env
    creds_json = os.environ.get("GOOGLE_CREDENTIALS")
    creds_dict = json.loads(base64.b64decode(creds_json))  

    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    
    # ⚠️ on ouvre le fichier Google Sheets 
    spreadsheet = client.open_by_key("1l2YSbJOsHo5tIPHfBWpsSxPs0qd3IxF0Xasui0xJ2oc")
    return spreadsheet


@app.route('/', methods=['GET', 'POST'])
def connexion():


    return render_template('index.html')


@app.route('/admin', methods=['GET', 'POST'])
def admin():

    if 'username' in session and session["user_info"]["classe"] == 'super@user':

        return render_template('admin.html', classe=classes)

    return redirect(url_for('connexion'))

@app.route("/get_enseignants")
def get_enseignants():

    spreadsheet = get_gsheet_gestion()
    worksheet = spreadsheet.worksheet("Enseignant")

    enseignants = worksheet.col_values(1)  # on suppose que les noms sont dans la 1ère colonne
    enseignants = [e for e in enseignants if e]  # retirer les vides

    return jsonify(enseignants)


@app.route("/update_encadreur", methods=["POST"])
def update_encadreur():
    data = request.get_json()
    email = data.get("email")
    nom = data.get("nom")
    prenoms = data.get("prenoms")
    encadreur = data.get("encadreur")
    classe = data.get("classe")
    print('le voici: ', email)
    print('lui egalement: ', encadreur)
    spreadsheet = get_gsheet_etudiant()
    worksheet = spreadsheet.worksheet(classe)

    # trouver la ligne de l'étudiant par email
    data_rows = worksheet.get_all_records()
    for i, row in enumerate(data_rows, start=2):  # +2 car ligne 1 = header
        if row.get("Email") == email:
            worksheet.update_cell(i, list(row.keys()).index("Encadreur_Academique") + 1, encadreur)

            subject = 'Information !'

            body = f"""Hello {nom} {prenoms}, \n Un encadreur academique vous a été affecté, veuillez vous connecter pour en savoir plus. \n DataCraft AFRICA, le progrès n'attend pas
            """

            # Création du message
            msg = Message(subject, sender='appsrf42@gmail.com', recipients=[email])
            msg.body = body

            mail.send(msg)
            return jsonify({"message": f"Affectation mise à jour pour {email}"})

    return jsonify({"message": "Email non trouvé"}), 404


@app.route("/get_etudiants/<classe>")
def get_etudiants(classe):
    # 1. Récupérer les étudiants de la classe depuis PostgreSQL
    etudiants = Etudiant.query.filter_by(classe=classe).all()

    # 2. Charger la feuille Google Sheet correspondant à la classe
    spreadsheet = get_gsheet_etudiant()
    worksheet = spreadsheet.worksheet(classe)  # ici on suppose que chaque classe = onglet
    all_rows = worksheet.get_all_records()  # renvoie une liste de dicts [{}, {}, ...]

    # 3. Indexer la Google Sheet par email (clé unique)
    gsheet_dict = {row["Email"]: row for row in all_rows if "Email" in row}

    # 4. Construire le résultat fusionné
    result = []
    for e in etudiants:
        gsheet_data = gsheet_dict.get(e.email, {})  # récupérer les infos Google Sheet par email

        result.append({
            "nom": e.nom,
            "prenoms": e.prenoms,
            "theme": gsheet_data.get("Theme", ""),
            "encadreur_pro": gsheet_data.get("Encadreur_Professionnel", ""),
            "tel_encadreur": gsheet_data.get("Telephone", ""),
            "structure": gsheet_data.get("Structure_Accueil", ""),
            "questions": gsheet_data.get("Questions_recherche", ""),
            "base_dispo": gsheet_data.get("BD", ""),
            "encadreur_acad": gsheet_data.get("Encadreur_Academique", ""),
            "email": e.email
        })

    return jsonify(result)


@app.route("/download_excel/<classe>")
def download_excel(classe):
    try:
        data = fetch_combined_data(classe)

        # Sécurité : si aucune donnée -> 204 No Content (JS gère l'alerte)
        if not data:
            return make_response("", 204)

        # Convertir en DataFrame
        df = pd.DataFrame(data)

        # Option : réordonner / renommer les colonnes pour l'export
        cols_order = ["nom", "prenoms", "email", "theme", "encadreur_pro",
                      "tel_encadreur", "structure", "questions", "base_dispo", "encadreur_acad"]
        cols_present = [c for c in cols_order if c in df.columns]
        df = df[cols_present]

        # Générer Excel en mémoire
        output = BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            # nom de feuille <= 31 caractères (Excel limitation)
            sheetname = classe[:31]
            df.to_excel(writer, index=False, sheet_name=sheetname)
        output.seek(0)

        # Envoyer le fichier
        return send_file(
            output,
            as_attachment=True,
            download_name=f"infos_{classe}.xlsx",
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    except Exception:
        current_app.logger.exception("Erreur download_excel")
        return jsonify({"error": "Erreur serveur lors de la génération du fichier"}), 500

def update_etudiant(worksheet, email, infos):
    """
    Met à jour les infos d'un étudiant dans la Google Sheet
    en se basant sur son email (clé unique).
    
    :param worksheet: feuille Google Sheet (gspread)
    :param email: adresse email de l'étudiant (string)
    :param infos: dictionnaire avec toutes les infos de l'étudiant 
                  (ex: {"Nom": "...", "Prénom": "...", "Classe": "...", "Theme": "...", ...})
    """
    # Récupérer toutes les lignes
    data = worksheet.get_all_values()
    headers = data[0]   # première ligne = noms de colonnes
    
    # Chercher la colonne Email
    email_col_index = headers.index("Email") + 1  # +1 car gspread est 1-based
    
    # Récupérer toutes les adresses email
    emails = worksheet.col_values(email_col_index)
    
    # Trouver la ligne correspondant à l'email
    if email in emails:
        row_index = emails.index(email) + 1  # ligne réelle dans la sheet

        # Construire la nouvelle ligne avec les infos reçues
        new_row = []
        for col in headers:
            if col == "Email":
                new_row.append(email)  # garder l’email inchangé
            else:
                new_row.append(infos.get(col, ""))  # prendre la nouvelle valeur ou vide si absente
        
        # Écrire toute la ligne d'un coup
        worksheet.update(f"A{row_index}:{chr(64+len(headers))}{row_index}", [new_row])
        print(f"Infos mises à jour pour {email}")
    else:
        print("Email non trouvé dans la feuille")


@app.route('/formulaire/<Etudiant>', methods=['GET', 'POST'])
def formulaire(Etudiant):

    if 'username' in session:

        spreadsheet = get_gsheet_etudiant()
        print('la classe: ', session["user_info"]["classe"])

        # Choisir l’onglet en fonction de la classe (ex: "ClasseA", "ClasseB")
        worksheet = spreadsheet.worksheet(session["user_info"]["classe"])

        # Récupérer toutes les lignes sous forme de dictionnaires
        data = worksheet.get_all_values()

        df = pd.DataFrame(data[1:], columns=data[0])  
        print("Colonnes dispo dans df:", df.columns)
        df = df[df['Email'] == session["user_info"]["email"]]

        if df.empty:
            modif = False
        else:
            modif = True

        if request.method == "POST":

            # Infos mémoire (Google Sheets)
            theme = request.form["theme"]
            structure = request.form["structure"]
            encadreur = request.form["encadreur_pro"]
            tel_encadreur = request.form["tel_encadreur_pro"]
            questions = request.form["questions"]
            base_dispo = request.form["base_dispo"]

            email = session["user_info"]["email"]

            action = request.form.get('action')

            if action == 'Enregistrer':

                #sheet = get_gsheet_etudiant()
                worksheet.append_row([email, theme, structure, encadreur, tel_encadreur, questions, base_dispo])

                flash("Vos informations ont été enregistrées avec succès 🎉", "success")

            if action == 'Modifier':

                infos = {
                    'Theme': theme,
                    'Structure_Accueil': structure,
                    'Encadreur_Professionnel': encadreur,
                    'Telephone': tel_encadreur,
                    'Questions_recherche': questions, 
                    'BD': base_dispo
                }

                 # Mettre à jour la ligne
                update_etudiant(worksheet, email, infos)

                flash("Vos informations ont été mises à jour avec succès !", "success")

            #print('la session est: ', session["username"])

            return redirect(url_for("formulaire", Etudiant=session["username"]))


        return render_template('saisie.html', adresse=session["username"], action = modif)
    
    return redirect(url_for('connexion'))



@app.route('/register/<Etudiant>', methods=['GET', 'POST'])
def register(Etudiant):

    # Sécurité : empêcher un "super@user" de passer ici
    if session["user_info"]["classe"] == "super@user":
        return redirect(url_for("admin"))

    if 'username' in session:


        spreadsheet = get_gsheet_etudiant()
        print('la classe: ', session["user_info"]["classe"])

        # Choisir l’onglet en fonction de la classe (ex: "ClasseA", "ClasseB")
        worksheet = spreadsheet.worksheet(session["user_info"]["classe"])

        # Récupérer toutes les lignes sous forme de dictionnaires
        data = worksheet.get_all_values()

        df = pd.DataFrame(data[1:], columns=data[0])  
        print("Colonnes dispo dans df:", df.columns)
        df = df[df['Email'] == session["user_info"]["email"]]

        if df.empty:
            valeur = {}
            valeur["nom"] = session["user_info"]["nom"]
            valeur["prenoms"] = session["user_info"]["prenoms"]
            valeur["classe"] = session["user_info"]["classe"]
        else:
            # On prend la première ligne
            ligne = df.iloc[0]

            valeur = {}
            valeur["nom"] = session["user_info"]["nom"]
            valeur["prenoms"] = session["user_info"]["prenoms"]
            valeur["classe"] = session["user_info"]["classe"]
            valeur['theme'] = ligne['Theme']
            valeur['structure'] = ligne['Structure_Accueil']
            valeur['Enca_pro'] = ligne['Encadreur_Professionnel']
            valeur['question'] = ligne['Questions_recherche']
            valeur['Enca_Aca'] = ligne['Encadreur_Academique']


        return render_template('Etudiant.html', user = session["user_info"]["prenoms"], valeurs = valeur, adresse=session["username"])
    
    redirect(url_for('connexion'))


@app.route('/login', methods=['GET', 'POST'])
def login():

    if request.method == "POST":

        email = request.form["email"]
        mpd = request.form["mpd"]

        # Vérifier si l'utilisateur existe
        etu = Etudiant.query.filter_by(email=email).first()

        if etu:
            # Vérification du mot de passe haché
            if check_password_hash(etu.mpd, mpd):
                # Création de la session
                session["username"] = etu.email  

                # Stockage des infos dans un dictionnaire
                user_info = {
                    "email": etu.email,
                    "nom": etu.nom,
                    "prenoms": etu.prenoms,
                    "classe": etu.classe
                }
                session["user_info"] = user_info

                flash("Connexion réussie ✅", "success")
                print('la boite: ', session["user_info"]["classe"])

                if session["user_info"]["classe"] != 'super@user':
                
                        return redirect(url_for('register', Etudiant= session["username"]))
                
                elif session["user_info"]["classe"] == 'super@user':

                    return redirect(url_for('admin'))  # Redirige vers une page tableau de bord
            else:
                flash("Mot de passe incorrect ❌", "danger")
        else:
            flash("Adresse email introuvable ❌", "danger")

    return render_template('login.html')


@app.route('/inscription', methods=['GET', 'POST'])
def inscription():

    if request.method == "POST":
        nom = request.form["nom"]
        prenom = request.form["prenom"]
        classe = request.form["classe"]
        email = request.form["email"]

        # Générer mot de passe aléatoire
        plain_password = generate_random_password(10)

        # Hacher le mot de passe
        hashed_password = generate_password_hash(plain_password)

        # Créer un nouvel étudiant
        new_student = Etudiant(
            email=email,
            nom=nom,
            prenoms=prenom,
            classe=classe,
            mpd=hashed_password
        )

        try:
            db.session.add(new_student)
            db.session.commit()
            print(f"✅ Étudiant ajouté : {nom} {prenom}, Mot de passe généré = {plain_password}")
            
            subject = 'Validation de compte !'

            body = f"""Bonjour {nom} {prenom}, \n Votre compte a été crée avec succès. Votre mot de passe est: {plain_password}  \n DataCraft AFRICA, le progrès n'attend pas
            """

            # Création du message
            msg = Message(subject, sender='appsrf42@gmail.com', recipients=[email])
            msg.body = body

            mail.send(msg)

            flash("Compte crée avec succès ! Vérifier votre boite mail pour le mot de passe.", "success")

            return redirect(url_for("login"))
        
        except Exception as e:
            db.session.rollback()
            print(f"❌ Erreur : {e}")
            flash("Erreur lors de l'inscription.", "danger")

       
    return render_template('inscription.html', classe=classes)


@app.route('/logout')

def logout():

    session.pop('loggin', None)
    session.pop('id', None)
    session.pop('username', None)


    return redirect(url_for('connexion'))

# --- Helper : fusion Postgres + Google Sheet en une liste de dicts ---
def fetch_combined_data(classe):
    """
    Retourne une liste de dicts :
    [
      {"email":..., "nom":..., "prenoms":..., "theme":..., ...},
      ...
    ]
    """
    # 1) récupérer étudiants depuis Postgres (Assure-toi que Etudiant.email existe)
    etudiants = Etudiant.query.filter_by(classe=classe).all()

    # 2) récupérer les lignes de la worksheet correspondant à la classe
    try:
        spreadsheet = get_gsheet_etudiant()
        try:
            worksheet = spreadsheet.worksheet(classe)
            g_rows = worksheet.get_all_records()  # liste de dicts
        except Exception:
            # feuille non trouvée ou vide -> on prend liste vide
            g_rows = []
    except Exception as e:
        # si la connexion gspread casse, on continue avec une liste vide (log)
        current_app.logger.exception("Erreur connexion Google Sheet")
        g_rows = []

    # Nettoyage / indexation par email : nettoie les clés (strip) pour éviter problème d'espaces
    gdict = {}
    for r in g_rows:
        # normaliser les clés : enlever espaces en début/fin
        norm = { (k.strip() if isinstance(k, str) else k) : v for k,v in r.items() }
        email_key = None
        # essayer plusieurs variantes pour la colonne Email
        for candidate in ("Email", "email", "E-mail", "E_MAIL"):
            if candidate in norm and norm.get(candidate):
                email_key = candidate
                break
        # si trouvé, indexer
        if email_key:
            gdict[norm[email_key]] = norm
        else:
            # tenter champ vide ou ignorer
            continue

    # 3) Construire la liste finale en fusionnant via email
    result = []
    for e in etudiants:
        email = getattr(e, "email", None)
        sheet_row = gdict.get(email, {}) if email else {}
        # essayer de récupérer plusieurs variantes de noms d'en-têtes (accents, espaces)
        def pick(*keys):
            for k in keys:
                if k in sheet_row and sheet_row[k] not in (None, ""):
                    return sheet_row[k]
            return ""

        result.append({
            "email": email or "",
            "nom": getattr(e, "nom", "") or "",
            "prenoms": getattr(e, "prenoms", "") or "",
            "theme": pick("Theme", "Thème", "theme"),
            "encadreur_pro": pick("Encadreur_Professionnel", "Encadreur", "encadreur"),
            "tel_encadreur": pick("Telephone", "Telephone", "Tel_encadreur", "tel_encadreur"),
            "structure": pick("Structure_Accueil", "Structure", "structure"),
            "questions": pick("Questions_recherche", "Questions", "questions"),
            "base_dispo": pick("BD", "Base_dispo", "base_dispo"),
            "encadreur_acad": pick("Encadreur_Academique", "Encadreur_acad", "encadreur_acad")
        })

    return result



if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
