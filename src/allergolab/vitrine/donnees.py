"""Chargement du tableau pour la page et l'onglet Explorer, avec les règles de lecture du kit d'origine.

Le fichier lu est celui du moteur (ALLERGOLAB_DONNEES, sinon donnees/ du projet).
Aucun recodage, aucun filtrage : les règles de l'équipe s'appliquent ensuite, dans commun.py.
"""

from pathlib import Path

import pandas as pd

from allergolab.configuration import Configuration

DICTIONNAIRE = Path(__file__).resolve().parent / "colonnes.csv"
NB_CLINIQUES = 15  # les quinze premières colonnes forment le bloc clinique
VIRGULE_OU_LETTRE = r",|[^\W\d_]"


def fichier_donnees():
    return Configuration.environnement().donnees


def charger(chemin=None):
    """Le tableau complet : « ; », UTF-8, seule une cellule vide est manquante, virgule décimale pour les dosages."""
    tableau = pd.read_csv(
        chemin or fichier_donnees(),
        sep=";",
        encoding="utf-8-sig",
        dtype=str,
        keep_default_na=False,
        na_values=[""],
    )
    for position, nom in enumerate(tableau.columns):
        cellules = tableau[nom]
        if position >= NB_CLINIQUES:
            tableau[nom] = pd.to_numeric(cellules.str.replace(",", ".", regex=False))
        elif not cellules.str.contains(VIRGULE_OU_LETTRE, regex=True, na=False).any():
            tableau[nom] = pd.to_numeric(cellules)
    return tableau


def colonnes(chemin=DICTIONNAIRE):
    """Le dictionnaire des colonnes : bloc, lecture, et une colonne puce_<type> par puce."""
    return pd.read_csv(
        chemin,
        encoding="utf-8",
        dtype={"colonne": str, "bloc": str, "lecture": str},
        true_values=["vrai"],
        false_values=["faux"],
    )
