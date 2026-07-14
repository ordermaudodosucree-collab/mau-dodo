import logging
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from sqlalchemy import func as sqlfunc
from . import database, schemas

log = logging.getLogger(__name__)


# ──────────────────────────────────────────
# GÉNÉRER UNE RÉFÉRENCE UNIQUE
# ──────────────────────────────────────────
def generer_reference(db: Session) -> str:
    total = db.query(database.Commande).count()
    return f"CMD-{str(total + 1).zfill(4)}"


# ──────────────────────────────────────────
# COMMANDES
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
        montant_total=commande.montant_total,
    )
    db.add(db_commande)
    db.flush()
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


def lister_commandes(db: Session):
    return db.query(database.Commande).order_by(database.Commande.date_reception.desc()).all()


def get_commande(db: Session, reference: str):
    return db.query(database.Commande).filter(database.Commande.reference == reference).first()


def changer_statut(db: Session, reference: str, nouveau_statut: str):
    commande = get_commande(db, reference)
    if not commande:
        return None
    commande.statut = nouveau_statut
    commande.date_statut = datetime.now()
    db.commit()
    db.refresh(commande)
    return commande


def maj_produit(db: Session, produit_id: int, fait: bool):
    produit = db.query(database.Produit).filter(database.Produit.id == produit_id).first()
    if not produit:
        return None
    produit.fait = 1 if fait else 0
    db.commit()
    db.refresh(produit)
    return produit


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


# ──────────────────────────────────────────
# STOCKS
# ──────────────────────────────────────────
def lister_stocks(db: Session):
    return db.query(database.Stock).order_by(database.Stock.nom).all()


def get_stock_par_nom(db: Session, nom: str):
    return db.query(database.Stock).filter(database.Stock.nom == nom).first()


def get_stock_par_ean(db: Session, ean: str):
    return db.query(database.Stock).filter(database.Stock.ean == ean).first()


def creer_ou_maj_stock(db: Session, nom: str, ean: str = None, quantite: int = 0, seuil_alerte: int = 50):
    stock = get_stock_par_nom(db, nom)
    if not stock:
        stock = database.Stock(nom=nom, ean=ean, quantite=quantite, seuil_alerte=seuil_alerte)
        db.add(stock)
        db.commit()
        db.refresh(stock)
    return stock


def maj_stock_quantite(db: Session, stock_id: int, quantite: int, type: str, motif: str = None):
    stock = db.query(database.Stock).filter(database.Stock.id == stock_id).first()
    if not stock:
        return None
    if type == "entree":
        stock.quantite += quantite
    elif type == "sortie":
        stock.quantite = max(0, stock.quantite - quantite)
    mouvement = database.MouvementStock(
        stock_id=stock_id, type=type, quantite=quantite, motif=motif)
    db.add(mouvement)
    db.commit()
    db.refresh(stock)
    return stock


def stocks_en_alerte(db: Session):
    return db.query(database.Stock).filter(
        database.Stock.quantite <= database.Stock.seuil_alerte).all()


def deduire_stock_commande(db: Session, commande_id: int):
    commande = db.query(database.Commande).filter(
        database.Commande.id == commande_id).first()
    if not commande:
        return
    for produit in commande.produits:
        stock = get_stock_par_nom(db, produit.nom)
        if not stock and produit.ean:
            stock = get_stock_par_ean(db, produit.ean)
        if stock:
            maj_stock_quantite(db, stock.id, produit.quantite,
                type="sortie", motif=commande.reference)


# ──────────────────────────────────────────
# DASHBOARD
# ──────────────────────────────────────────
def get_dashboard_stats(db: Session, periode: str = "mois"):
    now = datetime.now()
    if periode == "semaine":
        debut = now - timedelta(days=7)
    elif periode == "mois":
        debut = now.replace(day=1, hour=0, minute=0, second=0)
    elif periode == "annee":
        debut = now.replace(month=1, day=1, hour=0, minute=0, second=0)
    else:
        debut = now - timedelta(days=30)

    toutes = db.query(database.Commande).all()
    periode_commandes = db.query(database.Commande).filter(
        database.Commande.date_reception >= debut).all()

    livraisons_total = db.query(database.Commande).filter(
        database.Commande.statut == "livre").all()
    livraisons_periode = db.query(database.Commande).filter(
        database.Commande.statut == "livre").all()

    ca_total = sum(c.montant_total or 0 for c in toutes)
    ca_periode = sum(c.montant_total or 0 for c in periode_commandes)

    clients = {}
    for c in toutes:
        if c.client:
            clients[c.client] = clients.get(c.client, 0) + (c.montant_total or 0)
    top_clients = sorted([{"client": k, "ca": v} for k, v in clients.items()],
        key=lambda x: x["ca"], reverse=True)[:5]

    ca_par_jour = {}
    for c in db.query(database.Commande).filter(
            database.Commande.date_reception >= now - timedelta(days=30)).all():
        jour = c.date_reception.strftime("%d/%m")
        ca_par_jour[jour] = ca_par_jour.get(jour, 0) + (c.montant_total or 0)
    ca_par_jour_liste = [{"jour": k, "ca": v} for k, v in sorted(ca_par_jour.items())]

    alertes = stocks_en_alerte(db)

    return {
        "ca_total": ca_total,
        "ca_periode": ca_periode,
        "nb_commandes_total": len(toutes),
        "nb_commandes_periode": len(periode_commandes),
        "nb_livraisons_total": len(livraisons_total),
        "nb_livraisons_periode": len(livraisons_periode),
        "top_clients": top_clients,
        "ca_par_jour": ca_par_jour_liste,
        "stocks_bas": [{"nom": s.nom, "quantite": s.quantite, "seuil": s.seuil_alerte} for s in alertes]
    }


# ──────────────────────────────────────────
# MATIERES PREMIERES
# ──────────────────────────────────────────
def lister_matieres_premieres(db: Session):
    return db.query(database.MatierePremiere).order_by(database.MatierePremiere.nom).all()


def creer_matiere_premiere(db: Session, nom: str, unite: str, stock: int = 0, seuil_alerte: int = 0):
    mp = database.MatierePremiere(nom=nom, unite=unite, stock=stock, seuil_alerte=seuil_alerte)
    db.add(mp)
    db.commit()
    db.refresh(mp)
    return mp


def maj_stock_matiere_premiere(db: Session, mp_id: int, stock: int, seuil_alerte: int = None):
    mp = db.query(database.MatierePremiere).filter(database.MatierePremiere.id == mp_id).first()
    if not mp:
        return None
    mp.stock = stock
    if seuil_alerte is not None:
        mp.seuil_alerte = seuil_alerte
    db.commit()
    db.refresh(mp)
    return mp


# ──────────────────────────────────────────
# RECETTES
# ──────────────────────────────────────────
def lister_recettes(db: Session):
    return db.query(database.Recette).order_by(database.Recette.produit_nom).all()


def creer_recette(db: Session, produit_nom: str, grammage: int, ingredients: list):
    try:
        recette = database.Recette(produit_nom=produit_nom, grammage=grammage)
        db.add(recette)
        db.flush()
        log.error(f"Recette creee id: {recette.id}")
        for ing in ingredients:
            log.error(f"Ajout ingredient: {ing}")
            ri = database.RecetteIngredient(
                recette_id=recette.id,
                matiere_premiere_id=ing["matiere_premiere_id"],
                quantite=ing["quantite"]
            )
            db.add(ri)
        db.commit()
        db.refresh(recette)
        log.error(f"Recette finalisee: {recette.id}")
        return recette
    except Exception as e:
        db.rollback()
        log.error(f"ERREUR creer_recette: {e}")
        import traceback
        log.error(traceback.format_exc())
        return None

def calculer_besoins(db: Session, commande_id: int):
    commande = db.query(database.Commande).filter(database.Commande.id == commande_id).first()
    if not commande:
        return []

    resultat = []

    for produit in commande.produits:
        recette = db.query(database.Recette).filter(
            database.Recette.produit_nom.ilike(f"%{produit.nom}%")
        ).first()

        if not recette:
            continue

        besoins_produit = []
        for ingredient in recette.ingredients:
            mp = db.query(database.MatierePremiere).filter(
                database.MatierePremiere.id == ingredient.matiere_premiere_id).first()
            if mp:
                quantite_totale = ingredient.quantite * produit.quantite
                besoins_produit.append({
                    "matiere_premiere": mp.nom,
                    "unite": mp.unite,
                    "quantite_necessaire": quantite_totale,
                    "stock_disponible": mp.stock or 0,
                    "manque": (mp.stock or 0) < quantite_totale
                })

        if besoins_produit:
            resultat.append({
                "produit": produit.nom,
                "quantite_commandee": produit.quantite,
                "besoins": besoins_produit
            })

    return resultat