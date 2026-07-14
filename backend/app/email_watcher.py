import imaplib
import email
import os
import time
import requests
import logging
from email.header import decode_header

# ── Configuration ──────────────────────────────────────────────
GMAIL_ADDRESS      = os.getenv("GMAIL_ADDRESS")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")
API_URL            = os.getenv("API_URL", "http://localhost:10000")
CHECK_INTERVAL     = 120  # vérifier toutes les 2 minutes

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [email_watcher] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
log = logging.getLogger(__name__)

# Expéditeurs à ignorer
EXPEDITEURS_IGNORES = ["noreply-apps-scripts", "noreply@", "no-reply@", "donotreply@"]


def decoder(valeur):
    """Décode les en-têtes d'email."""
    if not valeur:
        return ""
    parties = decode_header(valeur)
    resultat = ""
    for partie, encoding in parties:
        if isinstance(partie, bytes):
            resultat += partie.decode(encoding or "utf-8", errors="ignore")
        else:
            resultat += partie
    return resultat


def connecter_gmail():
    """Se connecte à Gmail via IMAP."""
    mail = imaplib.IMAP4_SSL("imap.gmail.com")
    mail.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
    return mail


def extraire_pdfs(msg):
    """Extrait les pièces jointes PDF d'un email."""
    pdfs = []
    for partie in msg.walk():
        if partie.get_content_maintype() == "multipart":
            continue
        if partie.get("Content-Disposition") is None:
            continue
        nom_fichier = partie.get_filename()
        if not nom_fichier:
            continue
        nom_fichier = decoder(nom_fichier)
        if nom_fichier.lower().endswith(".pdf"):
            contenu = partie.get_payload(decode=True)
            chemin_tmp = f"/tmp/{nom_fichier}"
            with open(chemin_tmp, "wb") as f:
                f.write(contenu)
            pdfs.append((nom_fichier, chemin_tmp))
    return pdfs


def envoyer_au_backend(nom_fichier, chemin_pdf):
    """Envoie le PDF au backend FastAPI avec retry."""
    try:
        for tentative in range(3):
            try:
                with open(chemin_pdf, "rb") as f:
                    response = requests.post(
                        f"{API_URL}/commandes",
                        files={"pdf": (nom_fichier, f, "application/pdf")},
                        timeout=120
                    )
                if response.status_code == 200:
                    data = response.json()
                    log.info(f"Commande creee : {data['reference']} — {data['client']}")
                    return True
                else:
                    log.error(f"Erreur backend : {response.status_code} — {response.text}")
                    return False
            except Exception as e:
                log.error(f"Tentative {tentative + 1}/3 echouee : {e}")
                if tentative < 2:
                    time.sleep(10)
        return False
    finally:
        if os.path.exists(chemin_pdf):
            os.remove(chemin_pdf)


def verifier_nouveaux_emails():
    """Vérifie les nouveaux emails non lus avec pièces jointes PDF."""
    try:
        mail = connecter_gmail()
        mail.select("inbox")

        _, messages = mail.search(None, "UNSEEN")
        ids = messages[0].split()

        if not ids:
            log.info("Aucun nouvel email.")
            mail.logout()
            return

        log.info(f"{len(ids)} nouvel(s) email(s) trouvé(s).")

        for email_id in ids:
            _, data = mail.fetch(email_id, "(RFC822)")
            msg = email.message_from_bytes(data[0][1])

            sujet = decoder(msg.get("Subject", ""))
            expediteur = decoder(msg.get("From", ""))
            log.info(f"📧 Email de : {expediteur} | Sujet : {sujet}")

            # Ignorer les emails automatiques
            if any(x in expediteur.lower() for x in EXPEDITEURS_IGNORES):
                log.info(f"Email automatique ignoré : {expediteur}")
                mail.store(email_id, "+FLAGS", "\\Seen")
                continue

            # Extraire les PDFs
            pdfs = extraire_pdfs(msg)

            if not pdfs:
                log.info("Aucune pièce jointe PDF dans cet email.")
                continue

            for nom_fichier, chemin_pdf in pdfs:
                log.info(f"📄 PDF trouvé : {nom_fichier}")
                envoyer_au_backend(nom_fichier, chemin_pdf)

            # Marquer l'email comme lu
            mail.store(email_id, "+FLAGS", "\\Seen")

        mail.logout()

    except Exception as e:
        log.error(f"Erreur connexion Gmail : {e}")


def demarrer():
    """Lance la surveillance en boucle."""
    log.info(f"Démarrage surveillance Gmail : {GMAIL_ADDRESS}")
    log.info(f"Vérification toutes les {CHECK_INTERVAL // 60} minutes")

    while True:
        verifier_nouveaux_emails()
        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    demarrer()