from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app.models import db, Service, Supplement, RendezVous, RDVSupplement, verifier_conflit, get_creneaux_disponibles

client_bp = Blueprint('client', __name__)


@client_bp.route('/')
def vitrine():
    services = Service.query.filter_by(actif=True).order_by(Service.nom).all()
    return render_template('client/vitrine.html', services=services)


@client_bp.route('/reserver', methods=['GET', 'POST'])
@login_required
def reserver():
    services = Service.query.filter_by(actif=True).order_by(Service.nom).all()
    supplements = Supplement.query.filter_by(actif=True).order_by(Supplement.nom).all()

    if request.method == 'POST':
        service_id = request.form.get('service_id')
        date_str = request.form.get('date')
        heure_str = request.form.get('heure')
        supplement_ids = request.form.getlist('supplements')

        if not service_id or not date_str or not heure_str:
            flash('Tous les champs sont obligatoires.', 'danger')
            return render_template('client/reserver.html', services=services, supplements=supplements)

        service = Service.query.get_or_404(int(service_id))

        try:
            debut = datetime.strptime(f"{date_str} {heure_str}", "%Y-%m-%d %H:%M")
        except ValueError:
            flash('Format invalide.', 'danger')
            return render_template('client/reserver.html', services=services, supplements=supplements)

        if debut < datetime.now():
            flash('Impossible de reserver dans le passe.', 'danger')
            return render_template('client/reserver.html', services=services, supplements=supplements)

        if verifier_conflit(debut, service.duree_minutes):
            flash('Ce creneau est deja pris.', 'warning')
            return render_template('client/reserver.html', services=services, supplements=supplements)

        # Calcul prix total
        prix_total = service.prix
        supps_selectionnes = []
        for sid in supplement_ids:
            supp = Supplement.query.get(int(sid))
            if supp and supp.actif:
                prix_total += supp.prix
                supps_selectionnes.append(supp)

        # Création du RDV
        rdv = RendezVous(
            user_id=current_user.id,
            service_id=service.id,
            debut_datetime=debut,
            duree_minutes=service.duree_minutes,
            statut='en_attente',
            prix_total=prix_total,
            note_client=request.form.get('note', '').strip()
        )
        db.session.add(rdv)
        db.session.flush()  # pour avoir rdv.id

        # Liaison suppléments
        for supp in supps_selectionnes:
            rdv_supp = RDVSupplement(
                rdv_id=rdv.id,
                supplement_id=supp.id,
                prix_snapshot=supp.prix
            )
            db.session.add(rdv_supp)

        db.session.commit()
        flash('Demande envoyee ! En attente de confirmation.', 'success')
        return redirect(url_for('client.mes_rendezvous'))

    return render_template('client/reserver.html', services=services, supplements=supplements)


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
    rdvs = RendezVous.query.filter_by(user_id=current_user.id).order_by(RendezVous.debut_datetime.desc()).all()
    return render_template('client/mes_rendezvous.html', rendezvous=rdvs)


@client_bp.route('/salon')
def profil_salon():
    from app.models import ProfilSalon, PhotoSalon
    profil = ProfilSalon.get()
    photos = PhotoSalon.query.filter_by(salon_id=profil.id).all()
    services = Service.query.filter_by(actif=True).order_by(Service.nom).all()
    return render_template("client/profil_salon.html", profil=profil, photos=photos, services=services)
