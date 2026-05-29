import re
import pdfplumber
from collections import defaultdict


def detecter_format(texte: str) -> str:
    """Détecte le format du PDF."""
    if "PURCHASE ORDER" in texte or "Order NO." in texte:
        return "purchase_order"
    if "Bon de commande" in texte or "EAN principal" in texte:
        return "tribeca"
    return "inconnu"


def extraire_tribeca(texte: str, tableaux: list, words: list) -> dict:
    """Format Tribeca/Winners — avec EAN-13."""
    resultat = {
        "numero_commande": None, "client": None, "email_client": None,
        "telephone_client": None, "date_commande": None, "date_livraison": None, "montant_total": None,
        "produits": []
    }

    texte_propre = re.sub(r'([A-Za-z°])\1', r'\1', texte)

    m = re.search(r'commande\s+(\d{5,})\s+Date', texte_propre)
    if m: resultat["numero_commande"] = m.group(1)

    m = re.search(r'Date de commande\s+(\d{2}/\d{2}/\d{4})', texte_propre)
    if m: resultat["date_commande"] = m.group(1)

    m = re.search(r'livraison imp.rative\s+(\d{2}/\d{2}/\d{4})', texte_propre)
    if m: resultat["date_livraison"] = m.group(1)

    if tableaux:
        bloc = tableaux[0][1][1] if len(tableaux[0]) > 1 and len(tableaux[0][1]) > 1 else ""
        for ligne in (bloc or "").split("\n"):
            if (not resultat["client"] and ligne.strip()
                    and not any(x in ligne for x in ["Email", "Téléphone", "Règlement"])):
                resultat["client"] = ligne.strip()
            if "Email" in ligne:
                resultat["email_client"] = ligne.split("Email")[-1].strip()
            if "Téléphone" in ligne:
                resultat["telephone_client"] = ligne.split("Téléphone")[-1].strip()

    lignes_mots = defaultdict(list)
    for w in words:
        y = round(w['top'] / 5) * 5
        lignes_mots[y].append(w['text'])

    pattern_std = re.compile(r'\d{6}\s+(\d{13})\s+(.+?)\s+\d+\s+\d+\s+(\d+)Ar')
    pattern_inv = re.compile(r'^(.+?)\s+\d{6}\s+(\d{13})\s+\d+\s+\d+\s+(\d+)Ar')

    refs_vus = set()
    lignes_triees = sorted(lignes_mots.keys())
    i = 0

    while i < len(lignes_triees):
        y = lignes_triees[i]
        ligne = " ".join(lignes_mots[y])

        m_inv = pattern_inv.search(ligne)
        ean_inv = re.search(r'\d{6}\s+(\d{13})', ligne)
        if m_inv and ean_inv and ean_inv.group(1) not in refs_vus:
            suffixe = ""
            if i + 1 < len(lignes_triees):
                y2 = lignes_triees[i + 1]
                l2 = " ".join(lignes_mots[y2])
                if not re.search(r'\d{6}', l2) and len(l2.strip()) < 15:
                    suffixe = " " + l2.strip()
                    i += 1
            refs_vus.add(ean_inv.group(1))
            resultat["produits"].append({
                "ean": ean_inv.group(1),
                "nom": m_inv.group(1).strip() + suffixe,
                "quantite": int(m_inv.group(3)),
                "fait": False
            })
            i += 1
            continue

        m_std = pattern_std.search(ligne)
        if m_std and m_std.group(1) not in refs_vus:
            refs_vus.add(m_std.group(1))
            nom = m_std.group(2).strip()
            qte = int(m_std.group(3))
            if i + 1 < len(lignes_triees):
                y2 = lignes_triees[i + 1]
                l2 = " ".join(lignes_mots[y2])
                if not re.search(r'\d{6}', l2) and len(l2.strip()) < 15:
                    nom = nom + " " + l2.strip()
                    i += 1
            resultat["produits"].append({
                "ean": m_std.group(1),
                "nom": nom,
                "quantite": qte,
                "fait": False
            })

        i += 1

    return resultat


def extraire_purchase_order(texte: str) -> dict:
    """Format Purchase Order (hôtels, restaurants...)"""
    resultat = {
        "numero_commande": None, "client": None, "email_client": None,
        "telephone_client": None, "date_commande": None, "date_livraison": None, "montant_total": None,
        "produits": []
    }

    m = re.search(r'Order NO\.\s*:\s*([\w\s]+?)(?:\n|DATE)', texte)
    if m: resultat["numero_commande"] = m.group(1).strip()

    m = re.search(r'^TO\s+(.+?)(?:Order NO\.)', texte, re.MULTILINE)
    if m: resultat["client"] = m.group(1).strip()

    m = re.search(r'Phone:(\d+)', texte)
    if m: resultat["telephone_client"] = m.group(1).strip()

    m = re.search(r'DATE\s*:\s*(\d{2}/\d{2}/\d{4})', texte)
    if m: resultat["date_commande"] = m.group(1)

    m = re.search(r'Delivery Date\s*:\s*(\d{2}/\d{2}/\d{4})', texte)
    if m: resultat["date_livraison"] = m.group(1)

    # Montant total Purchase Order
    m = re.search(r'Net Total.*?([\d,]+\.?\d*)', texte)
    if m:
        try:
            resultat["montant_total"] = int(float(m.group(1).replace(',', '')))
        except:
            pass

    # Montant total Tribeca
    m = re.search(r'Montant achat\s+([\d\s]+\.?\d*)\s*MUR', texte_propre)
    if m:
        try:
            resultat["montant_total"] = int(float(m.group(1).replace(' ', '').replace(',', '')))
        except:
            pass

    pattern = re.compile(r'^\d+\s+\d+\s+(.+?)\s+(\d+(?:\.\d+)?)\s+EA\s', re.MULTILINE)
    for m in pattern.finditer(texte):
        nom = m.group(1).strip()
        try:
            qte = int(float(m.group(2)))
        except:
            qte = 0
        resultat["produits"].append({
            "ean": None,
            "nom": nom,
            "quantite": qte,
            "fait": False
        })

    return resultat


def extraire_commande(pdf_chemin: str) -> dict:
    """
    Lit un bon de commande PDF et retourne un dictionnaire structuré.
    Supporte plusieurs formats : Tribeca/Winners, Purchase Order (hôtels).
    """
    with pdfplumber.open(pdf_chemin) as pdf:
        page = pdf.pages[0]
        texte = page.extract_text()
        tableaux = page.extract_tables()
        words = page.extract_words()

    format_pdf = detecter_format(texte)

    if format_pdf == "tribeca":
        return extraire_tribeca(texte, tableaux, words)
    elif format_pdf == "purchase_order":
        return extraire_purchase_order(texte)
    else:
        # Format inconnu — tentative d'extraction générique
        return extraire_purchase_order(texte)


if __name__ == "__main__":
    import json, sys
    chemin = sys.argv[1] if len(sys.argv) > 1 else "test.pdf"
    data = extraire_commande(chemin)
    print(json.dumps(data, ensure_ascii=False, indent=2))
    print(f"\n{len(data['produits'])} produits extraits")