"""Outil : la répartition des codes d'une colonne clinique, sans compter les « non renseigné ».

Pourquoi : dans plusieurs colonnes, le code 9 veut dire « non renseigné » (dictionnaire
officiel). Le compter comme une réponse fausserait tous les pourcentages. Certaines
cellules ont plusieurs codes (« 1, 3 ») : un patient compte alors pour chacun d'eux.
"""


from allergolab.vitrine import commun


def repartition_clinique(colonne: str, puce: str | None = None) -> dict:
    """Répartition des codes d'une colonne clinique, en nombre et en pourcentage des patients renseignés.
    Le code 9 (non renseigné) et les cases vides sont comptés à part, jamais dans les pourcentages.
    Le sens de chaque code est dans le dictionnaire officiel, pas dans le tableau.

    Args:
        colonne: le nom exact d'une colonne clinique, par exemple "Skin_Symptoms" ou "French_Region".
        puce: "ALEX", "ISAC_V1" ou "ISAC_V2" pour se limiter à une puce ; None pour toutes.
    """
    commun.verifier_colonne(colonne, bloc="clinique")
    serie = commun.patients(puce)[colonne]
    vides = int(serie.isna().sum())
    texte = serie.dropna().astype(str).str.replace(".0", "", regex=False)
    non_renseignes = 0
    if colonne in commun.COLONNES_AVEC_CODE_9:
        non_renseignes = int((texte == commun.CODE_NON_RENSEIGNE).sum())
        texte = texte[texte != commun.CODE_NON_RENSEIGNE]
    renseignes = len(texte)
    comptes = commun.codes(texte).value_counts()
    if len(comptes) > 25:
        comptes = comptes.head(25)  # une colonne à beaucoup de valeurs : on garde les 25 plus fréquentes
    return {
        "colonne": colonne,
        "puce": puce or "toutes",
        "patients_renseignes": renseignes,
        "non_renseignes_code_9": non_renseignes,
        "cases_vides": vides,
        "codes": {code: {"patients": int(n), "pourcentage": commun.pourcentage(n, renseignes)} for code, n in comptes.items()},
        "plusieurs_codes_possibles": bool(texte.str.contains(",").any()),
    }
