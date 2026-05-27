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