from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


# ──────────────────────────────────────────
# PRODUIT
# ──────────────────────────────────────────
class ProduitBase(BaseModel):
    ean:      Optional[str] = None
    nom:      str
    quantite: int
    fait:     bool = False


class ProduitCreate(ProduitBase):
    pass


class Produit(ProduitBase):
    id:          int
    commande_id: int

    class Config:
        from_attributes = True


# ──────────────────────────────────────────
# COMMANDE
# ──────────────────────────────────────────
class CommandeBase(BaseModel):
    client:           str
    email_client:     Optional[str] = None
    telephone_client: Optional[str] = None
    numero_commande:  Optional[str] = None
    date_commande:    Optional[str] = None
    date_livraison:   Optional[str] = None
    montant_total:    Optional[int] = None


class CommandeCreate(CommandeBase):
    produits: List[ProduitCreate] = []


class CommandeUpdate(BaseModel):
    statut: Optional[str] = None  # recu | production | livraison | livre


class Commande(CommandeBase):
    id:             int
    reference:      str
    statut:         str
    pdf_nom:        Optional[str] = None
    date_reception: datetime
    produits:       List[Produit] = []

    class Config:
        from_attributes = True


# ──────────────────────────────────────────
# MISE A JOUR D'UN PRODUIT (cocher/décocher)
# ──────────────────────────────────────────
class ProduitUpdate(BaseModel):
    fait: bool

# ──────────────────────────────────────────
# STOCK
# ──────────────────────────────────────────
class StockBase(BaseModel):
    ean: Optional[str] = None
    nom: str
    quantite: int = 0
    seuil_alerte: int = 50

class StockCreate(StockBase):
    pass

class StockUpdate(BaseModel):
    quantite: Optional[int] = None
    seuil_alerte: Optional[int] = None

class MouvementStockBase(BaseModel):
    type: str       # "entree" | "sortie"
    quantite: int
    motif: Optional[str] = None

class Stock(StockBase):
    id: int
    date_maj: datetime
    class Config:
        from_attributes = True

class MouvementStock(MouvementStockBase):
    id: int
    stock_id: int
    date: datetime
    class Config:
        from_attributes = True

# ──────────────────────────────────────────
# DASHBOARD
# ──────────────────────────────────────────
class DashboardStats(BaseModel):
    ca_total: int
    ca_periode: int
    nb_commandes_total: int
    nb_commandes_periode: int
    nb_livraisons_total: int
    nb_livraisons_periode: int
    top_clients: list
    ca_par_jour: list
    stocks_bas: list