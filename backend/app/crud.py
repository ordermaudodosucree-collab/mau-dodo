from sqlalchemy.orm import Session
from datetime import datetime
from . import database, schemas


# ──────────────────────────────────────────
# GÉNÉRER UNE RÉFÉRENCE UNIQUE
# ex: CMD-0001, CMD-0042
# ──────────────────────────────────────────
def generer_reference(db: Session) -> str:
    total = db.query(database.Commande).count()
    return f"CMD-{str(total + 1).zfill(4)}"


# ──────────────────────────────────────────
# CRÉER UNE COMMANDE
# ──────────────────────────────────────────
def creer_commande(db: Session, commande: schemas.CommandeCreate, pdf_nom: str = None, pdf_chemin: str = None):
    reference = generer_reference(db)

    db_commande = database.Commande(
        reference=reference,
        numero_commande=commande.numero_commande,
        client=commande.client,
        email_client=commande.email_client,
        telephone_client=commande.telephone_client,
        statut="recu",
        pdf_nom=pdf_nom,
        pdf_chemin=pdf_chemin,
        date_commande=commande.date_commande,
        date_livraison=commande.date_livraison,
    )
    db.add(db_commande)
    db.flush()  # pour obtenir l'id avant le commit

    for p in commande.produits:
        db_produit = database.Produit(
            commande_id=db_commande.id,
            ean=p.ean,
            nom=p.nom,
            quantite=p.quantite,
            fait=0,
        )
        db.add(db_produit)

    db.commit()
    db.refresh(db_commande)
    return db_commande


# ──────────────────────────────────────────
# LISTER TOUTES LES COMMANDES
# ──────────────────────────────────────────
def lister_commandes(db: Session):
    return db.query(database.Commande).order_by(database.Commande.date_reception.desc()).all()


# ──────────────────────────────────────────
# RÉCUPÉRER UNE COMMANDE PAR RÉFÉRENCE
# ──────────────────────────────────────────
def get_commande(db: Session, reference: str):
    return db.query(database.Commande).filter(database.Commande.reference == reference).first()


# ──────────────────────────────────────────
# CHANGER LE STATUT D'UNE COMMANDE
# recu → production → livraison → livre
# ──────────────────────────────────────────
def changer_statut(db: Session, reference: str, nouveau_statut: str):
    commande = get_commande(db, reference)
    if not commande:
        return None
    commande.statut = nouveau_statut
    commande.date_statut = datetime.now()
    db.commit()
    db.refresh(commande)
    return commande


# ──────────────────────────────────────────
# COCHER / DÉCOCHER UN PRODUIT
# ──────────────────────────────────────────
def maj_produit(db: Session, produit_id: int, fait: bool):
    produit = db.query(database.Produit).filter(database.Produit.id == produit_id).first()
    if not produit:
        return None
    produit.fait = 1 if fait else 0
    db.commit()
    db.refresh(produit)
    return produit


# ──────────────────────────────────────────
# RECHERCHER DES COMMANDES
# par référence, client ou nom de produit
# ──────────────────────────────────────────
def rechercher_commandes(db: Session, q: str):
    q = f"%{q}%"
    return (
        db.query(database.Commande)
        .filter(
            database.Commande.reference.ilike(q) |
            database.Commande.client.ilike(q) |
            database.Commande.numero_commande.ilike(q) |
            database.Commande.produits.any(database.Produit.nom.ilike(q))
        )
        .order_by(database.Commande.date_reception.desc())
        .all()
    )