from flask import Flask
from flask_login import LoginManager
from flask_mail import Mail
from app.models import db, User
from config import config

login_manager = LoginManager()
mail = Mail()


def create_app(config_name='default'):
    app = Flask(__name__)
    app.config.from_object(config[config_name])

    # Initialisation des extensions
    db.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)

    # Redirection si non connecté
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Connectez-vous pour accéder à cette page.'
    login_manager.login_message_category = 'warning'

    # Chargement de l'utilisateur depuis la session
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Enregistrement des blueprints
    from app.auth.routes import auth_bp
    from app.client.routes import client_bp
    from app.admin.routes import admin_bp

    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(client_bp, url_prefix='/client')
    app.register_blueprint(admin_bp, url_prefix='/admin')

    # Route principale → redirige selon le rôle
    from flask import redirect, url_for
    from flask_login import current_user

    @app.route('/')
    def index():
        return redirect(url_for('client.vitrine'))

    # Création des tables si elles n'existent pas
    with app.app_context():
        db.create_all()

    return app
