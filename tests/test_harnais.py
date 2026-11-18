import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace

from allergolab.contrats import Demande, Plan
from allergolab.service import Service


def test_cache_et_metriques(service):
    demande = Demande(plan=Plan(operation="decrire", colonne="Age"))
    premier = service.traiter(demande)
    second = service.traiter(demande)
    assert not premier.mesures.cache
    assert second.mesures.cache
    assert premier.identifiant != second.identifiant
    assert premier.preuve == second.preuve
    bilan = service.stockage.bilan()
    assert bilan["requetes"] == 2
    assert bilan["cache"] == 1


def test_cache_change_avec_les_donnees(configuration):
    demande = Demande(plan=Plan(operation="decrire", colonne="Age"))
    premier = Service(configuration).traiter(demande)
    texte = configuration.donnees.read_text(encoding="utf-8").replace("1;A;20", "1;A;21")
    configuration.donnees.write_text(texte, encoding="utf-8")
    second = Service(configuration).traiter(demande)
    assert not second.mesures.cache
    assert second.preuve.empreinte != premier.preuve.empreinte
    assert second.reponse.valeur != premier.reponse.valeur


def test_cache_change_avec_definitions(configuration):
    premier = Service(configuration)
    premier.traiter(Demande(plan=Plan(operation="decrire", colonne="Score")))
    configuration.metadata.write_text("{}", encoding="utf-8")
    rapport = Service(configuration).traiter(Demande(plan=Plan(operation="decrire", colonne="Score")))
    assert rapport.code == "codage_non_valide"
    assert not rapport.mesures.cache


def test_cache_corrompu_recalcule(service):
    demande = Demande(plan=Plan(operation="compter"))
    service.traiter(demande)
    with service.stockage.connexion() as connexion:
        contenu = json.loads(connexion.execute("SELECT contenu FROM cache").fetchone()[0])
        contenu["reponse"]["valeur"] = 999
        connexion.execute("UPDATE cache SET contenu=?", (json.dumps(contenu),))
    resultat = service.traiter(demande)
    assert resultat.reponse.valeur == 12
    assert not resultat.mesures.cache


def test_cache_borne(configuration):
    service = Service(replace(configuration, cache_max=2))
    for seuil in (20, 30, 40):
        service.traiter(Demande(plan=Plan(operation="proportion", colonne="Age", seuil=seuil)))
    with service.stockage.connexion() as connexion:
        assert connexion.execute("SELECT COUNT(*) FROM cache").fetchone()[0] == 2


def test_telemetrie_sans_texte(service):
    question = "Une question privée et inconnue"
    service.traiter(Demande(question=question))
    with service.stockage.connexion() as connexion:
        lignes = connexion.execute("SELECT * FROM evenements").fetchall()
    assert question not in repr(lignes)
    assert "Patient_ID" not in repr(lignes)


def test_concurrence_un_seul_appel(configuration):
    appels = []

    def planifier(question, depot, configuration, mesures):
        appels.append(question)
        mesures.appels_modele += 1
        return Plan(operation="decrire", colonne="Age")

    service = Service(replace(configuration, modele_actif=True), planificateur=planifier)
    demande = Demande(question="Merci de fournir une description quantitative de Age")
    with ThreadPoolExecutor(max_workers=4) as pool:
        rapports = list(pool.map(lambda _: service.traiter(demande), range(4)))
    assert len(appels) == 1
    assert sum(r.mesures.cache for r in rapports) == 3
    assert all(r.reponse.statut == "reponse" for r in rapports)


def test_seuil_invente_refuse(configuration):
    service = Service(
        replace(configuration, modele_actif=True),
        planificateur=lambda *args: Plan(operation="proportion", colonne="Age", seuil=30),
    )
    rapport = service.traiter(Demande(question="Quelle proportion a un âge élevé ?"))
    assert rapport.code == "seuil_non_precise"


def test_pas_de_modele_pour_causalite(configuration):
    def interdit(*args):
        raise AssertionError("Le modèle ne doit pas être appelé")

    service = Service(replace(configuration, modele_actif=True), planificateur=interdit)
    assert (
        service.traiter(Demande(question="Cet allergène provoque-t-il des symptômes ?")).code
        == "hors_perimetre"
    )


def test_erreur_interne_masquee(configuration):
    def echouer(*args):
        raise RuntimeError("secret et chemin privé")

    service = Service(replace(configuration, modele_actif=True), planificateur=echouer)
    rapport = service.traiter(Demande(question="Une question non reconnue"))
    assert rapport.code == "erreur_interne"
    assert "secret" not in rapport.model_dump_json()
    assert service.stockage.bilan()["requetes"] == 1


def test_surcharge(service):
    for _ in range(service.configuration.analyses_simultanees):
        service.places.acquire()
    try:
        rapport = service.traiter(Demande(plan=Plan(operation="compter")))
        assert rapport.code == "surcharge"
    finally:
        for _ in range(service.configuration.analyses_simultanees):
            service.places.release()
