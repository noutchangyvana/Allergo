import math
from dataclasses import replace

import pytest
from pydantic import ValidationError

from allergolab.analyse import executer
from allergolab.contrats import Demande, Plan
from allergolab.donnees import Abstention, Depot
from allergolab.evaluation import evaluer
from allergolab.evidence import verifier
from allergolab.service import Service


def test_batterie_fictive():
    resultat = evaluer()
    assert resultat["reussis"] == resultat["total"] == 12, resultat
    assert resultat["cache_verifie"]
    assert resultat["mesures"]["appels_modele"] == 0


@pytest.mark.parametrize(
    "question", ["Combien de lignes compte le tableau ?", "Combien de patients dans la cohorte ?"]
)
def test_chemin_direct(service, question):
    rapport = service.traiter(Demande(question=question))
    assert rapport.reponse.valeur == 12
    assert rapport.mesures.appels_modele == 0
    assert rapport.preuve.controles
    assert set(service.repondre(question)) == {"statut", "valeur", "justification"}


@pytest.mark.parametrize("question", ["Quelle est la moyenne de Age ?", "Quel est l'âge moyen ?"])
def test_age_direct(service, question):
    rapport = service.traiter(Demande(question=question))
    assert rapport.reponse.statut == "reponse", rapport
    assert math.isclose(rapport.reponse.valeur, 390 / 11)
    assert rapport.preuve.manquants == 1


def test_denominteur_et_wilson(service):
    rapport = service.traiter(
        Demande(
            plan=Plan(
                operation="proportion",
                colonne="Ara_h_2",
                seuil=1,
                filtres=[{"colonne": "Chip_Type", "operateur": "eq", "valeur": "A"}],
            )
        )
    )
    assert math.isclose(rapport.reponse.valeur, 500 / 9)
    assert rapport.preuve.selection == 10
    assert rapport.preuve.exploitables == 9
    assert rapport.preuve.manquants == 1
    assert rapport.preuve.details["numerateur"] == 5
    bas, haut = rapport.preuve.details["ic95_wilson"]
    assert 20 < bas < rapport.reponse.valeur < haut < 90


@pytest.mark.parametrize("seuil,attendu", [(0, 100), (100, 0)])
def test_wilson_aux_extremes(service, seuil, attendu):
    rapport = service.traiter(Demande(plan=Plan(operation="proportion", colonne="Age", seuil=seuil)))
    assert rapport.reponse.valeur == attendu
    assert rapport.preuve.controles


def test_evidence_detecte_manipulation(service):
    reponse, preuve = executer(service.depot, Plan(operation="decrire", colonne="Age"))
    reponse.valeur = 999
    with pytest.raises(Abstention, match="EVIDENCE"):
        verifier(service.depot, reponse, preuve)


def test_evidence_detecte_denominteur(service):
    reponse, preuve = executer(service.depot, Plan(operation="proportion", colonne="Age", seuil=30))
    preuve.details["denominateur"] = 12
    with pytest.raises(Abstention, match="EVIDENCE"):
        verifier(service.depot, reponse, preuve)


def test_evidence_detecte_test_statistique_manipule(service):
    reponse, preuve = executer(service.depot, Plan(operation="comparer", colonne="Age", groupe="Groupe"))
    reponse.valeur = preuve.details["p_valeur"] = 0.5
    with pytest.raises(Abstention, match="EVIDENCE"):
        verifier(service.depot, reponse, preuve)


def test_filtre_dosage_ne_masque_pas_melange_puces(service):
    rapport = service.traiter(
        Demande(
            plan=Plan(operation="compter", filtres=[{"colonne": "Ara_h_2", "operateur": "gt", "valeur": 2}])
        )
    )
    assert rapport.code == "puce_ambigue"


def test_frequences_tronquees(service):
    rapport = service.traiter(Demande(plan=Plan(operation="frequences", colonne="Age", limite=2)))
    assert len(rapport.preuve.details["modalites"]) == 2
    assert rapport.preuve.details["autres_effectif"] == 9


def test_absences_et_puces(service):
    rapport = service.traiter(Demande(plan=Plan(operation="manquants", colonne="Bet_v_1")))
    assert rapport.preuve.details["colonnes"][0]["manquants"] == 2
    assert any("structurelle" in texte for texte in rapport.preuve.limites)


@pytest.mark.parametrize(
    "plan,code",
    [
        ({"operation": "decrire", "colonne": "Inconnue"}, "variable_absente"),
        ({"operation": "frequences", "colonne": "Patient_ID"}, "identifiant_protege"),
        ({"operation": "decrire", "colonne": "Ara_h_2"}, "puce_ambigue"),
        ({"operation": "decrire", "colonne": "Groupe"}, "codage_non_valide"),
        ({"operation": "comparer", "colonne": "Age", "groupe": "Chip_Type"}, "effectif_insuffisant"),
        (
            {"operation": "compter", "filtres": [{"colonne": "Age", "operateur": "eq", "valeur": "20"}]},
            "filtre_invalide",
        ),
        (
            {
                "operation": "decrire",
                "colonne": "Age",
                "filtres": [{"colonne": "Age", "operateur": "gt", "valeur": 100}],
            },
            "selection_vide",
        ),
    ],
)
def test_abstentions_explicites(service, plan, code):
    rapport = service.traiter(Demande(plan=Plan.model_validate(plan)))
    assert rapport.reponse.statut == "abstention"
    assert rapport.reponse.valeur is None
    assert rapport.code == code


def test_compte_vide_est_zero(service):
    rapport = service.traiter(
        Demande(
            plan=Plan(operation="compter", filtres=[{"colonne": "Age", "operateur": "gt", "valeur": 100}])
        )
    )
    assert rapport.reponse.valeur == 0


def test_spearman_sans_pvaleur_approximative(service):
    rapport = service.traiter(
        Demande(plan=Plan(operation="correler", colonne="Age", seconde_colonne="Score"))
    )
    assert math.isclose(rapport.reponse.valeur, 1)
    assert rapport.preuve.details["p_valeur"] is None
    assert rapport.preuve.exploitables == 11


def test_variable_constante(configuration):
    texte = configuration.donnees.read_text(encoding="utf-8").splitlines()
    lignes = [texte[0]]
    for ligne in texte[1:]:
        cellules = ligne.split(";")
        cellules[4] = "1"
        lignes.append(";".join(cellules))
    configuration.donnees.write_text("\n".join(lignes), encoding="utf-8")
    rapport = Service(configuration).traiter(
        Demande(plan=Plan(operation="correler", colonne="Age", seconde_colonne="Score"))
    )
    assert rapport.code == "variable_constante"


def test_patient_non_unique(configuration):
    texte = configuration.donnees.read_text(encoding="utf-8").replace("2;A;22", "1;A;22")
    configuration.donnees.write_text(texte, encoding="utf-8")
    service = Service(configuration)
    assert (
        service.traiter(Demande(question="Combien de patients dans la cohorte ?")).code == "unite_observation"
    )
    assert service.traiter(Demande(plan=Plan(operation="compter"))).reponse.valeur == 12


def test_identifiants_repetes_bloquent_inference(configuration):
    texte = configuration.donnees.read_text(encoding="utf-8").replace("2;A;22", "1;A;22")
    configuration.donnees.write_text(texte, encoding="utf-8")
    rapport = Service(configuration).traiter(
        Demande(plan=Plan(operation="comparer", colonne="Age", groupe="Groupe"))
    )
    assert rapport.code == "observations_non_independantes"


@pytest.mark.parametrize(
    "plan",
    [
        {"operation": "eval", "code": "1+1"},
        {"operation": "proportion", "colonne": "Age"},
        {"operation": "compter", "colonne": "Age"},
        {"operation": "compter", "filtres": [{"colonne": "Age", "operateur": "in", "valeur": 20}]},
        {"operation": "decrire", "colonne": "Age", "seuil": float("nan")},
        {"operation": "decrire", "colonne": "Age", "limite": 1000000},
    ],
)
def test_plans_fermes(plan):
    with pytest.raises(ValidationError):
        Plan.model_validate(plan)


def test_code_numerique_sans_definition(configuration):
    depot = Depot(replace(configuration, metadata=None))
    with pytest.raises(Abstention, match="quantitative"):
        executer(depot, Plan(operation="decrire", colonne="Score"))


def test_pas_de_mutation_du_depot(service):
    copie = service.depot._tableau.copy(deep=True)
    for operation in ("decrire", "frequences", "manquants"):
        service.traiter(Demande(plan=Plan(operation=operation, colonne="Age")))
    assert copie.equals(service.depot._tableau)
