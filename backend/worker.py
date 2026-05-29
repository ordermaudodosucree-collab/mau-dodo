"""
Point d'entrée pour le Background Worker sur Render.
Lance la surveillance Gmail en continu.
"""
import os
import sys

# S'assurer que le dossier backend est dans le path
sys.path.insert(0, os.path.dirname(__file__))

from app.email_watcher import demarrer

if __name__ == "__main__":
    demarrer()