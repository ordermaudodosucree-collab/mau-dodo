import os
import shutil
import json
from typing import List, Optional

from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from .database import init_db, get_db
from . import crud, schemas
from .pdf_parser import extraire_commande

# ──────────────────────────────────────────
# INITIALISATION
# ──────────────────────────────────────────
app = FastAPI(title="Mau Dodo Sucrée API")

# Dossier de stockage des PDFs
STORAGE_DIR = "storage/commandes"
os.makedirs(STORAGE_DIR, exist_ok=True)

# Créer les tables au démarrage
@app.on_event("startup")
def startup():
    init_db()

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
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erreur lecture PDF: {str(e)}")

    if not data["client"] or not data["produits"]:
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