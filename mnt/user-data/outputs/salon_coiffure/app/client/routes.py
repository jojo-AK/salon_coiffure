from datetime import datetime, date
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app.models import db, Service, RendezVous, verifier_conflit, get_creneaux_disponibles

client_bp = Blueprint('client', __name__)


@client_bp.route('/')
def vitrine():
    """Page d'accueil publique du salon."""
    services = Service.query.filter_by(actif=True).order_by(Service.nom).all()
    return render_template('client/vitrine.html', services=services)


@client_bp.route('/reserver', methods=['GET', 'POST'])
@login_required
def reserver():
    """Formulaire de réservation pour le client."""
    services = Service.query.filter_by(actif=True).order_by(Service.nom).all()

    if request.method == 'POST':
        service_id = request.form.get('service_id')
        date_str = request.form.get('date')
        heure_str = request.form.get('heure')

        # Validations
        if not service_id or not date_str or not heure_str:
            flash('Tous les champs sont obligatoires.', 'danger')
            return render_template('client/reserver.html', services=services)

        service = Service.query.get_or_404(int(service_id))

        try:
            debut = datetime.strptime(f"{date_str} {heure_str}", "%Y-%m-%d %H:%M")
        except ValueError:
            flash('Format de date ou heure invalide.', 'danger')
            return render_template('client/reserver.html', services=services)

        if debut < datetime.now():
            flash('Impossible de réserver dans le passé.', 'danger')
            return render_template('client/reserver.html', services=services)

        # ── VÉRIFICATION ANTI-CONFLIT ──────────────────────────
        if verifier_conflit(debut, service.duree_minutes):
            flash('Ce créneau est déjà pris. Choisissez un autre horaire.', 'warning')
            return render_template('client/reserver.html', services=services)

        # Création du rendez-vous
        rdv = RendezVous(
            user_id=current_user.id,
            service_id=service.id,
            debut_datetime=debut,
            duree_minutes=service.duree_minutes,  # Copie de la durée
            statut='en_attente',
            note_client=request.form.get('note', '').strip()
        )
        db.session.add(rdv)
        db.session.commit()

        flash('Demande envoyée ! En attente de confirmation du coiffeur.', 'success')
        return redirect(url_for('client.mes_rendezvous'))

    return render_template('client/reserver.html', services=services)


@client_bp.route('/creneaux-disponibles')
@login_required
def creneaux_disponibles():
    """
    API JSON : retourne les créneaux libres pour une date et un service donné.
    Appelée en AJAX depuis le formulaire de réservation.
    """
    service_id = request.args.get('service_id')
    date_str = request.args.get('date')

    if not service_id or not date_str:
        return jsonify({'error': 'Paramètres manquants'}), 400

    service = Service.query.get_or_404(int(service_id))

    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return jsonify({'error': 'Format de date invalide'}), 400

    creneaux = get_creneaux_disponibles(date_obj, service.duree_minutes)
    return jsonify({
        'creneaux': [c.strftime('%H:%M') for c in creneaux],
        'service': service.nom,
        'duree': service.duree_minutes
    })


@client_bp.route('/mes-rendezvous')
@login_required
def mes_rendezvous():
    """Historique des rendez-vous du client connecté."""
    rdvs = RendezVous.query.filter_by(user_id=current_user.id)\
        .order_by(RendezVous.debut_datetime.desc()).all()
    return render_template('client/mes_rendezvous.html', rendezvous=rdvs)
