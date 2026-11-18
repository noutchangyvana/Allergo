"""Les résultats structurés : un seul calcul, validé, gardé tel quel pour l'agent, l'interface et l'onglet Explorer.

Pourquoi : l'agent réécrit ses résultats en phrases, et une phrase ne se relit pas de
façon fiable. Ici, chaque outil dépose son résultat chiffré, validé, dans un journal.
L'interface affiche ce résultat-là, jamais des chiffres retrouvés dans un texte.

Deux précisions : « proportion » est la valeur exacte (positifs / testés), qui sert au tri ;
« pourcentage » est l'arrondi d'affichage (une décimale), le même pour le texte, le tableau
et le graphique. Ce fichier n'est pas un outil. VERSION change si la forme d'un résultat change.
"""

import hashlib
import json
import math
import threading
from functools import lru_cache
from pathlib import Path

from allergolab.vitrine import commun, nomenclature
from allergolab.vitrine.donnees import fichier_donnees

VERSION = "2"
ARRONDI = 1  # décimales des pourcentages affichés
_journal = threading.local()  # un journal par fil d'exécution : une question n'y voit pas l'onglet Explorer

LIMITE_SEUIL = "Le seuil de positivité est un choix de l'équipe (seuil usuel des fabricants), pas une validation clinique."
LIMITE_PUCES = ("Toutes puces : les positivités de puces aux unités différentes (ISU-E pour ISAC, kUA/L pour ALEX) sont "
                "regroupées avec un même seuil ; les valeurs brutes, elles, ne sont jamais mélangées.")
LIMITE_DENOMINATEURS = "Les allergènes ne sont pas testés chez les mêmes patients : le dénominateur change d'une ligne à l'autre."


def vider():
    """À appeler avant chaque question : le journal repart vide."""
    _journal.resultats = []


def noter(resultat):
    """Garde un résultat calculé par un outil ; le rend tel quel."""
    if not hasattr(_journal, "resultats"):
        vider()
    _journal.resultats.append(resultat)
    return resultat


def notes():
    return list(getattr(_journal, "resultats", []))


def source():
    """D'où viennent les chiffres : l'empreinte SHA-256 du fichier de données lu et la version du calcul."""
    return {"empreinte_donnees": empreinte_donnees(), "version_calcul": VERSION}


@lru_cache(maxsize=1)
def empreinte_donnees():
    try:
        return hashlib.sha256(Path(fichier_donnees()).read_bytes()).hexdigest()
    except OSError:
        return None


def mesurer(code, puce, seuil):
    """Les effectifs d'un allergène, selon les règles de commun.py : la base de tous les résultats."""
    commun.verifier_colonne(code, bloc="dosage")
    valides, non_testes, invalides = commun.lire_dosage(commun.patients(puce)[code])
    positifs, testes = int((valides >= seuil).sum()), len(valides)
    fiche = nomenclature.decrire(code)
    return {
        "code": code, "libelle": fiche.get("source"), "categorie": fiche.get("categorie"),
        "patients_positifs": positifs, "patients_testes": testes,
        "proportion": positifs / testes if testes else None,
        "pourcentage": commun.pourcentage(positifs, testes),
        "intervalle_confiance_95": commun.intervalle_wilson(positifs, testes),
        "non_testes_exclus": non_testes, "mesures_invalides_exclues": invalides,
    }


def parametres(puce, seuil, **autres):
    return {"puce": puce or "toutes", "seuil": seuil, "comparateur": ">=", "minimum_patients_testes": commun.MINIMUM_PATIENTS, **autres}


def classement(nombre=None, puce=None, seuil=None):
    """Les allergènes classés par proportion de sensibilisés parmi les testés. nombre=None : tous les éligibles."""
    seuil = commun.SEUIL_POSITIF if seuil is None else float(seuil)
    commun.patients(puce)  # refuse une puce inconnue
    d = commun.dictionnaire()
    eligibles = []
    for code in d.index[d["bloc"] == "dosage"]:
        if puce and not d.loc[code, f"puce_{puce}"]:
            continue  # cette puce ne mesure pas cet allergène
        ligne = mesurer(code, puce, seuil)
        if ligne["patients_testes"] >= commun.MINIMUM_PATIENTS:
            eligibles.append(ligne)
    eligibles.sort(key=lambda l: (-l["proportion"], l["code"]))  # tri sur la valeur exacte ; à égalité, par code
    demande = None if nombre is None else int(nombre)
    retenus = eligibles if demande is None else eligibles[: max(1, min(demande, 20))]
    limites = [LIMITE_SEUIL]
    if not puce:
        limites.append(LIMITE_PUCES)
    if len({l["patients_testes"] for l in retenus}) > 1:
        limites.append(LIMITE_DENOMINATEURS)
    if demande is not None and len(retenus) < min(demande, 20):
        limites.append(f"Seuls {len(retenus)} allergènes sont testés chez au moins {commun.MINIMUM_PATIENTS} patients"
                       f"{'' if not puce else ' sur cette puce'} : les autres sont écartés, leur pourcentage serait trop fragile.")
    if demande is not None and demande > 20:
        limites.append("Le classement s'arrête à 20 allergènes.")
    resultat = {
        "type": "classement_allergenes", "version": VERSION,
        "parametres": parametres(puce, seuil, nombre_demande=demande),
        "lignes": [{"rang": i + 1, **ligne} for i, ligne in enumerate(retenus)],
        "nombre_retourne": len(retenus), "nombre_eligibles": len(eligibles),
        "methode": {"indicateur": "proportion de patients sensibilisés parmi les dosages valides",
                    "denominateur": "patients effectivement testés pour chaque allergène (cases vides et valeurs négatives exclues)",
                    "tri": "proportion exacte décroissante, puis code", "arrondi_affichage": ARRONDI},
        "source": source(), "limites": limites,
    }
    return valider(resultat)


def prevalence(allergene, puce=None, seuil=None):
    """La prévalence d'un allergène parmi les testés, au même format que les lignes d'un classement."""
    seuil = commun.SEUIL_POSITIF if seuil is None else float(seuil)
    ligne = mesurer(allergene, puce, seuil)
    limites = [LIMITE_SEUIL] + ([] if puce else [LIMITE_PUCES])
    if ligne["patients_testes"] < commun.MINIMUM_PATIENTS:
        limites.append(f"Moins de {commun.MINIMUM_PATIENTS} patients testés : pourcentage trop fragile pour conclure.")
    return valider({
        "type": "prevalence_allergene", "version": VERSION, "parametres": parametres(puce, seuil),
        "ligne": ligne, "puces_qui_le_mesurent": commun.puces_qui_mesurent(allergene),
        "methode": {"indicateur": "proportion de patients sensibilisés parmi les dosages valides",
                    "denominateur": "patients effectivement testés pour cet allergène (cases vides et valeurs négatives exclues)",
                    "arrondi_affichage": ARRONDI},
        "source": source(), "limites": limites,
    })


def valider(r):
    """Vérifie un résultat avant de le laisser sortir ; lève une erreur claire sinon."""
    def exiger(condition, message):
        if not condition:
            raise ValueError(f"Résultat invalide : {message}.")
    d, p = commun.dictionnaire(), r["parametres"]
    exiger(r["version"] == VERSION and r["type"] in ("classement_allergenes", "prevalence_allergene"), "type ou version inattendus")
    exiger(p["comparateur"] == ">=" and isinstance(p["seuil"], (int, float)), "seuil ou comparateur non explicites")
    lignes = r["lignes"] if r["type"] == "classement_allergenes" else [r["ligne"]]
    for i, l in enumerate(lignes):
        exiger(l["code"] in d.index and d.loc[l["code"], "bloc"] == "dosage", f"{l['code']} n'est pas une colonne de dosage")
        if p["puce"] != "toutes" and r["type"] == "classement_allergenes":
            exiger(bool(d.loc[l["code"], f"puce_{p['puce']}"]), f"{l['code']} n'est pas mesuré sur {p['puce']}")
        exiger(0 <= l["patients_positifs"] <= l["patients_testes"], f"effectifs impossibles pour {l['code']}")
        if l["patients_testes"]:
            exiger(math.isclose(l["proportion"], l["patients_positifs"] / l["patients_testes"]), f"proportion fausse pour {l['code']}")
            exiger(l["pourcentage"] == round(100 * l["proportion"], ARRONDI), f"arrondi faux pour {l['code']}")
        else:
            exiger(l["proportion"] is None and l["pourcentage"] is None, f"pourcentage sans dénominateur pour {l['code']}")
    if r["type"] == "classement_allergenes":
        exiger(r["nombre_retourne"] == len(lignes) <= r["nombre_eligibles"], "nombre de lignes incohérent")
        for i, l in enumerate(lignes):
            exiger(l["rang"] == i + 1, "rangs non consécutifs")
            exiger(l["patients_testes"] >= p["minimum_patients_testes"], f"{l['code']} a trop peu de testés")
            exiger(i == 0 or (-lignes[i - 1]["proportion"], lignes[i - 1]["code"]) < (-l["proportion"], l["code"]), "ordre non déterministe")
    try:
        json.dumps(r, allow_nan=False)  # aucune valeur NaN ou infinie ne sort
    except ValueError:
        exiger(False, "valeur non finie")
    return r


def correspondant(reponse):
    """Le résultat noté qui correspond à la réponse finale de l'agent, ou None (erreur, abstention, rien de noté).

    Aucun chiffre n'est lu dans le texte : on vérifie seulement que la réponse parle de ce résultat
    (même valeur pour une prévalence, même allergène en tête pour un classement).
    """
    if not reponse or reponse.get("statut") != "reponse":
        return None
    valeur = reponse.get("valeur")
    for r in reversed(notes()):  # le plus récent d'abord : c'est celui que l'agent a utilisé en dernier
        if r["type"] == "prevalence_allergene" and isinstance(valeur, (int, float)) and r["ligne"]["pourcentage"] is not None:
            if abs(valeur - r["ligne"]["pourcentage"]) <= 0.05:
                return r
        if r["type"] == "classement_allergenes" and isinstance(valeur, str) and r["lignes"]:
            premier = r["lignes"][0]
            if any(nom and nom in valeur for nom in (premier["code"], premier["code"].replace("_", " "), premier["libelle"])):
                return r
    return None
