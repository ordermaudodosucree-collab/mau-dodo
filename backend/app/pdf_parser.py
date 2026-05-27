import re
import pdfplumber
from collections import defaultdict


def extraire_commande(pdf_chemin: str) -> dict:
    """
    Lit un bon de commande PDF (format Tribeca/Winners)
    et retourne un dictionnaire structuré.
    """
    with pdfplumber.open(pdf_chemin) as pdf:
        page = pdf.pages[0]
        texte = page.extract_text()
        tableaux = page.extract_tables()
        words = page.extract_words()

    resultat = {
        "numero_commande": None,
        "client": None,
        "email_client": None,
        "telephone_client": None,
        "date_commande": None,
        "date_livraison": None,
        "produits": []
    }

    texte_propre = re.sub(r'([A-Za-z°])\1', r'\1', texte)

    m = re.search(r'commande\s+(\d{5,})\s+Date', texte_propre)
    if m:
        resultat["numero_commande"] = m.group(1)

    m = re.search(r'Date de commande\s+(\d{2}/\d{2}/\d{4})', texte_propre)
    if m:
        resultat["date_commande"] = m.group(1)

    m = re.search(r'livraison imp.rative\s+(\d{2}/\d{2}/\d{4})', texte_propre)
    if m:
        resultat["date_livraison"] = m.group(1)

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

    # Pattern standard : N°article EAN libellé nb pcb qtéAr
    pattern_std = re.compile(r'\d{6}\s+(\d{13})\s+(.+?)\s+\d+\s+\d+\s+(\d+)Ar')
    # Pattern inversé  : libellé N°article EAN nb pcb qtéAr
    pattern_inv = re.compile(r'^(.+?)\s+\d{6}\s+(\d{13})\s+\d+\s+\d+\s+(\d+)Ar')

    refs_vus = set()
    lignes_triees = sorted(lignes_mots.keys())
    i = 0

    while i < len(lignes_triees):
        y = lignes_triees[i]
        ligne = " ".join(lignes_mots[y])

        # Cas inversé
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

        # Cas standard
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


if __name__ == "__main__":
    import json, sys
    chemin = sys.argv[1] if len(sys.argv) > 1 else "test.pdf"
    data = extraire_commande(chemin)
    print(json.dumps(data, ensure_ascii=False, indent=2))
    print(f"\n{len(data['produits'])} produits extraits")