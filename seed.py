"""
Script de test Phase 1 :
    python seed.py
Crée un compte coiffeur + un compte client + quelques services.
"""
from app import create_app
from app.models import db, User, Service

app = create_app('development')

with app.app_context():
    db.drop_all()
    db.create_all()

    # Compte coiffeur (admin)
    coiffeur = User(nom='Joseph Coiffeur', email='coiffeur@salon.com', role='coiffeur')
    coiffeur.set_password('coiffeur123')
    db.session.add(coiffeur)

    # Compte client test
    client = User(nom='Client Test', email='client@test.com', role='client')
    client.set_password('client123')
    db.session.add(client)

    # Services
    services = [
        Service(nom='Coupe simple', prix=2000, duree_minutes=30,
                description='Coupe classique homme'),
        Service(nom='Dégradé', prix=3000, duree_minutes=45,
                description='Dégradé bas ou haut'),
        Service(nom='Tresse', prix=8000, duree_minutes=180,
                description='Tresses africaines'),
        Service(nom='Soin + Coupe', prix=5000, duree_minutes=60,
                description='Soin capillaire et coupe'),
    ]
    for s in services:
        db.session.add(s)

    db.session.commit()
    print("Base initialisée avec succès !")
    print("  Coiffeur : coiffeur@salon.com / coiffeur123")
    print("  Client   : client@test.com / client123")
    print("  Services : 4 services créés")
