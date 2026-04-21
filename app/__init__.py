import os
import click
from flask import Flask, render_template
from flask_login import LoginManager
from flask_mail import Mail
from app.models import db, User
from config import config

login_manager = LoginManager()
mail = Mail()


def create_app(config_name='default'):
    app = Flask(__name__)
    app.config.from_object(config[config_name])

    # Derrière le proxy HTTPS de Render, Flask doit faire confiance aux
    # en-têtes X-Forwarded-* pour générer les bonnes URLs (https://).
    if not app.config.get('DEBUG'):
        from werkzeug.middleware.proxy_fix import ProxyFix
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

    db.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)

    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Connectez-vous pour accéder à cette page.'
    login_manager.login_message_category = 'warning'

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    from app.auth.routes import auth_bp
    from app.client.routes import client_bp
    from app.admin.routes import admin_bp

    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(client_bp, url_prefix='/client')
    app.register_blueprint(admin_bp, url_prefix='/admin')

    from flask import redirect, url_for

    @app.route('/')
    def index():
        return redirect(url_for('client.vitrine'))

    @app.errorhandler(404)
    def not_found(e):
        return render_template('404.html'), 404

    @app.errorhandler(500)
    def server_error(e):
        return render_template('500.html'), 500

    with app.app_context():
        db.create_all()

    @app.context_processor
    def inject_profil_salon():
        """Injecte le profil salon dans tous les templates (nom, whatsapp...) pour que le client voie ce que l'admin configure."""
        try:
            from app.models import ProfilSalon
            profil = ProfilSalon.get()
            return {'profil_salon': profil}
        except Exception:
            return {'profil_salon': None}

    @app.cli.command('init-admin')
    @click.option('--email', default=lambda: os.environ.get('ADMIN_EMAIL'))
    @click.option('--password', default=lambda: os.environ.get('ADMIN_PASSWORD'))
    @click.option('--nom', default=lambda: os.environ.get('ADMIN_NOM', 'Coiffeur'))
    def init_admin(email, password, nom):
        """Crée le compte coiffeur initial (à lancer une fois en prod via le shell Render)."""
        if not email or not password:
            click.echo("✕ Fournir --email et --password, ou ADMIN_EMAIL / ADMIN_PASSWORD dans l'env.")
            return
        if User.query.filter_by(email=email).first():
            click.echo(f"ℹ Le compte {email} existe déjà.")
            return
        admin = User(nom=nom, email=email, role='coiffeur')
        admin.set_password(password)
        db.session.add(admin)
        db.session.commit()
        click.echo(f"✓ Admin créé : {email}")

    return app
