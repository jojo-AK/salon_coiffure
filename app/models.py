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
    telephone = db.Column(db.String(20), nullable=True)
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


class Service(db.Model):
    __tablename__ = 'services'
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100), nullable=False)
    prix = db.Column(db.Float, nullable=False)
    duree_minutes = db.Column(db.Integer, nullable=False)
    description = db.Column(db.Text, nullable=True)
    photo = db.Column(db.String(200), nullable=True)
    actif = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.now)
    rendezvous = db.relationship(
        'RendezVous', backref='service', lazy='dynamic')


class Supplement(db.Model):
    __tablename__ = 'supplements'
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100), nullable=False)
    prix = db.Column(db.Float, nullable=False)
    actif = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.now)


class RendezVous(db.Model):
    __tablename__ = 'rendezvous'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    service_id = db.Column(db.Integer, db.ForeignKey(
        'services.id'), nullable=False)
    debut_datetime = db.Column(db.DateTime, nullable=False)
    duree_minutes = db.Column(db.Integer, nullable=False)
    statut = db.Column(db.String(20), nullable=False, default='en_attente')
    prix_total = db.Column(db.Float, nullable=False, default=0)
    created_at = db.Column(db.DateTime, default=datetime.now)
    note_client = db.Column(db.Text, nullable=True)
    supplements = db.relationship(
        'RDVSupplement', backref='rendezvous', lazy='dynamic')

    @property
    def fin_datetime(self):
        return self.debut_datetime + timedelta(minutes=self.duree_minutes)

    @property
    def liste_supplements(self):
        return [rs for rs in self.supplements]


class RDVSupplement(db.Model):
    __tablename__ = 'rdv_supplements'
    id = db.Column(db.Integer, primary_key=True)
    rdv_id = db.Column(db.Integer, db.ForeignKey(
        'rendezvous.id'), nullable=False)
    supplement_id = db.Column(db.Integer, db.ForeignKey(
        'supplements.id'), nullable=False)
    prix_snapshot = db.Column(db.Float, nullable=False)
    nom_snapshot = db.Column(db.String(100), nullable=True)
    supplement = db.relationship('Supplement')

    @property
    def nom(self):
        """Pour les templates qui font map(attribute='nom')."""
        return self.nom_snapshot or (self.supplement.nom if self.supplement else '')


class ProfilSalon(db.Model):
    __tablename__ = 'profil_salon'
    id = db.Column(db.Integer, primary_key=True)
    nom_salon = db.Column(db.String(100), nullable=False, default='MonSalon')
    bio = db.Column(db.Text, nullable=True)
    whatsapp = db.Column(db.String(20), nullable=True)
    adresse = db.Column(db.String(200), nullable=True)
    horaires = db.Column(db.String(200), nullable=True)
    photo_profil = db.Column(db.String(200), nullable=True)
    updated_at = db.Column(
        db.DateTime, default=datetime.now, onupdate=datetime.now)
    photos_interieur = db.relationship(
        'PhotoSalon', backref='salon', lazy='dynamic')

    @staticmethod
    def get():
        profil = ProfilSalon.query.first()
        if not profil:
            profil = ProfilSalon()
            db.session.add(profil)
            db.session.commit()
        return profil


class PhotoSalon(db.Model):
    __tablename__ = 'photos_salon'
    id = db.Column(db.Integer, primary_key=True)
    salon_id = db.Column(db.Integer, db.ForeignKey(
        'profil_salon.id'), nullable=False)
    filename = db.Column(db.String(200), nullable=False)
    legende = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.now)


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
