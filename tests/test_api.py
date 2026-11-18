from dataclasses import replace

from fastapi.testclient import TestClient

from allergolab.api import creer_application
from allergolab.service import Service


def test_api_et_contrat(service):
    with TestClient(creer_application(service=service, cle_api="secret-test")) as client:
        assert client.get("/health").status_code == 200
        assert client.get("/v1/catalogue").status_code == 401
        entetes = {"X-API-Key": "secret-test"}
        catalogue = client.get("/v1/catalogue", headers=entetes).json()
        assert all(c["colonne"] != "Patient_ID" for c in catalogue["colonnes"])
        reponse = client.post("/v1/questions", headers=entetes, json={"plan": {"operation": "compter"}})
        assert reponse.status_code == 200
        assert reponse.json()["reponse"]["valeur"] == 12
        assert reponse.json()["preuve"]["controles"]
        assert client.get("/v1/metriques", headers=entetes).json()["requetes"] == 1


def test_validation_api(service):
    with TestClient(creer_application(service=service)) as client:
        for corps in (
            {},
            {"question": " "},
            {"question": "bonjour", "plan": {"operation": "compter"}},
            {"plan": {"operation": "exec", "code": "print(1)"}},
            {"question": "a" * 4001},
        ):
            assert client.post("/v1/questions", json=corps).status_code == 422


def test_limitation_corps(service):
    with TestClient(creer_application(service=service)) as client:
        assert client.post("/v1/questions", content=b"x" * 32769).status_code == 413


def test_limitation_requetes(configuration):
    configuration = replace(configuration, requetes_minute=1)
    with TestClient(creer_application(service=Service(configuration))) as client:
        assert client.get("/v1/catalogue").status_code == 200
        assert client.get("/v1/catalogue").status_code == 429


def test_surcharge_http(service):
    for _ in range(service.configuration.analyses_simultanees):
        service.places.acquire()
    try:
        with TestClient(creer_application(service=service)) as client:
            assert client.post("/v1/questions", json={"plan": {"operation": "compter"}}).status_code == 503
    finally:
        for _ in range(service.configuration.analyses_simultanees):
            service.places.release()
