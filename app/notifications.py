"""
Système de notifications du salon.
- Flash messages : toujours actifs (affichés dans base.html)
- Email : optionnel, activé seulement si MAIL_USERNAME est configuré dans .env
"""
from flask import flash
from flask_mail import Message
from app import mail


def notifier_coiffeur_nouvelle_demande(rdv):
    """
    Notifie le coiffeur qu'une nouvelle demande vient d'arriver.
    Flash message immédiat + email si configuré.
    """
    flash(
        f'Nouvelle demande de {rdv.client.nom} pour "{rdv.service.nom}" '
        f'le {rdv.debut_datetime.strftime("%d/%m/%Y à %H:%M")}.',
        'info'
    )
    _envoyer_email_optionnel(
        sujet=f'[MonSalon] Nouvelle demande — {rdv.client.nom}',
        corps=f"""
Bonjour,

Une nouvelle demande de rendez-vous vient d'arriver :

- Client  : {rdv.client.nom} ({rdv.client.email})
- Service : {rdv.service.nom}
- Date    : {rdv.debut_datetime.strftime("%d/%m/%Y à %H:%M")}
- Durée   : {rdv.duree_minutes} min
- Fin     : {rdv.fin_datetime.strftime("%H:%M")}

Connectez-vous au dashboard pour accepter ou refuser.
        """.strip()
    )


def notifier_client_confirmation(rdv):
    """Notifie le client que son RDV a été accepté."""
    _envoyer_email_optionnel(
        destinataire=rdv.client.email,
        sujet='[MonSalon] Rendez-vous confirmé !',
        corps=f"""
Bonjour {rdv.client.nom},

Votre rendez-vous a été confirmé :

- Service : {rdv.service.nom}
- Date    : {rdv.debut_datetime.strftime("%d/%m/%Y à %H:%M")}
- Durée   : {rdv.duree_minutes} min

À bientôt chez MonSalon !
        """.strip()
    )


def notifier_client_refus(rdv):
    """Notifie le client que son RDV a été refusé."""
    _envoyer_email_optionnel(
        destinataire=rdv.client.email,
        sujet='[MonSalon] Rendez-vous non disponible',
        corps=f"""
Bonjour {rdv.client.nom},

Nous sommes désolés, votre demande pour "{rdv.service.nom}"
le {rdv.debut_datetime.strftime("%d/%m/%Y à %H:%M")} n'a pas pu être acceptée.

Vous pouvez réserver un autre créneau directement sur le site.

À bientôt !
        """.strip()
    )


def _envoyer_email_optionnel(sujet, corps, destinataire=None):
    """
    Envoie un email seulement si Flask-Mail est configuré.
    Silencieux si MAIL_USERNAME manque (mode dev sans email).
    """
    from flask import current_app
    if not current_app.config.get('MAIL_USERNAME'):
        return  # Email non configuré → on skip silencieusement

    try:
        msg = Message(
            subject=sujet,
            recipients=[destinataire] if destinataire else [current_app.config['MAIL_USERNAME']],
            body=corps
        )
        mail.send(msg)
    except Exception as e:
        current_app.logger.warning(f'Email non envoyé : {e}')
