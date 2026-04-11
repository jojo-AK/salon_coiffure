from app import create_app
from app.models import db, User, Service, Supplement
import os

app = create_app('development')

with app.app_context():
    confirm = input("ATTENTION : seed.py efface TOUTES les donnees. Taper 'oui' pour confirmer : ")
    if confirm.strip().lower() != 'oui':
        print("Annulé.")
        exit()
    db.drop_all()
    db.create_all()

    # Coiffeur
    coiffeur = User(nom='Joseph Coiffeur', email='coiffeur@salon.com', role='coiffeur')
    coiffeur.set_password('coiffeur123')
    db.session.add(coiffeur)

    # Services
    services = [
        Service(nom='Coupe simple', prix=2000, duree_minutes=30, description='Coupe classique homme'),
        Service(nom='Degrade', prix=3000, duree_minutes=45, description='Degrade bas ou haut'),
        Service(nom='Tresse', prix=8000, duree_minutes=180, description='Tresses africaines'),
        Service(nom='Soin + Coupe', prix=5000, duree_minutes=60, description='Soin capillaire et coupe'),
    ]
    for s in services:
        db.session.add(s)

    # Suppléments globaux
    supplements = [
        Supplement(nom='Sauce', prix=500),
        Supplement(nom='Fibre capillaire', prix=1000),
        Supplement(nom='Coloration', prix=2000),
        Supplement(nom='Traitement hydratant', prix=1500),
    ]
    for s in supplements:
        db.session.add(s)

    db.session.commit()
    print("Base initialisee !")
    print("  Admin : coiffeur@salon.com / coiffeur123")
    print("  4 services + 4 supplements crees")
    print("  Les clients n'ont plus besoin de compte !")
