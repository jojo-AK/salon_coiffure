import os
from datetime import datetime, date, timedelta
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from functools import wraps
from werkzeug.utils import secure_filename
from app.models import db, Service, Supplement, RendezVous
from app.notifications import notifier_client_confirmation, notifier_client_refus

admin_bp = Blueprint('admin', __name__)
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def coiffeur_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin():
            flash('Acces reserve au coiffeur.', 'danger')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated


@admin_bp.route('/dashboard')
@login_required
@coiffeur_required
def dashboard():
    # Date sélectionnée (aujourd'hui par défaut)
    date_str = request.args.get('date')
    try:
        date_selectionnee = datetime.strptime(date_str, '%Y-%m-%d').date() if date_str else date.today()
    except ValueError:
        date_selectionnee = date.today()

    # RDV du jour sélectionné, triés par heure
    debut_jour = datetime(date_selectionnee.year, date_selectionnee.month, date_selectionnee.day, 0, 0)
    fin_jour = datetime(date_selectionnee.year, date_selectionnee.month, date_selectionnee.day, 23, 59)

    rdv_du_jour = RendezVous.query.filter(
        RendezVous.debut_datetime >= debut_jour,
        RendezVous.debut_datetime <= fin_jour
    ).order_by(RendezVous.debut_datetime).all()

    # Toutes les demandes en attente (tous jours)
    rdv_attente = RendezVous.query.filter_by(statut='en_attente').order_by(RendezVous.debut_datetime).all()

    # RDV acceptés aujourd'hui
    rdv_acceptes = RendezVous.query.filter(
        RendezVous.statut == 'accepte',
        RendezVous.debut_datetime >= debut_jour,
        RendezVous.debut_datetime <= fin_jour
    ).all()

    return render_template('admin/dashboard.html',
        rdv_du_jour=rdv_du_jour,
        rdv_attente=rdv_attente,
        rdv_acceptes=rdv_acceptes,
        aujourd_hui=date_selectionnee.strftime('%d/%m/%Y'),
        date_precedente=(date_selectionnee - timedelta(days=1)).strftime('%Y-%m-%d'),
        date_suivante=(date_selectionnee + timedelta(days=1)).strftime('%Y-%m-%d'),
    )


# ── Services ─────────────────────────────────────────

@admin_bp.route('/services')
@login_required
@coiffeur_required
def services():
    tous_services = Service.query.order_by(Service.nom).all()
    return render_template('admin/services.html', services=tous_services)


@admin_bp.route('/services/ajouter', methods=['GET', 'POST'])
@login_required
@coiffeur_required
def ajouter_service():
    if request.method == 'POST':
        nom = request.form.get('nom', '').strip()
        prix = request.form.get('prix')
        duree = request.form.get('duree_minutes')
        description = request.form.get('description', '').strip()
        if not nom or not prix or not duree:
            flash('Nom, prix et duree sont obligatoires.', 'danger')
            return render_template('admin/service_form.html', service=None)
        service = Service(nom=nom, prix=float(prix), duree_minutes=int(duree), description=description)
        photo = request.files.get('photo')
        if photo and allowed_file(photo.filename):
            filename = secure_filename(f"service_{nom.lower().replace(' ', '_')}_{photo.filename}")
            upload_dir = os.path.join(current_app.root_path, 'static', 'uploads')
            os.makedirs(upload_dir, exist_ok=True)
            photo.save(os.path.join(upload_dir, filename))
            service.photo = filename
        db.session.add(service)
        db.session.commit()
        flash(f'Service "{nom}" ajoute.', 'success')
        return redirect(url_for('admin.services'))
    return render_template('admin/service_form.html', service=None)


@admin_bp.route('/services/modifier/<int:service_id>', methods=['GET', 'POST'])
@login_required
@coiffeur_required
def modifier_service(service_id):
    service = Service.query.get_or_404(service_id)
    if request.method == 'POST':
        service.nom = request.form.get('nom', '').strip()
        service.prix = float(request.form.get('prix', 0))
        service.duree_minutes = int(request.form.get('duree_minutes', 30))
        service.description = request.form.get('description', '').strip()
        photo = request.files.get('photo')
        if photo and allowed_file(photo.filename):
            filename = secure_filename(f"service_{service.nom.lower().replace(' ', '_')}_{photo.filename}")
            upload_dir = os.path.join(current_app.root_path, 'static', 'uploads')
            os.makedirs(upload_dir, exist_ok=True)
            photo.save(os.path.join(upload_dir, filename))
            service.photo = filename
        db.session.commit()
        flash('Service mis a jour.', 'success')
        return redirect(url_for('admin.services'))
    return render_template('admin/service_form.html', service=service)


@admin_bp.route('/services/supprimer/<int:service_id>', methods=['POST'])
@login_required
@coiffeur_required
def supprimer_service(service_id):
    service = Service.query.get_or_404(service_id)
    service.actif = False
    db.session.commit()
    flash('Service desactive.', 'info')
    return redirect(url_for('admin.services'))


# ── Suppléments ──────────────────────────────────────

@admin_bp.route('/supplements')
@login_required
@coiffeur_required
def supplements():
    tous = Supplement.query.order_by(Supplement.nom).all()
    return render_template('admin/supplements.html', supplements=tous)


@admin_bp.route('/supplements/ajouter', methods=['GET', 'POST'])
@login_required
@coiffeur_required
def ajouter_supplement():
    if request.method == 'POST':
        nom = request.form.get('nom', '').strip()
        prix = request.form.get('prix')
        if not nom or not prix:
            flash('Nom et prix sont obligatoires.', 'danger')
            return render_template('admin/supplement_form.html', supplement=None)
        supp = Supplement(nom=nom, prix=float(prix))
        db.session.add(supp)
        db.session.commit()
        flash(f'Supplement "{nom}" ajoute.', 'success')
        return redirect(url_for('admin.supplements'))
    return render_template('admin/supplement_form.html', supplement=None)


@admin_bp.route('/supplements/modifier/<int:supp_id>', methods=['GET', 'POST'])
@login_required
@coiffeur_required
def modifier_supplement(supp_id):
    supp = Supplement.query.get_or_404(supp_id)
    if request.method == 'POST':
        supp.nom = request.form.get('nom', '').strip()
        supp.prix = float(request.form.get('prix', 0))
        db.session.commit()
        flash('Supplement mis a jour.', 'success')
        return redirect(url_for('admin.supplements'))
    return render_template('admin/supplement_form.html', supplement=supp)


@admin_bp.route('/supplements/supprimer/<int:supp_id>', methods=['POST'])
@login_required
@coiffeur_required
def supprimer_supplement(supp_id):
    supp = Supplement.query.get_or_404(supp_id)
    supp.actif = False
    db.session.commit()
    flash('Supplement desactive.', 'info')
    return redirect(url_for('admin.supplements'))


# ── RDV ──────────────────────────────────────────────

@admin_bp.route('/rdv/<int:rdv_id>/accepter', methods=['POST'])
@login_required
@coiffeur_required
def accepter_rdv(rdv_id):
    rdv = RendezVous.query.get_or_404(rdv_id)
    rdv.statut = 'accepte'
    db.session.commit()
    notifier_client_confirmation(rdv)
    flash(f'Rendez-vous de {rdv.client.nom} accepte.', 'success')
    return redirect(url_for('admin.dashboard'))


@admin_bp.route('/rdv/<int:rdv_id>/refuser', methods=['POST'])
@login_required
@coiffeur_required
def refuser_rdv(rdv_id):
    rdv = RendezVous.query.get_or_404(rdv_id)
    rdv.statut = 'refuse'
    db.session.commit()
    notifier_client_refus(rdv)
    flash(f'Rendez-vous de {rdv.client.nom} refuse.', 'info')
    return redirect(url_for('admin.dashboard'))
