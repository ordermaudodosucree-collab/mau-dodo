import os
from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey, func
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./mau_dodo.db")

# Render utilise postgres:// mais SQLAlchemy a besoin de postgresql://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False}
    )
else:
    engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# ──────────────────────────────────────────
# TABLE : commandes
# ──────────────────────────────────────────
class Commande(Base):
    __tablename__ = "commandes"

    id                = Column(Integer, primary_key=True, index=True)
    reference         = Column(String, unique=True, index=True, nullable=False)  # ex: CMD-0042
    numero_commande   = Column(String, nullable=True)   # N° du bon de commande client (ex: 300043)
    client            = Column(String, nullable=False)
    email_client      = Column(String, nullable=True)
    telephone_client  = Column(String, nullable=True)
    statut            = Column(String, default="recu")  # recu | production | livraison | livre
    pdf_nom           = Column(String, nullable=True)   # nom original du fichier
    pdf_chemin        = Column(String, nullable=True)   # chemin relatif sur le serveur
    date_commande     = Column(String, nullable=True)   # date sur le bon (ex: 25/05/2026)
    date_livraison    = Column(String, nullable=True)   # date livraison impérative
    date_reception    = Column(DateTime, default=func.now())  # date où l'email a été reçu
    date_statut       = Column(DateTime, default=func.now(), onupdate=func.now())

    produits = relationship("Produit", back_populates="commande", cascade="all, delete")


# ──────────────────────────────────────────
# TABLE : produits
# ──────────────────────────────────────────
class Produit(Base):
    __tablename__ = "produits"

    id           = Column(Integer, primary_key=True, index=True)
    commande_id  = Column(Integer, ForeignKey("commandes.id"), nullable=False)
    ean          = Column(String, nullable=True)   # code-barres EAN-13 (ex: 6091314110022)
    nom          = Column(String, nullable=False)  # ex: PATE DE FRUIT ANANAS 200G
    quantite     = Column(Integer, nullable=False) # ex: 12
    fait         = Column(Integer, default=0)      # 0 = non coché, 1 = coché

    commande = relationship("Commande", back_populates="produits")


# ──────────────────────────────────────────
# Création des tables au démarrage
# ──────────────────────────────────────────
def init_db():
    Base.metadata.create_all(bind=engine)


# ──────────────────────────────────────────
# Dépendance FastAPI
# ──────────────────────────────────────────
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()