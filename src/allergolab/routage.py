"""Reconnaissance volontairement étroite des demandes sans appel au modèle."""

import re

from .contrats import Plan
from .donnees import Abstention, Depot, normaliser


def garde_question(question: str) -> None:
    texte = normaliser(question)
    if re.search(r"\b(diagnosti\w*|prescri\w*|posologie|causal\w*|provoque\w*|guerir)\b", texte) or re.search(
        r"\b(quel|quelle|recommande\w*)\b.*\btraitement\b|\b(cause|causent|cause-t-il)\b", texte
    ):
        raise Abstention(
            "Ces données de cohorte ne permettent ni diagnostic individuel, ni prescription, "
            "ni conclusion causale ; reformuler en question descriptive ou en association.",
            "hors_perimetre",
        )


def plan_direct(question: str, depot: Depot) -> Plan | None:
    texte = normaliser(question).strip().rstrip(" ?.!;:").strip()
    support = r"(?:le tableau|la cohorte|cette cohorte|la base|ce jeu de donnees)"
    if re.fullmatch(
        r"(?:combien (?:de |d')?(?:lignes|observations|patients)"
        rf"(?: (?:compte|contient) {support}| dans {support}| au total| y a-t-il(?: dans {support})?)?"
        r"|quel est l'effectif|nombre (?:de lignes|de patients|d'observations))",
        texte,
    ):
        # Compter des patients exige de vérifier l'unicité des identifiants.
        if "patient" in texte:
            tableau = depot._tableau
            if (
                "Patient_ID" not in tableau
                or tableau["Patient_ID"].isna().any()
                or not tableau["Patient_ID"].is_unique
            ):
                raise Abstention(
                    "Le nombre de patients distincts ne peut pas être assimilé au nombre de lignes.",
                    "unite_observation",
                )
        return Plan(operation="compter")
    if texte in {
        "quelles variables presentent le plus de donnees manquantes",
        "donnees manquantes",
        "valeurs manquantes",
    }:
        return Plan(operation="manquants")
    if texte in {"quel est l'age moyen", "quel est l'age moyen des patients", "age moyen"}:
        return Plan(operation="decrire", colonne="Age")
    if texte in {"quel est l'age median", "quel est l'age median des patients", "age median"}:
        return Plan(operation="decrire", colonne="Age", statistique="mediane")
    correspondance = re.fullmatch(
        r"(?:quelle est la |quel est le |calcule la |calcule le )?"
        r"(moyenne|mediane|minimum|maximum|age moyen|age median)"
        r"(?: (?:de |d'|du |des |la |le |l'|patients))*(.*)",
        texte,
    )
    if correspondance:
        statistique, colonne = correspondance.groups()
        if statistique.startswith("age"):
            if colonne.strip():
                return None
            colonne = "Age"
            statistique = "mediane" if "median" in statistique else "moyenne"
        else:
            colonne = colonne.strip(" `\"'")
            if colonne in {"age", "ages"}:
                colonne = "Age"
        if not colonne:
            return None
        try:
            colonne = depot.resoudre(colonne)
        except Abstention:
            return None
        return Plan(operation="decrire", colonne=colonne, statistique=statistique)
    return None


def verifier_seuil_question(question: str, plan: Plan):
    """Empêcher l'ajout d'un seuil clinique absent de la demande explicite."""
    if plan.operation != "proportion":
        return
    nombres = re.findall(r"(?<![\w.])-?\d+(?:[.,]\d+)?(?![\w.])", question)
    if not any(float(n.replace(",", ".")) == plan.seuil for n in nombres):
        raise Abstention(
            "Le seuil n'est pas explicite dans la question ; préciser la valeur, le comparateur "
            "et la puce concernée.",
            "seuil_non_precise",
        )
