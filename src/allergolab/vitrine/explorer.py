"""L'onglet « Explorer » de l'interface : des vues des données calculées par les outils de l'équipe.

Aucun appel au modèle, aucun jeton : ce sont les mêmes outils que ceux de l'agent,
appelés directement. Chaque vue rend des valeurs simples (nombres, courtes listes),
jamais le tableau : les mêmes règles de lecture s'appliquent partout (commun.py).
"""

from functools import lru_cache

from allergolab.vitrine import analyses, commun, nomenclature
from allergolab.vitrine.prevalence_allergene import prevalence_allergene
from allergolab.vitrine.prevalence_par_groupe import prevalence_par_groupe
from allergolab.vitrine.repartition_clinique import repartition_clinique


def puce_valide(puce):
    """Une puce de la liste, ou None pour toutes ; toute autre valeur est refusée."""
    if puce in (None, "", "toutes"):
        return None
    if puce not in commun.PUCES:
        raise ValueError(f"Puce inconnue : {puce}.")
    return puce


def resume():
    """Les chiffres de l'en-tête : patients, patients par puce, allergènes, seuil."""
    puces = repartition_clinique(colonne="Chip_Type")
    dosage = commun.dictionnaire()["bloc"] == "dosage"
    return {
        "patients": len(commun.tableau()),
        "par_puce": {code: v["patients"] for code, v in puces["codes"].items()},
        "allergenes": int(dosage.sum()),
        "allergenes_par_puce": {p: int(commun.dictionnaire().loc[dosage, f"puce_{p}"].sum()) for p in commun.PUCES},
        "seuil": commun.SEUIL_POSITIF,
        "minimum_patients": commun.MINIMUM_PATIENTS,
    }


@lru_cache(maxsize=8)
def classement(puce=None):
    """Tous les allergènes testés chez au moins 30 patients, du plus fréquent au moins fréquent."""
    # Le même calcul que l'outil classer_allergenes de l'agent : un seul classement, partout.
    resultat = analyses.classement(nombre=None, puce=puce_valide(puce))
    return [
        {"code": l["code"], "testes": l["patients_testes"], "positifs": l["patients_positifs"], "pourcentage": l["pourcentage"], **nomenclature.decrire(l["code"])}
        for l in resultat["lignes"]
    ]


def fiche_allergene(code):
    """Tout ce qu'il faut pour la fiche d'un allergène : ensemble, par puce, et sa nomenclature."""
    ensemble = prevalence_allergene(allergene=code)
    par_puce = [ligne for ligne in prevalence_par_groupe(allergene=code, groupe="Chip_Type") if ligne["patients_testes"] > 0]
    return {"code": code, "ensemble": ensemble, "par_puce": par_puce, **nomenclature.decrire(code)}


def clinique(colonne, puce=None):
    """La répartition des codes d'une colonne clinique (code 9 et cases vides comptés à part)."""
    return repartition_clinique(colonne=colonne, puce=puce_valide(puce))


def noms():
    """Pour chaque colonne de dosage : ce que la nomenclature de l'équipe en dit."""
    d = commun.dictionnaire()
    return {code: nomenclature.decrire(code) for code in d.index[d["bloc"] == "dosage"]}
