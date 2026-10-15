"""Telecharge les reserves de change (Banque mondiale) et assemble le panel final.

Usage (depuis la racine du projet) : python scripts/construire_panel.py
Entrees  : data/processed/fmi_{dette,solde,inflation,croissance}.csv
Sorties  : data/raw/bm_reserves.csv (donnees brutes), data/processed/panel.csv
"""
import time
from pathlib import Path

import pandas as pd
import requests

INDICATEURS_FMI = ["dette", "solde", "inflation", "croissance"]
CEMAC = ["CMR", "GAB", "COG", "TCD", "GNQ", "CAF"]
HEADERS = {"User-Agent": "Mozilla/5.0"}
BM_INDICATEUR = "FI.RES.TOTL.MO"  # reserves totales en mois d'importations


def telecharger_bm(codes_iso3, debut=2000, fin=2025):
    url = f"https://api.worldbank.org/v2/country/{';'.join(codes_iso3)}/indicator/{BM_INDICATEUR}"
    lignes, page, pages = [], 1, 1
    while page <= pages:
        params = {"format": "json", "per_page": 5000, "date": f"{debut}:{fin}", "page": page}
        for essai in range(3):
            try:
                r = requests.get(url, params=params, headers=HEADERS, timeout=60)
                r.raise_for_status()
                break
            except requests.RequestException as e:
                print(f"  essai {essai + 1}/3 echoue : {type(e).__name__}")
                time.sleep(3)
        else:
            raise SystemExit("Banque mondiale injoignable apres 3 essais.")
        meta, donnees = r.json()[0], r.json()[1]
        pages = meta["pages"]
        for d in donnees or []:
            lignes.append({"iso3": d["countryiso3code"], "annee": int(d["date"]),
                           "reserves_mois": d["value"]})
        page += 1
    return pd.DataFrame(lignes)


def charger_fmi():
    panel = None
    for nom in INDICATEURS_FMI:
        df = pd.read_csv(f"data/processed/fmi_{nom}.csv")
        if panel is None:
            panel = df[["pays", "iso3", "annee", nom, f"{nom}_projection"]]
        else:
            panel = panel.merge(df[["iso3", "annee", nom, f"{nom}_projection"]],
                                on=["iso3", "annee"], how="outer", validate="one_to_one")
    flags = [f"{n}_projection" for n in INDICATEURS_FMI]
    panel["projection"] = panel[flags].any(axis=1)  # vrai si au moins un indicateur est projete
    return panel.drop(columns=flags)


if __name__ == "__main__":
    fmi = charger_fmi()
    print(f"FMI : {fmi['iso3'].nunique()} pays, {len(fmi)} lignes")

    print("Telechargement Banque mondiale...")
    bm = telecharger_bm(sorted(fmi["iso3"].unique()))
    Path("data/raw").mkdir(parents=True, exist_ok=True)
    bm.to_csv("data/raw/bm_reserves.csv", index=False)
    print(f"BM : {bm['reserves_mois'].notna().sum()} valeurs non vides sur {len(bm)} lignes")

    panel = fmi.merge(bm, on=["iso3", "annee"], how="left", validate="one_to_one")
    panel["cemac"] = panel["iso3"].isin(CEMAC)
    panel = panel.sort_values(["iso3", "annee"]).reset_index(drop=True)
    panel.to_csv("data/processed/panel.csv", index=False)
    print(f"\nPanel : {len(panel)} lignes -> data/processed/panel.csv")

    hist = panel[(panel.annee.between(2000, 2025)) & (~panel.projection)]
    cols = INDICATEURS_FMI + ["reserves_mois"]
    print("\nPart de valeurs manquantes, 2000-2025 (hors projections) :")
    print((hist[cols].isna().mean() * 100).round(1).to_string())
    print("\nReserves (mois d'importations), nombre d'annees renseignees, CEMAC :")
    print(hist[hist.cemac].groupby("pays")["reserves_mois"].count().to_string())
