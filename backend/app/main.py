import os
import shutil
import json
from typing import List, Optional

from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, WebSocket, WebSocketDisconnect, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from .database import init_db, get_db, MatierePremiere, Recette, RecetteIngredient
from . import crud, schemas
from .pdf_parser import extraire_commande
from sqlalchemy import text as sqltext
from .notifier import notif_nouvelle_commande, notif_rupture_stock


# ──────────────────────────────────────────
# INITIALISATION
# ──────────────────────────────────────────
app = FastAPI(title="Mau Dodo Sucrée API")

# Dossier de stockage des PDFs
STORAGE_DIR = "storage/commandes"
os.makedirs(STORAGE_DIR, exist_ok=True)

# Créer les tables au démarrage
import threading

@app.on_event("startup")
def startup():
    # Migration automatique PostgreSQL
    try:
        from sqlalchemy import text as sqltext
        with database.engine.connect() as conn:
            conn.execute(sqltext(
                "ALTER TABLE commandes ADD COLUMN IF NOT EXISTS montant_total INTEGER;"
            ))
            conn.execute(sqltext(
                "CREATE TABLE IF NOT EXISTS stocks ("
                "id SERIAL PRIMARY KEY, ean VARCHAR, nom VARCHAR NOT NULL UNIQUE,"
                "quantite INTEGER DEFAULT 0, seuil_alerte INTEGER DEFAULT 50,"
                "date_maj TIMESTAMP DEFAULT NOW());"
            ))
            conn.execute(sqltext(
                "CREATE TABLE IF NOT EXISTS mouvements_stock ("
                "id SERIAL PRIMARY KEY, stock_id INTEGER REFERENCES stocks(id),"
                "type VARCHAR NOT NULL, quantite INTEGER NOT NULL,"
                "motif VARCHAR, date TIMESTAMP DEFAULT NOW());"
            ))

            conn.execute(sqltext(
                "CREATE TABLE IF NOT EXISTS matieres_premieres ("
                "id SERIAL PRIMARY KEY, nom VARCHAR NOT NULL UNIQUE,"
                "unite VARCHAR NOT NULL, stock INTEGER DEFAULT 0,"
                "seuil_alerte INTEGER DEFAULT 0,"
                "date_maj TIMESTAMP DEFAULT NOW());"
            ))
            conn.execute(sqltext(
                "CREATE TABLE IF NOT EXISTS recettes ("
                "id SERIAL PRIMARY KEY, produit_nom VARCHAR NOT NULL UNIQUE,"
                "grammage INTEGER NOT NULL, date_maj TIMESTAMP DEFAULT NOW());"
            ))
            conn.execute(sqltext(
                "CREATE TABLE IF NOT EXISTS recette_ingredients ("
                "id SERIAL PRIMARY KEY,"
                "recette_id INTEGER REFERENCES recettes(id),"
                "matiere_premiere_id INTEGER REFERENCES matieres_premieres(id),"
                "quantite INTEGER NOT NULL);"
            ))

            conn.commit()
    except Exception as e:
        print(f'Migration info: {e}')

    init_db()

    # Lancer le watcher Gmail en arrière-plan
    if os.getenv("GMAIL_ADDRESS") and os.getenv("GMAIL_APP_PASSWORD"):
        def lancer_watcher():
            import time
            from .email_watcher import verifier_nouveaux_emails
            while True:
                verifier_nouveaux_emails()
                time.sleep(120)
        thread = threading.Thread(target=lancer_watcher, daemon=True)
        thread.start()

# CORS — permet au frontend React (Vercel) de communiquer avec ce backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # on restreindra à l'URL Vercel en production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ──────────────────────────────────────────
# WEBSOCKETS — mises à jour temps réel
# ──────────────────────────────────────────
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_text(json.dumps(message))
            except Exception:
                pass

manager = ConnectionManager()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)


# ──────────────────────────────────────────
# ROUTES — COMMANDES
# ──────────────────────────────────────────

@app.get("/")
def root():
    return {"message": "Mau Dodo Sucrée API opérationnelle 🍬"}

@app.head("/")
def root_head():
    return Response(status_code=200)


@app.get("/commandes", response_model=List[schemas.Commande])
def lister_commandes(db: Session = Depends(get_db)):
    """Retourne toutes les commandes pour le Kanban."""
    return crud.lister_commandes(db)


@app.get("/commandes/recherche", response_model=List[schemas.Commande])
def rechercher(q: str, db: Session = Depends(get_db)):
    """Recherche par référence, client ou produit."""
    return crud.rechercher_commandes(db, q)


@app.get("/commandes/{reference}", response_model=schemas.Commande)
def get_commande(reference: str, db: Session = Depends(get_db)):
    """Récupère une commande par sa référence (ex: CMD-0042)."""
    commande = crud.get_commande(db, reference)
    if not commande:
        raise HTTPException(status_code=404, detail="Commande introuvable")
    return commande


@app.post("/commandes", response_model=schemas.Commande)
async def creer_commande(
    pdf: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Reçoit un PDF, extrait les infos automatiquement
    et crée la commande dans la base de données.
    """
    # Sauvegarder le PDF temporairement
    tmp_path = f"/tmp/{pdf.filename}"
    with open(tmp_path, "wb") as f:
        shutil.copyfileobj(pdf.file, f)

    # Extraire les infos du PDF
    try:
        data = extraire_commande(tmp_path)
        import logging
        logging.error(f"PDF parsé: client='{data.get('client')}', strip='{data.get('client', '').strip()}', produits={len(data.get('produits', []))}")
    except Exception as e:
        raise HTTPException(400, f"Erreur PDF: {e}")

    if not data.get("client", "").strip() or not data.get("produits"):
        raise HTTPException(status_code=400, detail="PDF invalide ou format non reconnu")

    # Créer la commande en base pour obtenir la référence
    commande_data = schemas.CommandeCreate(
        client=data["client"],
        email_client=data.get("email_client"),
        telephone_client=data.get("telephone_client"),
        numero_commande=data.get("numero_commande"),
        date_commande=data.get("date_commande"),
        date_livraison=data.get("date_livraison"),
        produits=[schemas.ProduitCreate(**p) for p in data["produits"]]
    )

    # Sauvegarder le PDF dans le bon dossier
    # On crée d'abord la commande pour obtenir la référence
    db_commande = crud.creer_commande(db, commande_data)
    dossier = f"{STORAGE_DIR}/{db_commande.reference}"
    os.makedirs(dossier, exist_ok=True)
    pdf_chemin = f"{dossier}/{pdf.filename}"
    shutil.move(tmp_path, pdf_chemin)

    # Mettre à jour le chemin PDF en base
    db_commande.pdf_nom = pdf.filename
    db_commande.pdf_chemin = pdf_chemin
    db.commit()
    db.refresh(db_commande)

# Notifier tous les clients connectés
    await manager.broadcast({"type": "nouvelle_commande", "reference": db_commande.reference})

    # Envoyer notification email nouvelle commande
    notif_nouvelle_commande(db_commande)

    return db_commande

@app.patch("/commandes/{reference}/statut", response_model=schemas.Commande)
async def changer_statut(
    reference: str,
    update: schemas.CommandeUpdate,
    db: Session = Depends(get_db)
):
    """Change le statut d'une commande (recu → production → livraison → livre)."""
    statuts_valides = ["recu", "production", "livraison", "livre"]
    if update.statut not in statuts_valides:
        raise HTTPException(status_code=400, detail=f"Statut invalide. Valeurs: {statuts_valides}")

    commande = crud.changer_statut(db, reference, update.statut)
    if not commande:
        raise HTTPException(status_code=404, detail="Commande introuvable")

    # Déduire le stock automatiquement quand livré
    if update.statut == "livre":
        crud.deduire_stock_commande(db, commande.id)

    # Notifier tous les clients connectés
    await manager.broadcast({
        "type": "statut_change",
        "reference": reference,
        "statut": update.statut
    })

    return commande


# ──────────────────────────────────────────
# ROUTES — PRODUITS
# ──────────────────────────────────────────

@app.patch("/produits/{produit_id}", response_model=schemas.Produit)
async def maj_produit(
    produit_id: int,
    update: schemas.ProduitUpdate,
    db: Session = Depends(get_db)
):
    """Coche ou décoche un produit."""
    produit = crud.maj_produit(db, produit_id, update.fait)
    if not produit:
        raise HTTPException(status_code=404, detail="Produit introuvable")

    # Notifier tous les clients connectés
    await manager.broadcast({
        "type": "produit_update",
        "produit_id": produit_id,
        "fait": update.fait
    })

    return produit

# ──────────────────────────────────────────
# ROUTES — STOCKS
# ──────────────────────────────────────────

@app.get("/stocks")
def lister_stocks(db: Session = Depends(get_db)):
    """Retourne tous les stocks."""
    return crud.lister_stocks(db)

@app.post("/stocks")
def creer_stock(stock: schemas.StockCreate, db: Session = Depends(get_db)):
    """Crée ou met à jour un produit en stock."""
    return crud.creer_ou_maj_stock(db,
        nom=stock.nom, ean=stock.ean,
        quantite=stock.quantite, seuil_alerte=stock.seuil_alerte)

@app.patch("/stocks/{stock_id}")
def maj_stock(stock_id: int, update: schemas.StockUpdate, db: Session = Depends(get_db)):
    """Met à jour le seuil d'alerte d'un stock."""
    stock = db.query(database.Stock).filter(database.Stock.id == stock_id).first()
    if not stock:
        raise HTTPException(status_code=404, detail="Stock introuvable")
    if update.seuil_alerte is not None:
        stock.seuil_alerte = update.seuil_alerte
    db.commit()
    db.refresh(stock)
    return stock

@app.post("/stocks/{stock_id}/entree")
async def entree_stock(stock_id: int, mouvement: schemas.MouvementStockBase, db: Session = Depends(get_db)):
    """Ajoute des unités au stock manuellement."""
    stock = crud.maj_stock_quantite(db, stock_id, mouvement.quantite, "entree", mouvement.motif)
    if not stock:
        raise HTTPException(status_code=404, detail="Stock introuvable")
    await manager.broadcast({"type": "stock_update", "stock_id": stock_id})
    return stock

@app.post("/stocks/{stock_id}/sortie")
async def sortie_stock(stock_id: int, mouvement: schemas.MouvementStockBase, db: Session = Depends(get_db)):
    """Retire des unités du stock manuellement."""
    stock = crud.maj_stock_quantite(db, stock_id, mouvement.quantite, "sortie", mouvement.motif)
    if not stock:
        raise HTTPException(status_code=404, detail="Stock introuvable")
    await manager.broadcast({"type": "stock_update", "stock_id": stock_id})
    # Notification rupture stock
    if stock.quantite <= stock.seuil_alerte:
        notif_rupture_stock(stock.nom, stock.quantite, stock.seuil_alerte)
    return stock

@app.get("/stocks/alertes")
def stocks_en_alerte(db: Session = Depends(get_db)):
    """Retourne les stocks sous le seuil d'alerte."""
    return crud.stocks_en_alerte(db)


# ──────────────────────────────────────────
# ROUTES — DASHBOARD
# ──────────────────────────────────────────

@app.get("/dashboard")
def get_dashboard(periode: str = "mois", db: Session = Depends(get_db)):
    """Retourne les statistiques du dashboard."""
    return crud.get_dashboard_stats(db, periode)


# ──────────────────────────────────────────
# DÉDUCTION STOCK AUTOMATIQUE À LA LIVRAISON
# ──────────────────────────────────────────

# ──────────────────────────────────────────
# MIGRATION TEMPORAIRE — à supprimer après
# ──────────────────────────────────────────
@app.post("/migration")
def migration(db: Session = Depends(get_db)):
    try:
        db.execute(sqltext(
            "ALTER TABLE commandes ADD COLUMN IF NOT EXISTS montant_total INTEGER;"
        ))
        db.execute(sqltext(
            "CREATE TABLE IF NOT EXISTS stocks ("
            "id SERIAL PRIMARY KEY,"
            "ean VARCHAR,"
            "nom VARCHAR NOT NULL UNIQUE,"
            "quantite INTEGER DEFAULT 0,"
            "seuil_alerte INTEGER DEFAULT 50,"
            "date_maj TIMESTAMP DEFAULT NOW());"
        ))
        db.execute(sqltext(
            "CREATE TABLE IF NOT EXISTS mouvements_stock ("
            "id SERIAL PRIMARY KEY,"
            "stock_id INTEGER REFERENCES stocks(id),"
            "type VARCHAR NOT NULL,"
            "quantite INTEGER NOT NULL,"
            "motif VARCHAR,"
            "date TIMESTAMP DEFAULT NOW());"
        ))
        db.commit()
        return {"message": "Migration réussie !"}
    except Exception as e:
        return {"erreur": str(e)}

# ──────────────────────────────────────────
# ROUTES — MATIERES PREMIERES
# ──────────────────────────────────────────

@app.get("/matieres-premieres")
def lister_matieres_premieres(db: Session = Depends(get_db)):
    return crud.lister_matieres_premieres(db)

@app.post("/matieres-premieres")
def creer_matiere_premiere(mp: schemas.MatierePremiereCreate, db: Session = Depends(get_db)):
    return crud.creer_matiere_premiere(db, mp.nom, mp.unite, mp.stock, mp.seuil_alerte)

@app.patch("/matieres-premieres/{mp_id}")
def maj_matiere_premiere(mp_id: int, update: schemas.MatierePremiereUpdate, db: Session = Depends(get_db)):
    mp = crud.maj_stock_matiere_premiere(db, mp_id, update.stock, update.seuil_alerte)
    if not mp:
        raise HTTPException(status_code=404, detail="Matiere premiere introuvable")
    return mp


# ──────────────────────────────────────────
# ROUTES — RECETTES
# ──────────────────────────────────────────

@app.get("/recettes")
def lister_recettes(db: Session = Depends(get_db)):
    try:
        from sqlalchemy import text as sqltext

        # Récupérer les recettes
        recettes_raw = db.execute(
            sqltext("SELECT id, produit_nom, grammage FROM recettes ORDER BY produit_nom")).fetchall()

        result = []
        for r in recettes_raw:
            # Récupérer les ingrédients de chaque recette
            ings_raw = db.execute(sqltext(
                f"SELECT ri.id, ri.quantite, mp.id as mp_id, mp.nom, mp.unite "
                f"FROM recette_ingredients ri "
                f"JOIN matieres_premieres mp ON mp.id = ri.matiere_premiere_id "
                f"WHERE ri.recette_id = {r[0]}"
            )).fetchall()

            ingredients = [
                {"id": i[0], "quantite": i[1], "matiere_premiere": {"id": i[2], "nom": i[3], "unite": i[4]}}
                for i in ings_raw
            ]

            result.append({
                "id": r[0],
                "produit_nom": r[1],
                "grammage": r[2],
                "ingredients": ingredients
            })

        return result
    except Exception as e:
        log.error(f"Erreur GET recettes: {e}")
        import traceback
        log.error(traceback.format_exc())
        return []



@app.post("/recettes")
def creer_recette(recette: schemas.RecetteCreate, db: Session = Depends(get_db)):
    return crud.creer_recette(
        db,
        recette.produit_nom,
        recette.grammage,
        [{"matiere_premiere_id": i.matiere_premiere_id, "quantite": i.quantite}
         for i in recette.ingredients]
    )


# ──────────────────────────────────────────
# ROUTES — CALCUL BESOINS PAR COMMANDE
# ──────────────────────────────────────────

@app.get("/commandes/{commande_id}/besoins")
def calculer_besoins(commande_id: int, db: Session = Depends(get_db)):
    try:
        besoins = crud.calculer_besoins(db, commande_id)
        return besoins
    except Exception as e:
        import logging, traceback
        logging.error(f"Erreur besoins: {e}")
        logging.error(traceback.format_exc())
        return []


@app.get("/debug/tables")
def debug_tables(db: Session = Depends(get_db)):
    try:
        from sqlalchemy import text as sqltext
        result = db.execute(sqltext(
            "SELECT table_name FROM information_schema.tables WHERE table_schema='public';"
        ))
        tables = [row[0] for row in result]
        return {"tables": tables}
    except Exception as e:
        return {"error": str(e)}

@app.delete("/recettes/{recette_id}")
def supprimer_recette(recette_id: int, db: Session = Depends(get_db)):
    try:
        from sqlalchemy import text as sqltext
        db.execute(sqltext(f"DELETE FROM recette_ingredients WHERE recette_id = {recette_id}"))
        db.execute(sqltext(f"DELETE FROM recettes WHERE id = {recette_id}"))
        db.commit()
        return {"message": "Recette supprimée"}
    except Exception as e:
        return {"error": str(e)}

@app.delete("/commandes/{reference}")
def supprimer_commande(reference: str, db: Session = Depends(get_db)):
    try:
        from sqlalchemy import text as sqltext
        commande = crud.get_commande(db, reference)
        if not commande:
            raise HTTPException(status_code=404, detail="Commande introuvable")
        db.execute(sqltext(f"DELETE FROM produits WHERE commande_id = {commande.id}"))
        db.execute(sqltext(f"DELETE FROM commandes WHERE id = {commande.id}"))
        db.commit()
        return {"message": f"Commande {reference} supprimée"}
    except Exception as e:
        return {"error": str(e)}