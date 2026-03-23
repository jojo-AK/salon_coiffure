from datetime import datetime
from app.models import db, RendezVous


def cloturer_rdv_expires():
    """
    Passe automatiquement les RDV acceptés dont l'heure de fin
    est dépassée au statut 'termine'.
    Appelée à chaque chargement du dashboard et de mes_rendezvous.
    """
    rdvs_acceptes = RendezVous.query.filter_by(statut='accepte').all()
    modifies = 0
    for rdv in rdvs_acceptes:
        if rdv.fin_datetime < datetime.now():
            rdv.statut = 'termine'
            modifies += 1
    if modifies > 0:
        db.session.commit()
