from datetime import datetime, timedelta
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app.models import db, Service, Supplement, RendezVous, RDVSupplement, verifier_conflit, get_creneaux_disponibles
from app.notifications import notifier_coiffeur_nouvelle_demande

client_bp = Blueprint('client', __name__)


@client_bp.route('/')
def vitrine():
    from app.models import ProfilSalon
    services = Service.query.filter_by(actif=True).order_by(Service.nom).all()
    profil_salon = ProfilSalon.get()
    return render_template('client/vitrine.html', services=services, profil_salon=profil_salon)


@client_bp.route('/salon')
def profil_salon():
    from app.models import ProfilSalon, PhotoSalon
    profil = ProfilSalon.get()
    photos = PhotoSalon.query.filter_by(salon_id=profil.id).all()
    services = Service.query.filter_by(actif=True).order_by(Service.nom).all()
    return render_template('client/profil_salon.html', profil=profil, photos=photos, services=services)


@client_bp.route('/reserver', methods=['GET', 'POST'])
@login_required
def reserver():
    services = Service.query.filter_by(actif=True).order_by(Service.nom).all()
    supplements = Supplement.query.filter_by(
        actif=True).order_by(Supplement.nom).all()

    if request.method == 'POST':
        service_id = request.form.get('service_id')
        date_str = request.form.get('date')
        heure_str = request.form.get('heure')
        supplement_ids = request.form.getlist('supplements')

        if not service_id or not date_str or not heure_str:
            flash('Tous les champs sont obligatoires.', 'danger')
            return render_template('client/reserver.html', services=services, supplements=supplements)

        service = db.get_or_404(Service, int(service_id))

        try:
            debut = datetime.strptime(
                f"{date_str} {heure_str}", "%Y-%m-%d %H:%M")
        except ValueError:
            flash('Format invalide.', 'danger')
            return render_template('client/reserver.html', services=services, supplements=supplements)

        if debut < datetime.now():
            flash('Impossible de reserver dans le passe.', 'danger')
            return render_template('client/reserver.html', services=services, supplements=supplements)

        if debut > datetime.now() + timedelta(days=30):
            flash('Impossible de reserver a plus de 30 jours.', 'danger')
            return render_template('client/reserver.html', services=services, supplements=supplements)

        rdv_actif = RendezVous.query.filter(
            RendezVous.user_id == current_user.id,
            RendezVous.statut.in_(
                ['en_attente', 'accepte', 'annulation_demandee'])
        ).first()

        if rdv_actif:
            flash(
                'Vous avez deja un rendez-vous en cours. Annulez-le avant d\'en prendre un nouveau.', 'warning')
            return render_template('client/reserver.html', services=services, supplements=supplements)

        if verifier_conflit(debut, service.duree_minutes):
            flash('Ce creneau est deja pris.', 'warning')
            return render_template('client/reserver.html', services=services, supplements=supplements)

        prix_total = service.prix
        supps_selectionnes = []
        for sid in supplement_ids:
            supp = Supplement.query.get(int(sid))
            if supp and supp.actif:
                prix_total += supp.prix
                supps_selectionnes.append(supp)

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
        db.session.flush()

        for supp in supps_selectionnes:
            rdv_supp = RDVSupplement(
                rdv_id=rdv.id,
                supplement_id=supp.id,
                prix_snapshot=supp.prix,
                nom_snapshot=supp.nom
            )
            db.session.add(rdv_supp)

        db.session.commit()
        notifier_coiffeur_nouvelle_demande(rdv)
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
    service = db.get_or_404(Service, int(service_id))
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
    # Clôture automatique des RDV expirés
    from app.utils import cloturer_rdv_expires
    cloturer_rdv_expires()

    rdvs = RendezVous.query.filter_by(user_id=current_user.id).order_by(
        RendezVous.debut_datetime.desc()).all()
    return render_template('client/mes_rendezvous.html', rendezvous=rdvs, now=datetime.now())


@client_bp.route('/rdv/<int:rdv_id>/annuler', methods=['POST'])
@login_required
def annuler_rdv(rdv_id):
    rdv = db.get_or_404(RendezVous, rdv_id)

    if rdv.user_id != current_user.id:
        flash('Action non autorisee.', 'danger')
        return redirect(url_for('client.mes_rendezvous'))

    if rdv.statut in ['annule', 'annulation_demandee']:
        flash('Une demande d\'annulation est deja en cours.', 'warning')
        return redirect(url_for('client.mes_rendezvous'))

    if rdv.statut == 'refuse':
        flash('Ce RDV est deja refuse.', 'warning')
        return redirect(url_for('client.mes_rendezvous'))

    if rdv.debut_datetime < datetime.now():
        flash('Impossible d\'annuler un rendez-vous dont la date est passee.', 'danger')
        return redirect(url_for('client.mes_rendezvous'))

    rdv.statut = 'annulation_demandee'
    db.session.commit()
    flash('Demande d\'annulation envoyee. En attente de confirmation du coiffeur.', 'info')
    return redirect(url_for('client.mes_rendezvous'))
