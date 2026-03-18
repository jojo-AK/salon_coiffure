from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from functools import wraps
from app.models import db, Service, RendezVous

admin_bp = Blueprint('admin', __name__)


# Décorateur : réserve les routes au coiffeur uniquement
def coiffeur_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin():
            flash('Accès réservé au coiffeur.', 'danger')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated


@admin_bp.route('/dashboard')
@login_required
@coiffeur_required
def dashboard():
    rdv_attente = RendezVous.query.filter_by(statut='en_attente').order_by(
        RendezVous.debut_datetime).all()
    rdv_acceptes = RendezVous.query.filter_by(statut='accepte').order_by(
        RendezVous.debut_datetime).all()
    return render_template('admin/dashboard.html',
                           rdv_attente=rdv_attente,
                           rdv_acceptes=rdv_acceptes)


# ── Gestion des services ─────────────────────────────────────

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
            flash('Nom, prix et durée sont obligatoires.', 'danger')
            return render_template('admin/service_form.html', service=None)

        service = Service(
            nom=nom,
            prix=float(prix),
            duree_minutes=int(duree),
            description=description
        )
        db.session.add(service)
        db.session.commit()
        flash(f'Service "{nom}" ajouté ({duree} min).', 'success')
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
        db.session.commit()
        flash('Service mis à jour.', 'success')
        return redirect(url_for('admin.services'))

    return render_template('admin/service_form.html', service=service)


@admin_bp.route('/services/supprimer/<int:service_id>', methods=['POST'])
@login_required
@coiffeur_required
def supprimer_service(service_id):
    service = Service.query.get_or_404(service_id)
    service.actif = False  # Soft delete
    db.session.commit()
    flash('Service désactivé.', 'info')
    return redirect(url_for('admin.services'))


# ── Validation / refus des rendez-vous ──────────────────────

@admin_bp.route('/rdv/<int:rdv_id>/accepter', methods=['POST'])
@login_required
@coiffeur_required
def accepter_rdv(rdv_id):
    rdv = RendezVous.query.get_or_404(rdv_id)
    rdv.statut = 'accepte'
    db.session.commit()
    flash('Rendez-vous accepté.', 'success')
    return redirect(url_for('admin.dashboard'))


@admin_bp.route('/rdv/<int:rdv_id>/refuser', methods=['POST'])
@login_required
@coiffeur_required
def refuser_rdv(rdv_id):
    rdv = RendezVous.query.get_or_404(rdv_id)
    rdv.statut = 'refuse'
    db.session.commit()
    flash('Rendez-vous refusé.', 'info')
    return redirect(url_for('admin.dashboard'))
