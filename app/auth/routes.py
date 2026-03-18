from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app.models import db, User

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('client.vitrine'))
    if request.method == 'POST':
        nom = request.form.get('nom', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm = request.form.get('confirm_password', '')
        if not nom or not email or not password:
            flash('Tous les champs sont obligatoires.', 'danger')
            return render_template('auth/register.html')
        if password != confirm:
            flash('Les mots de passe ne correspondent pas.', 'danger')
            return render_template('auth/register.html')
        if User.query.filter_by(email=email).first():
            flash('Cet email est deja utilise.', 'danger')
            return render_template('auth/register.html')
        user = User(nom=nom, email=email, role='client')
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        flash('Compte cree ! Connectez-vous.', 'success')
        return redirect(url_for('auth.login'))
    return render_template('auth/register.html')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('client.vitrine'))
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        remember = bool(request.form.get('remember'))
        user = User.query.filter_by(email=email).first()
        if not user or not user.check_password(password):
            flash('Email ou mot de passe incorrect.', 'danger')
            return render_template('auth/login.html')
        login_user(user, remember=remember)
        flash(f'Bienvenue, {user.nom} !', 'success')
        next_page = request.args.get('next')
        if next_page:
            return redirect(next_page)
        if user.is_admin():
            return redirect(url_for('admin.dashboard'))
        return redirect(url_for('client.mes_rendezvous'))
    return render_template('auth/login.html')


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Vous etes deconnecte.', 'info')
    return redirect(url_for('auth.login'))
