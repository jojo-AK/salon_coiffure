"""
Tests unitaires — algorithme anti-conflit de créneaux
Lancer avec : python -m pytest tests/ -v
"""
import pytest
from datetime import datetime, timedelta
from app import create_app
from app.models import db, User, Service, RendezVous, verifier_conflit, get_creneaux_disponibles


@pytest.fixture
def app():
    app = create_app('development')
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['TESTING'] = True
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture
def ctx(app):
    with app.app_context():
        yield


# ── Helpers ──────────────────────────────────────────────────

def creer_rdv_accepte(user_id, service_id, debut, duree):
    rdv = RendezVous(
        user_id=user_id,
        service_id=service_id,
        debut_datetime=debut,
        duree_minutes=duree,
        statut='accepte'
    )
    db.session.add(rdv)
    db.session.commit()
    return rdv


def creer_fixtures(ctx):
    """Crée un user et un service de base pour les tests."""
    user = User(nom='Test', email='test@test.com', role='client')
    user.set_password('test123')
    db.session.add(user)

    service = Service(nom='Coupe', prix=2000, duree_minutes=30)
    db.session.add(service)
    db.session.commit()
    return user, service


# ── Tests verifier_conflit ────────────────────────────────────

def test_pas_de_conflit_creneau_libre(app):
    """Aucun RDV en base → pas de conflit."""
    with app.app_context():
        debut = datetime(2025, 7, 14, 10, 0)
        assert verifier_conflit(debut, 30) == False


def test_conflit_chevauchement_direct(app):
    """RDV A 14h-17h (180min) → B à 15h doit être bloqué."""
    with app.app_context():
        user, service = creer_fixtures(app.app_context())
        creer_rdv_accepte(user.id, service.id, datetime(2025, 7, 14, 14, 0), 180)

        assert verifier_conflit(datetime(2025, 7, 14, 15, 0), 30) == True


def test_conflit_debut_identique(app):
    """Même heure de début → conflit."""
    with app.app_context():
        user, service = creer_fixtures(app.app_context())
        creer_rdv_accepte(user.id, service.id, datetime(2025, 7, 14, 10, 0), 60)

        assert verifier_conflit(datetime(2025, 7, 14, 10, 0), 30) == True


def test_conflit_fin_qui_deborde(app):
    """RDV B commence avant la fin de A → conflit."""
    with app.app_context():
        user, service = creer_fixtures(app.app_context())
        # A : 10h00 → 10h30
        creer_rdv_accepte(user.id, service.id, datetime(2025, 7, 14, 10, 0), 30)
        # B : 10h15 → 10h45 → chevauche A
        assert verifier_conflit(datetime(2025, 7, 14, 10, 15), 30) == True


def test_pas_de_conflit_juste_apres(app):
    """RDV B commence exactement à la fin de A → pas de conflit."""
    with app.app_context():
        user, service = creer_fixtures(app.app_context())
        # A : 10h00 → 10h30
        creer_rdv_accepte(user.id, service.id, datetime(2025, 7, 14, 10, 0), 30)
        # B : 10h30 → 11h00 → juste après, OK
        assert verifier_conflit(datetime(2025, 7, 14, 10, 30), 30) == False


def test_pas_de_conflit_avant(app):
    """RDV B se termine avant le début de A → pas de conflit."""
    with app.app_context():
        user, service = creer_fixtures(app.app_context())
        # A : 11h00 → 11h30
        creer_rdv_accepte(user.id, service.id, datetime(2025, 7, 14, 11, 0), 30)
        # B : 10h00 → 10h30 → avant A, OK
        assert verifier_conflit(datetime(2025, 7, 14, 10, 0), 30) == False


def test_rdv_refuse_ne_bloque_pas(app):
    """Un RDV refusé ne doit PAS bloquer le créneau."""
    with app.app_context():
        user, service = creer_fixtures(app.app_context())
        rdv = RendezVous(
            user_id=user.id,
            service_id=service.id,
            debut_datetime=datetime(2025, 7, 14, 10, 0),
            duree_minutes=30,
            statut='refuse'
        )
        db.session.add(rdv)
        db.session.commit()

        assert verifier_conflit(datetime(2025, 7, 14, 10, 0), 30) == False


def test_rdv_en_attente_ne_bloque_pas(app):
    """Un RDV en attente ne doit PAS bloquer (seul 'accepte' bloque)."""
    with app.app_context():
        user, service = creer_fixtures(app.app_context())
        rdv = RendezVous(
            user_id=user.id,
            service_id=service.id,
            debut_datetime=datetime(2025, 7, 14, 10, 0),
            duree_minutes=30,
            statut='en_attente'
        )
        db.session.add(rdv)
        db.session.commit()

        assert verifier_conflit(datetime(2025, 7, 14, 10, 0), 30) == False


def test_tresse_3h_bloque_creneaux_intermediaires(app):
    """Cas concret du cahier des charges : tresse 14h-17h bloque 14h30, 15h, 16h."""
    with app.app_context():
        user, service = creer_fixtures(app.app_context())
        creer_rdv_accepte(user.id, service.id, datetime(2025, 7, 14, 14, 0), 180)

        assert verifier_conflit(datetime(2025, 7, 14, 14, 30), 30) == True
        assert verifier_conflit(datetime(2025, 7, 14, 15, 0),  30) == True
        assert verifier_conflit(datetime(2025, 7, 14, 16, 0),  30) == True
        assert verifier_conflit(datetime(2025, 7, 14, 17, 0),  30) == False  # juste après


# ── Tests get_creneaux_disponibles ───────────────────────────

def test_creneaux_vides_si_journee_pleine(app):
    """Journée bloquée par un RDV de 12h → aucun créneau."""
    with app.app_context():
        user, service = creer_fixtures(app.app_context())
        # RDV de 8h à 20h (720 min)
        creer_rdv_accepte(user.id, service.id, datetime(2025, 7, 14, 8, 0), 720)

        from datetime import date
        creneaux = get_creneaux_disponibles(date(2025, 7, 14), 30)
        assert len(creneaux) == 0


def test_creneaux_disponibles_journee_libre(app):
    """Journée sans RDV → créneaux toutes les 30min de 8h à 20h."""
    with app.app_context():
        from datetime import date
        creneaux = get_creneaux_disponibles(date(2025, 7, 14), 30)
        # 8h à 19h30 = 24 créneaux de 30min
        assert len(creneaux) == 24
        assert creneaux[0].hour == 8
        assert creneaux[0].minute == 0
