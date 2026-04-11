from datetime import datetime, timedelta
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
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
def reserver():
    services = Service.query.filter_by(actif=True).order_by(Service.nom).all()
    supplements = Supplement.query.filter_by(
        actif=True).order_by(Supplement.nom).all()

    if request.method == 'POST':
        # Guest info
        nom_client = request.form.get('nom_client', '').strip()
        telephone = request.form.get('telephone', '').strip()
        email_client = request.form.get('email_client', '').strip() or None

        # Booking info
        service_id = request.form.get('service_id')
        date_str = request.form.get('date')
        heure_str = request.form.get('heure')
        supplement_ids = request.form.getlist('supplements')

        if not nom_client or not telephone:
            flash('Le nom et le telephone sont obligatoires.', 'danger')
            return render_template('client/reserver.html', services=services, supplements=supplements)

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

        # Check if this phone already has an active booking
        rdv_actif = RendezVous.query.filter(
            RendezVous.telephone == telephone,
            RendezVous.statut.in_(
                ['en_attente', 'accepte', 'annulation_demandee'])
        ).first()

        if rdv_actif:
            flash(
                'Ce numero a deja un rendez-vous en cours. Attendez sa confirmation ou annulez-le avant d\'en prendre un nouveau.', 'warning')
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
            nom_client=nom_client,
            telephone=telephone,
            email_client=email_client,
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
        flash('Demande envoyee ! Vous recevrez une confirmation par telephone.', 'success')
        return redirect(url_for('client.confirmation', rdv_id=rdv.id))

    return render_template('client/reserver.html', services=services, supplements=supplements)


@client_bp.route('/confirmation/<int:rdv_id>')
def confirmation(rdv_id):
    rdv = db.get_or_404(RendezVous, rdv_id)
    return render_template('client/confirmation.html', rdv=rdv)


@client_bp.route('/creneaux-disponibles')
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


@client_bp.route('/suivi', methods=['GET', 'POST'])
def suivi():
    """Lookup bookings by phone number."""
    rdvs = []
    telephone = ''
    if request.method == 'POST':
        telephone = request.form.get('telephone', '').strip()
        if telephone:
            rdvs = RendezVous.query.filter_by(telephone=telephone).order_by(
                RendezVous.debut_datetime.desc()).all()
    return render_template('client/suivi.html', rendezvous=rdvs, telephone=telephone, now=datetime.now())


@client_bp.route('/rdv/<int:rdv_id>/annuler', methods=['POST'])
def annuler_rdv(rdv_id):
    rdv = db.get_or_404(RendezVous, rdv_id)
    telephone = request.form.get('telephone', '').strip()

    if rdv.telephone != telephone:
        flash('Numero de telephone incorrect.', 'danger')
        return redirect(url_for('client.suivi'))

    if rdv.statut in ['annule', 'annulation_demandee']:
        flash('Une demande d\'annulation est deja en cours.', 'warning')
        return redirect(url_for('client.suivi'))

    if rdv.statut == 'refuse':
        flash('Ce RDV est deja refuse.', 'warning')
        return redirect(url_for('client.suivi'))

    if rdv.debut_datetime < datetime.now():
        flash('Impossible d\'annuler un rendez-vous dont la date est passee.', 'danger')
        return redirect(url_for('client.suivi'))

    rdv.statut = 'annulation_demandee'
    db.session.commit()
    flash('Demande d\'annulation envoyee. En attente de confirmation du coiffeur.', 'info')
    return redirect(url_for('client.suivi'))
