from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app.models import db, Service, RendezVous, verifier_conflit, get_creneaux_disponibles

client_bp = Blueprint('client', __name__)


@client_bp.route('/')
def vitrine():
    services = Service.query.filter_by(actif=True).order_by(Service.nom).all()
    return render_template('client/vitrine.html', services=services)


@client_bp.route('/reserver', methods=['GET', 'POST'])
@login_required
def reserver():
    services = Service.query.filter_by(actif=True).order_by(Service.nom).all()
    if request.method == 'POST':
        service_id = request.form.get('service_id')
        date_str = request.form.get('date')
        heure_str = request.form.get('heure')
        if not service_id or not date_str or not heure_str:
            flash('Tous les champs sont obligatoires.', 'danger')
            return render_template('client/reserver.html', services=services)
        service = Service.query.get_or_404(int(service_id))
        try:
            debut = datetime.strptime(
                f"{date_str} {heure_str}", "%Y-%m-%d %H:%M")
        except ValueError:
            flash('Format invalide.', 'danger')
            return render_template('client/reserver.html', services=services)
        if debut < datetime.now():
            flash('Impossible de reserver dans le passe.', 'danger')
            return render_template('client/reserver.html', services=services)
        if verifier_conflit(debut, service.duree_minutes):
            flash('Ce creneau est deja pris.', 'warning')
            return render_template('client/reserver.html', services=services)
        rdv = RendezVous(
            user_id=current_user.id,
            service_id=service.id,
            debut_datetime=debut,
            duree_minutes=service.duree_minutes,
            statut='en_attente',
            note_client=request.form.get('note', '').strip()
        )
        db.session.add(rdv)
        db.session.commit()
        flash('Demande envoyee !', 'success')
        return redirect(url_for('client.mes_rendezvous'))
    return render_template('client/reserver.html', services=services)


@client_bp.route('/creneaux-disponibles')
@login_required
def creneaux_disponibles():
    service_id = request.args.get('service_id')
    date_str = request.args.get('date')
    if not service_id or not date_str:
        return jsonify({'error': 'Parametres manquants'}), 400
    service = Service.query.get_or_404(int(service_id))
    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return jsonify({'error': 'Format invalide'}), 400
    creneaux = get_creneaux_disponibles(date_obj, service.duree_minutes)
    return jsonify({
        'creneaux': [c.strftime('%H:%M') for c in creneaux],
        'service': service.nom,
        'duree': service.duree_minutes
    })


@client_bp.route('/mes-rendezvous')
@login_required
def mes_rendezvous():
    rdvs = RendezVous.query.filter_by(user_id=current_user.id).order_by(
        RendezVous.debut_datetime.desc()).all()
    return render_template('client/mes_rendezvous.html', rendezvous=rdvs)
