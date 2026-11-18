"""Tests isolés : ni réseau, ni vraie clé, ni lecture des données de recherche."""

import socket

import pytest

from allergolab.evaluation import creer_fixture
from allergolab.service import Service


@pytest.fixture(autouse=True)
def isoler(monkeypatch):
    monkeypatch.delenv("ALLERGYLAB_CLE", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("ALLERGOLAB_CLE_API", raising=False)
    connexion = socket.socket.connect

    def refuser(prise, adresse, *args):
        if isinstance(adresse, tuple) and adresse[0] in {"127.0.0.1", "::1"}:
            return connexion(prise, adresse, *args)
        raise AssertionError("Un test tente une connexion réseau.")

    monkeypatch.setattr(socket.socket, "connect", refuser)


@pytest.fixture
def configuration(tmp_path):
    return creer_fixture(tmp_path)


@pytest.fixture
def service(configuration):
    return Service(configuration)
