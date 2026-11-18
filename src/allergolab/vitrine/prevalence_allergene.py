"""Outil : le pourcentage de patients sensibilisés à un allergène, parmi ceux qui ont été testés.

Pourquoi : une case vide veut dire « non mesuré sur cette puce », pas « négatif ».
Diviser par tous les patients avantagerait les allergènes mesurés sur plus de puces.
Ici, le dénominateur est toujours le nombre de patients réellement testés.
Le calcul est celui de analyses.prevalence : son résultat est noté tel quel, et c'est lui que l'interface affiche.
"""


from allergolab.vitrine import analyses, commun


def prevalence_allergene(allergene: str, puce: str | None = None, seuil: float | None = None) -> dict:
    """Pourcentage de patients sensibilisés à un allergène (dosage >= seuil), parmi les patients testés.
    Les cases vides (non testé) et les valeurs négatives (mesure invalide) sont exclues du dénominateur.

    Args:
        allergene: le nom exact de la colonne de dosage, par exemple "Ara_h_2".
        puce: "ALEX", "ISAC_V1" ou "ISAC_V2" pour se limiter à une puce ; None pour toutes.
        seuil: valeur à partir de laquelle un dosage compte comme positif ; None pour le seuil de l'équipe (0,3).
    """
    r = analyses.noter(analyses.prevalence(allergene, puce=puce, seuil=seuil))
    l = r["ligne"]
    resultat = {
        "allergene": allergene,
        "puce": r["parametres"]["puce"],
        "seuil": r["parametres"]["seuil"],
        "patients_testes": l["patients_testes"],
        "patients_positifs": l["patients_positifs"],
        "pourcentage_parmi_testes": l["pourcentage"],
        "intervalle_confiance_95": l["intervalle_confiance_95"],
        "non_testes_exclus": l["non_testes_exclus"],
        "mesures_invalides_exclues": l["mesures_invalides_exclues"],
        "puces_qui_le_mesurent": r["puces_qui_le_mesurent"],
    }
    if l["patients_testes"] < commun.MINIMUM_PATIENTS:
        resultat["avertissement"] = f"Moins de {commun.MINIMUM_PATIENTS} patients testés : pourcentage trop fragile."
    return resultat
