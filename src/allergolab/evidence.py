"""Contrôles indépendants des effectifs, dénominateurs et valeurs publiées."""

import math

from scipy import stats

from .contrats import Preuve, Reponse
from .donnees import Abstention, Depot


def verifier(depot: Depot, reponse: Reponse, preuve: Preuve) -> None:
    def exiger(condition, message):
        if not condition:
            raise Abstention(f"EVIDENCE ne valide pas le résultat : {message}.", "verification_echouee")

    selection = depot.selectionner(preuve.plan.filtres)
    exiger(preuve.empreinte == depot.empreinte, "version des données incohérente")
    exiger(preuve.population == depot.nombre and preuve.selection == len(selection), "population incohérente")
    exiger(0 <= preuve.exploitables <= preuve.selection <= preuve.population, "effectifs incohérents")
    exiger(preuve.exploitables + preuve.manquants == preuve.selection, "dénominateur incohérent")

    def proche(a, b):
        exiger(
            isinstance(a, (int, float))
            and math.isfinite(a)
            and math.isclose(a, b, rel_tol=1e-10, abs_tol=1e-10),
            "valeur publiée incohérente",
        )

    plan, details = preuve.plan, preuve.details
    noms = [depot.resoudre(n) for n in (plan.colonne, plan.seconde_colonne, plan.groupe) if n]
    attendus = len(selection[noms].dropna()) if noms and plan.operation != "manquants" else len(selection)
    exiger(preuve.exploitables == attendus, "effectif exploitable incohérent")
    if plan.operation == "compter":
        proche(reponse.valeur, len(selection))
    elif plan.operation == "proportion":
        serie = selection[noms[0]].dropna()
        numerateur = int(getattr(serie, plan.comparateur)(plan.seuil).sum())
        exiger(
            details["denominateur"] == len(serie) and details["numerateur"] == numerateur,
            "numérateur incohérent",
        )
        proche(reponse.valeur, 100 * numerateur / len(serie))
        proche(details["pourcentage"], reponse.valeur)
        bas, haut = details["ic95_wilson"]
        exiger(
            -1e-10 <= bas <= reponse.valeur + 1e-10 and reponse.valeur <= haut + 1e-10 <= 100 + 1e-9,
            "intervalle de confiance incohérent",
        )
    elif plan.operation == "decrire":
        serie = selection[noms[0]].dropna()
        fonction = {"moyenne": "mean", "mediane": "median", "minimum": "min", "maximum": "max"}[
            plan.statistique
        ]
        proche(reponse.valeur, float(getattr(serie, fonction)()))
        for nom, fonction in (
            ("moyenne", "mean"),
            ("mediane", "median"),
            ("minimum", "min"),
            ("maximum", "max"),
        ):
            proche(details[nom], float(getattr(serie, fonction)()))
        if len(serie) > 1:
            proche(details["ecart_type"], float(serie.std(ddof=1)))
        else:
            exiger(details["ecart_type"] is None, "écart type indéfini")
    elif plan.operation == "frequences":
        effectifs = selection[noms[0]].dropna().value_counts()
        exiger(
            sum(x["effectif"] for x in details["modalites"]) + details["autres_effectif"]
            == preuve.exploitables,
            "fréquences incomplètes",
        )
        exiger(
            [x["effectif"] for x in details["modalites"]] == [int(x) for x in effectifs.iloc[: plan.limite]],
            "fréquences incorrectes",
        )
        exiger(
            [x["valeur"] for x in details["modalites"]]
            == [str(x) for x in effectifs.iloc[: plan.limite].index],
            "modalités incorrectes",
        )
        for ligne in details["modalites"]:
            proche(ligne["pourcentage"], 100 * ligne["effectif"] / preuve.exploitables)
    elif plan.operation == "manquants":
        for ligne in details["colonnes"]:
            exiger(
                ligne["manquants"] == int(selection[ligne["colonne"]].isna().sum()), "absences incohérentes"
            )
    elif plan.operation == "comparer":
        exiger(
            sum(g["effectif"] for g in details["groupes"]) == preuve.exploitables,
            "effectifs de groupes incohérents",
        )
        proche(reponse.valeur, details["p_valeur"])
        exiger(0 <= reponse.valeur <= 1, "p-valeur hors domaine")
        groupes = list(selection[noms].dropna().groupby(noms[1], sort=True, observed=True))
        exiger(len(groupes) == 2, "nombre de groupes incorrect")
        for (nom, groupe), publie in zip(groupes, details["groupes"], strict=True):
            exiger(publie["effectif"] == len(groupe) and publie["valeur"] == str(nom), "groupe incorrect")
            proche(publie["mediane"], float(groupe[noms[0]].median()))
        test = stats.mannwhitneyu(
            groupes[0][1][noms[0]], groupes[1][1][noms[0]], alternative="two-sided", method="asymptotic"
        )
        proche(details["statistique_u"], float(test.statistic))
        proche(reponse.valeur, float(test.pvalue))
    elif plan.operation == "correler":
        proche(reponse.valeur, details["rho"])
        exiger(-1 <= reponse.valeur <= 1, "corrélation hors domaine")
        paires = selection[noms].dropna()
        test = stats.spearmanr(paires[noms[0]], paires[noms[1]])
        proche(reponse.valeur, float(test.statistic))
        if preuve.exploitables > 500:
            proche(details["p_valeur"], float(test.pvalue))
        else:
            exiger(details["p_valeur"] is None, "p-valeur non justifiée pour ce petit échantillon")
    # Interdire NaN/Infinity même au sein des détails, pas seulement dans la valeur principale.
    import json

    try:
        json.dumps(preuve.model_dump(mode="json"), allow_nan=False)
    except ValueError:
        raise Abstention("EVIDENCE détecte un résultat numérique indéfini.", "verification_echouee") from None
    preuve.controles = [
        "version des données",
        "population et sélection",
        "dénominateur et absences",
        "cohérence de la valeur publiée",
        "résultats numériques finis",
    ]
