"""Outil : comparer la fréquence d'une sensibilisation entre groupes de patients (puce, région, sexe...).

Pourquoi : « est-ce plus fréquent chez X que chez Y » demande un pourcentage par
groupe, chacun calculé sur les patients testés de ce groupe. Le code 9 (non
renseigné) n'est jamais un groupe.
"""


from allergolab.vitrine import commun


def prevalence_par_groupe(allergene: str, groupe: str, seuil: float | None = None) -> list:
    """Pourcentage de patients sensibilisés à un allergène, parmi les testés, pour chaque valeur d'une colonne clinique.
    Les groupes de moins de 30 patients testés sont signalés comme trop petits.

    Args:
        allergene: le nom exact de la colonne de dosage, par exemple "Ara_h_2".
        groupe: une colonne clinique à 20 valeurs au plus, par exemple "Chip_Type", "French_Region" ou "Gender".
        seuil: valeur à partir de laquelle un dosage compte comme positif ; None pour le seuil de l'équipe (0,3).
    """
    commun.verifier_colonne(allergene, bloc="dosage")
    commun.verifier_colonne(groupe, bloc="clinique")
    seuil = commun.SEUIL_POSITIF if seuil is None else seuil
    t = commun.tableau()
    valeurs_du_groupe = t[groupe].dropna().astype(str).str.replace(".0", "", regex=False)
    if valeurs_du_groupe.nunique() > 20:
        raise ValueError(f"La colonne {groupe!r} a trop de valeurs différentes pour former des groupes.")
    resultat = []
    for valeur in sorted(valeurs_du_groupe.unique()):
        if groupe in commun.COLONNES_AVEC_CODE_9 and valeur == commun.CODE_NON_RENSEIGNE:
            continue
        lignes = t.loc[valeurs_du_groupe.index[valeurs_du_groupe == valeur]]
        valides, _, _ = commun.lire_dosage(lignes[allergene])
        positifs = int((valides >= seuil).sum())
        ligne = {
            "groupe": valeur,
            "patients_testes": len(valides),
            "patients_positifs": positifs,
            "pourcentage_parmi_testes": commun.pourcentage(positifs, len(valides)),
            "intervalle_confiance_95": commun.intervalle_wilson(positifs, len(valides)),
        }
        if len(valides) < commun.MINIMUM_PATIENTS:
            ligne["avertissement"] = "groupe trop petit pour conclure"
        resultat.append(ligne)
    return resultat
