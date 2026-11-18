"""Méthodes prédéfinies : aucune génération de Python ou de SQL par le modèle."""

import math

from scipy import stats

from .contrats import Plan, Preuve, Reponse
from .donnees import Abstention, Depot


def wilson(succes: int, total: int) -> list[float]:
    z = 1.959963984540054
    p = succes / total
    denominateur = 1 + z * z / total
    centre = (p + z * z / (2 * total)) / denominateur
    marge = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / denominateur
    return [max(0.0, 100 * (centre - marge)), min(100.0, 100 * (centre + marge))]


def executer(depot: Depot, plan: Plan) -> tuple[Reponse, Preuve]:
    if plan.operation == "abstention":
        raise Abstention(plan.motif, "question_non_resolue")
    tableau = depot.selectionner(plan.filtres)
    noms = [depot.verifier_colonne(n) for n in (plan.colonne, plan.seconde_colonne, plan.groupe) if n]
    limites = ["Résultat descriptif ou exploratoire limité à cette cohorte ; aucune causalité démontrée."]
    filtres_dosage = [
        f for f in plan.filtres if depot.catalogue[depot.resoudre(f.colonne)]["bloc"] == "dosage"
    ]
    dose_analyse = plan.operation not in {"compter", "manquants"} and any(
        depot.catalogue[nom]["bloc"] == "dosage" for nom in noms
    )
    if filtres_dosage or dose_analyse:
        # Vérifier la puce AVANT les filtres de dosage : leur résultat ne doit pas
        # masquer un mélange d'unités en excluant accidentellement une autre puce.
        support = depot.selectionner([f for f in plan.filtres if f not in filtres_dosage])
        if (
            "Chip_Type" not in support
            or support["Chip_Type"].isna().any()
            or support["Chip_Type"].nunique() != 1
        ):
            raise Abstention(
                "Les dosages demandent une sélection explicite sur un seul Chip_Type ; "
                "les unités et disponibilités peuvent différer selon la puce.",
                "puce_ambigue",
            )
    if plan.operation in {"comparer", "correler"} and "Patient_ID" in tableau:
        identifiants = tableau["Patient_ID"]
        if identifiants.isna().any() or not identifiants.is_unique:
            raise Abstention(
                "Des identifiants sont absents ou répétés ; vérifier l'indépendance des observations avant le test.",
                "observations_non_independantes",
            )
    if plan.operation == "compter":
        details = {"effectif": len(tableau)}
        n, methode = len(tableau), "Comptage des lignes après application des filtres"
        reponse = Reponse(
            statut="reponse", valeur=n, justification=f"La sélection contient {n} observations."
        )
    elif plan.operation == "manquants":
        colonnes = noms or [c for c in tableau if not depot.catalogue[c]["protegee"]]
        if not colonnes:
            raise Abstention("Aucune colonne analysable dans cette sélection.")
        lignes = [
            {
                "colonne": c,
                "manquants": int(tableau[c].isna().sum()),
                "total": len(tableau),
                "pourcentage": float(100 * tableau[c].isna().mean()) if len(tableau) else None,
            }
            for c in colonnes
        ]
        lignes.sort(key=lambda ligne: (-ligne["manquants"], ligne["colonne"]))
        details = {"colonnes": lignes[: plan.limite], "colonnes_total": len(lignes)}
        n, methode = len(tableau), "Cellules vides par colonne ; aucune imputation"
        if "Chip_Type" in tableau and tableau["Chip_Type"].nunique() > 1:
            limites.append(
                "Une absence de dosage peut être structurelle selon la puce ; ce n'est pas un résultat négatif."
            )
        reponse = Reponse(
            statut="reponse",
            valeur=" ; ".join(
                f"{x['colonne']} : {x['manquants']}/{x['total']} absences" for x in lignes[: plan.limite]
            ),
            justification="Les absences correspondent aux cellules vides, sans recodage des valeurs textuelles.",
        )
    else:
        if not len(tableau):
            raise Abstention(
                "Aucune observation ne correspond aux filtres ; élargir la sélection.", "selection_vide"
            )
        nom = noms[0]
        serie = tableau[nom].dropna()
        n = len(serie)
        if not n:
            raise Abstention(
                "La variable ne contient aucune valeur exploitable dans cette sélection.", "donnees_absentes"
            )
        if plan.operation in {"decrire", "proportion", "comparer", "correler"}:
            depot.verifier_colonne(nom, quantitative=True)
        if plan.operation == "decrire":
            details = {
                "moyenne": float(serie.mean()),
                "mediane": float(serie.median()),
                "minimum": float(serie.min()),
                "maximum": float(serie.max()),
                "ecart_type": float(serie.std(ddof=1)) if n > 1 else None,
            }
            methode = "Statistiques descriptives sur les valeurs non manquantes"
            reponse = Reponse(
                statut="reponse",
                valeur=details[plan.statistique],
                justification=f"{plan.statistique.capitalize()} de {nom}, calculée sur {n} observations exploitables.",
            )
        elif plan.operation == "frequences":
            frequences = serie.value_counts(dropna=True)
            lignes = [
                {"valeur": str(k), "effectif": int(v), "pourcentage": 100 * int(v) / n}
                for k, v in frequences.iloc[: plan.limite].items()
            ]
            details = {
                "modalites": lignes,
                "modalites_total": len(frequences),
                "autres_effectif": int(frequences.iloc[plan.limite :].sum()),
            }
            methode = "Fréquences des valeurs exactes ; cellules multivaluées conservées telles quelles"
            reponse = Reponse(
                statut="reponse",
                valeur=" ; ".join(f"{x['valeur']} : {x['effectif']}/{n}" for x in lignes),
                justification=f"Distribution de {nom} parmi les {n} observations renseignées, sans interpréter les codes.",
            )
        elif plan.operation == "proportion":
            succes = int(getattr(serie, plan.comparateur)(plan.seuil).sum())
            details = {
                "numerateur": succes,
                "denominateur": n,
                "pourcentage": 100 * succes / n,
                "ic95_wilson": wilson(succes, n),
                "seuil": plan.seuil,
                "comparateur": plan.comparateur,
            }
            methode = "Proportion observée et intervalle de Wilson à 95 %"
            reponse = Reponse(
                statut="reponse",
                valeur=details["pourcentage"],
                justification=f"{succes} observations sur {n} renseignées satisfont {nom} "
                f"{plan.comparateur} {plan.seuil} ; le résultat est exprimé en pourcentage.",
            )
            limites.append(
                "Le seuil est un critère explicite de requête ; sa validité clinique n'est pas déduite du dosage."
            )
        elif plan.operation == "comparer":
            groupe = depot.verifier_colonne(plan.groupe)
            if nom == groupe:
                raise Abstention("La variable de mesure et la variable de groupe doivent être différentes.")
            complets = tableau[[nom, groupe]].dropna()
            groupes = list(complets.groupby(groupe, sort=True, observed=True))
            if len(groupes) != 2:
                raise Abstention(
                    "La comparaison disponible exige exactement deux groupes renseignés.", "groupes_invalides"
                )
            if any(len(g) < depot.configuration.effectif_min for _, g in groupes):
                raise Abstention(
                    "Au moins un groupe a un effectif insuffisant pour cette analyse.", "effectif_insuffisant"
                )
            resultat = stats.mannwhitneyu(
                groupes[0][1][nom], groupes[1][1][nom], alternative="two-sided", method="asymptotic"
            )
            n = len(complets)
            details = {
                "groupes": [
                    {"valeur": str(k), "effectif": len(g), "mediane": float(g[nom].median())}
                    for k, g in groupes
                ],
                "statistique_u": float(resultat.statistic),
                "p_valeur": float(resultat.pvalue),
            }
            methode = "Mann–Whitney bilatéral asymptotique avec correction des ex æquo et de continuité"
            reponse = Reponse(
                statut="reponse",
                valeur=float(resultat.pvalue),
                justification=f"Comparaison exploratoire de {nom} entre deux groupes de {groupe}, "
                f"sur {n} dossiers complets ; la valeur rendue est la p-valeur bilatérale.",
            )
            limites.append(
                "Test de distributions supposant des observations indépendantes ; "
                "aucune preuve de causalité ni correction de comparaisons multiples."
            )
        else:
            seconde = depot.verifier_colonne(plan.seconde_colonne, quantitative=True)
            if nom == seconde:
                raise Abstention("Une corrélation demande deux variables différentes.")
            complets = tableau[[nom, seconde]].dropna()
            n = len(complets)
            if n < depot.configuration.effectif_min:
                raise Abstention(
                    "Effectif de paires complètes insuffisant pour étudier une corrélation.",
                    "effectif_insuffisant",
                )
            if any(complets[c].nunique() < 2 for c in (nom, seconde)):
                raise Abstention(
                    "Une variable est constante ; la corrélation est indéfinie.", "variable_constante"
                )
            resultat = stats.spearmanr(complets[nom], complets[seconde])
            details = {
                "rho": float(resultat.statistic),
                "p_valeur": float(resultat.pvalue) if n > 500 else None,
            }
            methode = "Corrélation de rangs de Spearman sur paires complètes"
            reponse = Reponse(
                statut="reponse",
                valeur=details["rho"],
                justification=f"Corrélation de Spearman entre {nom} et {seconde}, calculée sur {n} paires complètes.",
            )
            limites.append(
                "Les observations doivent être indépendantes ; la corrélation n'établit pas de causalité."
            )
            if n <= 500:
                limites.append(
                    "P-valeur asymptotique non publiée pour 500 observations ou moins ; "
                    "un test de permutation distinct serait nécessaire."
                )
    if len(tableau) - n:
        limites.append("Les valeurs manquantes sont exclues du dénominateur, sans imputation.")
    preuve = Preuve(
        source=depot.configuration.provenance,
        empreinte=depot.empreinte,
        plan=plan,
        methode=methode,
        population=depot.nombre,
        selection=len(tableau),
        exploitables=n,
        manquants=len(tableau) - n,
        details=details,
        limites=limites,
    )
    return reponse, preuve
