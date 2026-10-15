"""Prepare les deux tables du tableau de bord Power BI (schema en etoile).

Usage (depuis la racine du projet) : python scripts/preparer_dashboard.py
Entrees : data/processed/panel.csv, data/raw/notes_agences.csv
Sorties : data/dashboard/dim_pays.csv (1 ligne par pays)
          data/dashboard/faits_indicateurs.csv (1 ligne par pays et par annee)
"""
from pathlib import Path

import pandas as pd

NOMS_FR = {
    "DZA": "Algérie", "AGO": "Angola", "BEN": "Bénin", "BWA": "Botswana",
    "BFA": "Burkina Faso", "BDI": "Burundi", "CPV": "Cabo Verde", "CMR": "Cameroun",
    "CAF": "Centrafrique", "TCD": "Tchad", "COM": "Comores", "COD": "RD Congo",
    "COG": "Congo-Brazzaville", "CIV": "Côte d'Ivoire", "DJI": "Djibouti", "EGY": "Égypte",
    "GNQ": "Guinée équatoriale", "ERI": "Érythrée", "SWZ": "Eswatini", "ETH": "Éthiopie",
    "GAB": "Gabon", "GMB": "Gambie", "GHA": "Ghana", "GIN": "Guinée",
    "GNB": "Guinée-Bissau", "KEN": "Kenya", "LSO": "Lesotho", "LBR": "Libéria",
    "LBY": "Libye", "MDG": "Madagascar", "MWI": "Malawi", "MLI": "Mali",
    "MRT": "Mauritanie", "MUS": "Maurice", "MAR": "Maroc", "MOZ": "Mozambique",
    "NAM": "Namibie", "NER": "Niger", "NGA": "Nigéria", "RWA": "Rwanda",
    "STP": "Sao Tomé-et-Principe", "SEN": "Sénégal", "SYC": "Seychelles",
    "SLE": "Sierra Leone", "SOM": "Somalie", "ZAF": "Afrique du Sud",
    "SSD": "Soudan du Sud", "SDN": "Soudan", "TZA": "Tanzanie", "TGO": "Togo",
    "TUN": "Tunisie", "UGA": "Ouganda", "ZMB": "Zambie", "ZWE": "Zimbabwe",
}
CEMAC = {"CMR", "GAB", "COG", "TCD", "GNQ", "CAF"}
UEMOA = {"BEN", "BFA", "CIV", "GNB", "MLI", "NER", "SEN", "TGO"}


def groupe_note(n):
    """Trois groupes pour le tableau de bord et le modele (equivalent S&P)."""
    if pd.isna(n):
        return None
    if n <= 5:
        return "1 - CCC+ et moins"
    if n <= 8:
        return "2 - B- a B+"
    return "3 - BB- et plus"


def zone(iso3):
    return "CEMAC" if iso3 in CEMAC else "UEMOA" if iso3 in UEMOA else "Autres pays"


if __name__ == "__main__":
    panel = pd.read_csv("data/processed/panel.csv")
    notes = pd.read_csv("data/raw/notes_agences.csv")

    dim = panel[["iso3"]].drop_duplicates().reset_index(drop=True)
    dim["pays"] = dim["iso3"].map(NOMS_FR)
    dim["zone"] = dim["iso3"].map(zone)

    for agence, prefixe in [("S&P", "sp"), ("Fitch", "fitch"), ("Moody's", "moodys")]:
        n = notes[notes["agence"] == agence][["iso3", "note", "note_num", "perspective", "confiance"]]
        n.columns = ["iso3", f"{prefixe}_note", f"{prefixe}_note_num",
                     f"{prefixe}_perspective", f"{prefixe}_confiance"]
        dim = dim.merge(n, on="iso3", how="left", validate="one_to_one")
    dim["groupe_note"] = dim["sp_note_num"].map(groupe_note)

    faits = panel[panel["annee"].between(2000, 2031)][
        ["iso3", "annee", "dette", "solde", "inflation", "croissance", "reserves_mois", "projection"]
    ]

    sortie = Path("data/dashboard")
    sortie.mkdir(parents=True, exist_ok=True)
    dim.to_csv(sortie / "dim_pays.csv", index=False)
    faits.to_csv(sortie / "faits_indicateurs.csv", index=False)

    print(f"dim_pays : {len(dim)} pays | faits_indicateurs : {len(faits)} lignes")
    print("\nNoms francais manquants :", dim[dim.pays.isna()].iso3.tolist() or "aucun")
    print("\nPays par zone :")
    print(dim["zone"].value_counts().to_string())
    print("\nPays notes par S&P, par groupe :")
    print(dim["groupe_note"].value_counts(dropna=False).sort_index().to_string())
    print("\nCEMAC :")
    print(dim[dim.zone == "CEMAC"][["pays", "sp_note", "fitch_note", "moodys_note", "groupe_note"]].to_string(index=False))
