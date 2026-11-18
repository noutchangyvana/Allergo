"""La page web et l'onglet Explorer : servis, cohérents, sans modèle et sans coût."""

import pytest
from fastapi.testclient import TestClient

from allergolab.api import creer_application
from allergolab.configuration import Configuration
from allergolab.service import Service
from allergolab.vitrine.routes import ajouter_page


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    # Le fichier de données du projet, un dossier temporaire pour le cache du moteur.
    service = Service(Configuration(runtime=tmp_path_factory.mktemp("runtime")))
    application = creer_application(service=service)
    application.state.service = service
    ajouter_page(application, service)
    with TestClient(application) as client:
        yield client


def question(client, texte):
    reponse = client.post("/question", json={"question": texte})
    assert reponse.status_code == 200
    return reponse.json()


def test_page_et_fichiers(client):
    assert "AllergyLab" in client.get("/").text
    assert client.get("/fond_paysage.jpg").headers["content-type"] == "image/jpeg"
    assert client.get("/avatar/cumulus.avatar.json").json()["name"]


def test_colonnes(client):
    corps = client.get("/colonnes").json()
    assert "Ara_h_2" in corps["dosage"] and "Chip_Type" in corps["clinique"]
    assert corps["noms"]["Ara_h_2"]["source"] == "Arachide"


def test_explorer(client):
    resume = client.get("/explorer/resume").json()
    assert resume["patients"] == sum(resume["par_puce"].values())
    lignes = client.get("/explorer/classement?puce=ALEX").json()
    assert lignes and all(x["testes"] >= 30 for x in lignes)
    assert [x["pourcentage"] for x in lignes] == sorted((x["pourcentage"] for x in lignes), reverse=True)
    fiche = client.get("/explorer/allergene?code=Ara_h_2").json()
    assert 0 <= fiche["ensemble"]["pourcentage_parmi_testes"] <= 100
    assert client.get("/explorer/clinique?colonne=Skin_Symptoms").json()["colonne"] == "Skin_Symptoms"


def test_explorer_refuse_entrees_inconnues(client):
    assert client.get("/explorer/allergene?code=Inconnu").status_code == 400
    assert client.get("/explorer/classement?puce=AUTRE").status_code == 400
    assert client.get("/explorer/autre").status_code == 404


def test_question_prevalence_structuree(client):
    r = question(client, "Quel pourcentage des patients testés est sensibilisé à Ara_h_2 ?")
    assert r["etat"] == "reponse" and r["analyse"]["type"] == "prevalence_allergene"
    assert r["valeur"] == r["analyse"]["ligne"]["pourcentage"]
    assert r["cout"] == 0


def test_question_classement_structure(client):
    r = question(client, "Quels sont les cinq allergènes les plus fréquents parmi les patients testés ?")
    assert r["etat"] == "reponse" and len(r["analyse"]["lignes"]) == 5


def test_question_par_le_moteur(client):
    r = question(client, "Quel est l'âge moyen des patients ?")
    assert r["etat"] == "reponse" and r["etapes"]
    assert question(client, "Ara_h_2 provoque-t-il des réactions graves ?")["etat"] == "abstention"
    assert question(client, " ")["etat"] == "erreur"


def test_origine_etrangere_refusee(client):
    reponse = client.post("/question", json={"question": "x"}, headers={"Origin": "https://autre.exemple"})
    assert reponse.status_code == 403
