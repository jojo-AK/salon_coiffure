from datetime import datetime, timedelta
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    mot_de_passe = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='client')
    created_at = db.Column(db.DateTime, default=datetime.now)

    rendezvous = db.relationship(
        'RendezVous', backref='client', lazy='dynamic')

    def set_password(self, password):
        self.mot_de_passe = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.mot_de_passe, password)

    def is_admin(self):
        return self.role == 'coiffeur'

    def __repr__(self):
        return f'<User {self.email} ({self.role})>'


class Service(db.Model):
    __tablename__ = 'services'

    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100), nullable=False)
    prix = db.Column(db.Float, nullable=False)
    duree_minutes = db.Column(db.Integer, nullable=False)
    description = db.Column(db.Text, nullable=True)
    actif = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.now)

    rendezvous = db.relationship(
        'RendezVous', backref='service', lazy='dynamic')

    def __repr__(self):
        return f'<Service {self.nom} - {self.duree_minutes}min>'


class RendezVous(db.Model):
    __tablename__ = 'rendezvous'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    service_id = db.Column(db.Integer, db.ForeignKey(
        'services.id'), nullable=False)
    debut_datetime = db.Column(db.DateTime, nullable=False)
    duree_minutes = db.Column(db.Integer, nullable=False)
    statut = db.Column(db.String(20), nullable=False, default='en_attente')
    created_at = db.Column(db.DateTime, default=datetime.now)
    note_client = db.Column(db.Text, nullable=True)

    @property
    def fin_datetime(self):
        return self.debut_datetime + timedelta(minutes=self.duree_minutes)

    def __repr__(self):
        return f'<RDV {self.id} | {self.debut_datetime} | {self.statut}>'


def verifier_conflit(debut_nouveau, duree_minutes):
    fin_nouveau = debut_nouveau + timedelta(minutes=duree_minutes)

    rdv_en_conflit = RendezVous.query.filter(
        RendezVous.statut == 'accepte',
        RendezVous.debut_datetime < fin_nouveau,
    ).all()

    for rdv in rdv_en_conflit:
        if rdv.fin_datetime > debut_nouveau:
            return True

    return False


def get_creneaux_disponibles(date, duree_minutes, heure_ouverture=8, heure_fermeture=20):
    creneaux = []
    current = datetime(date.year, date.month, date.day, heure_ouverture, 0)
    fermeture = datetime(date.year, date.month, date.day, heure_fermeture, 0)

    while current + timedelta(minutes=duree_minutes) <= fermeture:
        if not verifier_conflit(current, duree_minutes):
            creneaux.append(current)
        current += timedelta(minutes=30)

    return creneaux
