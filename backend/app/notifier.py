import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
import logging


log = logging.getLogger(__name__)

GMAIL_ADDRESS      = os.getenv("GMAIL_ADDRESS")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")
NOTIFICATION_EMAIL = os.getenv("NOTIFICATION_EMAIL")

def envoyer_email(sujet: str, corps: str):
    """Envoie un email de notification via Brevo."""
    if not all([NOTIFICATION_EMAIL, os.getenv("BREVO_API_KEY")]):
        log.warning("Variables email manquantes — notification ignorée")
        return False
    try:
        import sib_api_v3_sdk
        from sib_api_v3_sdk.rest import ApiException

        configuration = sib_api_v3_sdk.Configuration()
        configuration.api_key['api-key'] = os.getenv("BREVO_API_KEY")

        api_instance = sib_api_v3_sdk.TransactionalEmailsApi(
            sib_api_v3_sdk.ApiClient(configuration))

        send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
            to=[{"email": NOTIFICATION_EMAIL}],
            sender={"name": "Mau Dodo Sucrée", "email": "ordermaudodosucree@gmail.com"},
            subject=sujet,
            html_content=corps
        )

        api_instance.send_transac_email(send_smtp_email)
        log.info(f"Notification envoyée : {sujet}")
        return True
    except Exception as e:
        log.error(f"Erreur envoi notification : {e}")
        return False


def notif_nouvelle_commande(commande):
    """Email quand une nouvelle commande est reçue.
    Inclut la date de livraison prévue (date réception + 4 jours)."""

    date_reception = datetime.now()
    date_livraison_prevue = date_reception + timedelta(days=4)
    date_livraison_str = date_livraison_prevue.strftime('%d/%m/%Y')

    # Si le bon de commande a une date de livraison, on l'utilise
    date_affichee = commande.date_livraison if commande.date_livraison else date_livraison_str

    produits_html = "".join([
        f"<tr>"
        f"<td style='padding:8px 12px;border-bottom:1px solid #f0e8e0'>{p.nom}</td>"
        f"<td style='padding:8px 12px;border-bottom:1px solid #f0e8e0;text-align:center;font-family:monospace;font-size:12px'>{p.ean or '—'}</td>"
        f"<td style='padding:8px 12px;border-bottom:1px solid #f0e8e0;text-align:center;font-weight:bold'>×{p.quantite}</td>"
        f"</tr>"
        for p in commande.produits
    ])

    corps = f"""
    <div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto">
      <div style="background:#5C3317;padding:20px;border-radius:10px 10px 0 0">
        <h1 style="color:white;margin:0;font-size:20px">🍬 Mau Dodo Sucrée</h1>
        <p style="color:rgba(255,255,255,.7);margin:5px 0 0">Nouvelle commande reçue</p>
      </div>
      <div style="background:white;padding:24px;border:1px solid #e8d5c4;border-top:none">
        <h2 style="color:#5C3317;margin-top:0">#{commande.reference}</h2>

        <table style="width:100%;margin-bottom:16px">
          <tr>
            <td style="padding:4px 0;color:#7A4828"><strong>Client :</strong></td>
            <td style="padding:4px 0">{commande.client}</td>
          </tr>
          <tr>
            <td style="padding:4px 0;color:#7A4828"><strong>Réf. client :</strong></td>
            <td style="padding:4px 0">{commande.numero_commande or '—'}</td>
          </tr>
          <tr>
            <td style="padding:4px 0;color:#7A4828"><strong>Date de réception :</strong></td>
            <td style="padding:4px 0">{date_reception.strftime('%d/%m/%Y')}</td>
          </tr>
        </table>

        <div style="background:#FEF3E2;border-left:4px solid #D4841A;padding:14px 16px;border-radius:0 8px 8px 0;margin-bottom:20px">
          <p style="margin:0;color:#854F0B;font-size:15px">
            📅 <strong>Date de livraison prévue : {date_affichee}</strong>
          </p>
          <p style="margin:6px 0 0;color:#854F0B;font-size:13px">
            Commande reçue le {date_reception.strftime('%d/%m/%Y')} — livraison à effectuer sous 4 jours
          </p>
        </div>

        <h3 style="color:#5C3317;margin-bottom:8px">Produits commandés ({len(commande.produits)})</h3>
        <table style="width:100%;border-collapse:collapse">
          <thead>
            <tr style="background:#5C3317;color:white">
              <th style="padding:8px 12px;text-align:left;font-size:12px">Produit</th>
              <th style="padding:8px 12px;text-align:center;font-size:12px">EAN</th>
              <th style="padding:8px 12px;text-align:center;font-size:12px">Qté</th>
            </tr>
          </thead>
          <tbody>{produits_html}</tbody>
        </table>
      </div>
      <div style="background:#f5ede6;padding:12px 20px;border-radius:0 0 10px 10px;text-align:center">
        <p style="color:#a0785a;font-size:12px;margin:0">Mau Dodo Sucrée — Notification automatique</p>
      </div>
    </div>
    """
    envoyer_email(
        f"🆕 Nouvelle commande #{commande.reference} — Livraison prévue le {date_affichee}",
        corps
    )


def notif_rupture_stock(stock_nom: str, quantite: int, seuil: int):
    """Email quand un produit est en rupture de stock."""
    corps = f"""
    <div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto">
      <div style="background:#CC0000;padding:20px;border-radius:10px 10px 0 0">
        <h1 style="color:white;margin:0;font-size:20px">🚨 Alerte rupture de stock</h1>
        <p style="color:rgba(255,255,255,.8);margin:5px 0 0">Un produit est sous le seuil d'alerte</p>
      </div>
      <div style="background:white;padding:24px;border:1px solid #e8d5c4;border-top:none">
        <h2 style="color:#CC0000;margin-top:0">{stock_nom}</h2>
        <p><strong>Stock actuel :</strong> <span style="color:#CC0000;font-weight:bold">{quantite} unités</span></p>
        <p><strong>Seuil d'alerte :</strong> {seuil} unités</p>
        <div style="background:#FFEEEE;border-left:4px solid #CC0000;padding:14px 16px;border-radius:0 8px 8px 0;margin-top:16px">
          <p style="margin:0;color:#CC0000">
            🚨 Le stock de <strong>{stock_nom}</strong> est critique.<br>
            Veuillez réapprovisionner rapidement.
          </p>
        </div>
      </div>
      <div style="background:#f5ede6;padding:12px 20px;border-radius:0 0 10px 10px;text-align:center">
        <p style="color:#a0785a;font-size:12px;margin:0">Mau Dodo Sucrée — Notification automatique</p>
      </div>
    </div>
    """
    envoyer_email(
        f"🚨 Rupture stock : {stock_nom} ({quantite} unités restantes)",
        corps
    )