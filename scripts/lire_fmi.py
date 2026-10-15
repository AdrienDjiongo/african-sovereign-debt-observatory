"""Convertit un export WEO du FMI (.xls) en CSV propre : pays, iso3, annee, valeur, projection.

Usage : python scripts/lire_fmi.py data/raw/fmi_dette.xls dette
Resultat : data/processed/fmi_dette.csv
"""
import sys
from pathlib import Path

import pandas as pd
import xlrd

PAYS_AFRIQUE = {
    "Algeria": "DZA", "Angola": "AGO", "Benin": "BEN", "Botswana": "BWA",
    "Burkina Faso": "BFA", "Burundi": "BDI", "Cabo Verde": "CPV", "Cameroon": "CMR",
    "Central African Republic": "CAF", "Chad": "TCD", "Comoros": "COM",
    "Congo, Dem. Rep. of the": "COD", "Congo, Republic of": "COG",
    "Côte d'Ivoire": "CIV", "Djibouti": "DJI", "Egypt": "EGY",
    "Equatorial Guinea": "GNQ", "Eritrea": "ERI", "Eswatini": "SWZ",
    "Ethiopia": "ETH", "Gabon": "GAB", "Gambia, The": "GMB", "Ghana": "GHA",
    "Guinea": "GIN", "Guinea-Bissau": "GNB", "Kenya": "KEN", "Lesotho": "LSO",
    "Liberia": "LBR", "Libya": "LBY", "Madagascar": "MDG", "Malawi": "MWI",
    "Mali": "MLI", "Mauritania": "MRT", "Mauritius": "MUS", "Morocco": "MAR",
    "Mozambique": "MOZ", "Namibia": "NAM", "Niger": "NER", "Nigeria": "NGA",
    "Rwanda": "RWA", "São Tomé and Príncipe": "STP", "Senegal": "SEN",
    "Seychelles": "SYC", "Sierra Leone": "SLE", "Somalia": "SOM",
    "South Africa": "ZAF", "South Sudan, Republic of": "SSD", "Sudan": "SDN",
    "Tanzania": "TZA", "Togo": "TGO", "Tunisia": "TUN", "Uganda": "UGA",
    "Zambia": "ZMB", "Zimbabwe": "ZWE",
}
CEMAC = ["CMR", "GAB", "COG", "TCD", "GNQ", "CAF"]


def lire(chemin, nom):
    # ignore_workbook_corruption : les exports du FMI ont un en-tete OLE un peu abime
    wb = xlrd.open_workbook(chemin, ignore_workbook_corruption=True)
    feuille = wb.sheet_by_index(0)
    entetes = [feuille.cell_value(0, c) for c in range(feuille.ncols)]
    colonnes_annees = {c: int(h) for c, h in enumerate(entetes) if isinstance(h, float)}
    col_estim = feuille.ncols - 1  # derniere colonne : "Estimates start after"

    lignes = []
    for r in range(1, feuille.nrows):
        pays = str(feuille.cell_value(r, 0)).strip()
        if pays not in PAYS_AFRIQUE:
            continue
        derniere_annee_reelle = feuille.cell_value(r, col_estim)
        for c, annee in colonnes_annees.items():
            v = feuille.cell_value(r, c)
            valeur = v if isinstance(v, float) else None
            projection = (
                isinstance(derniere_annee_reelle, float) and annee > derniere_annee_reelle
            )
            lignes.append(
                {"pays": pays, "iso3": PAYS_AFRIQUE[pays], "annee": annee,
                 nom: valeur, f"{nom}_projection": projection}
            )
    return pd.DataFrame(lignes)


if __name__ == "__main__":
    chemin, nom = sys.argv[1], sys.argv[2]
    df = lire(chemin, nom)
    sortie = Path("data/processed")
    sortie.mkdir(parents=True, exist_ok=True)
    df.to_csv(sortie / f"fmi_{nom}.csv", index=False)

    print(f"{df['pays'].nunique()} pays, {len(df)} lignes -> {sortie / f'fmi_{nom}.csv'}")
    obs = df[(df.annee.between(2000, 2025)) & df[nom].notna()]
    couv = obs.groupby("iso3").size().sort_values()
    print("Pays avec donnees incompletes sur 2000-2025 (26 annees possibles) :")
    print(couv[couv < 26].to_string())
    print("\nCEMAC, 2023-2025 :")
    print(df[df.iso3.isin(CEMAC) & df.annee.between(2023, 2025)]
          .pivot(index="pays", columns="annee", values=nom).round(1).to_string())
