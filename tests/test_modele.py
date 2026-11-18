from dataclasses import replace
from types import SimpleNamespace

import pytest

from allergolab.contrats import Mesures
from allergolab.donnees import Abstention


@pytest.fixture
def reglage_modele(configuration, tmp_path, monkeypatch):
    reglages = tmp_path / "modeles.toml"
    reglages.write_text(
        '[modeles.developpement]\nidentifiant="faux"\nentree=0.1\nsortie=0.5\n', encoding="utf-8"
    )
    monkeypatch.setenv("ALLERGYLAB_CLE", "cle-fictive-pour-tests")
    return replace(configuration, reglages=reglages)


def test_planificateur_toolcalling_reel_sans_reseau(service, monkeypatch):
    from smolagents import Model
    from smolagents.models import ChatMessage, ChatMessageToolCall, ChatMessageToolCallFunction
    from smolagents.monitoring import TokenUsage

    from allergolab import modele

    class FauxModele(Model):
        erreur_finale = None

        def generate(self, messages, **kwargs):
            return ChatMessage(
                role="assistant",
                content="",
                token_usage=TokenUsage(input_tokens=12, output_tokens=10),
                tool_calls=[
                    ChatMessageToolCall(
                        id="appel-1",
                        type="function",
                        function=ChatMessageToolCallFunction(
                            name="final_answer",
                            arguments={"answer": {"operation": "decrire", "colonne": "Age"}},
                        ),
                    )
                ],
            )

    monkeypatch.setattr(modele, "construire_modele", lambda *args: FauxModele())
    plan = modele.planifier("Décrire Age", service.depot, service.configuration, Mesures())
    assert plan.operation == "decrire"
    assert plan.colonne == "Age"


def test_mesure_jetons_et_appel_borne(reglage_modele, monkeypatch):
    from smolagents import LiteLLMModel

    from allergolab.modele import construire_modele

    appels = []

    def generer(self, messages, **options):
        appels.append(options)
        return SimpleNamespace(token_usage=SimpleNamespace(input_tokens=100, output_tokens=20))

    monkeypatch.setattr(LiteLLMModel, "generate", generer)
    mesures = Mesures()
    modele = construire_modele(reglage_modele, mesures)
    modele.generate([{"role": "user", "content": "texte"}])
    assert mesures.appels_modele == 1
    assert mesures.jetons_entree == 100
    assert mesures.jetons_sortie == 20
    assert mesures.cout_estime_usd == pytest.approx(0.00002)
    with pytest.raises(Abstention, match="maximal"):
        modele.generate([])
    assert len(appels) == 1


@pytest.mark.parametrize("code,attendu", [(429, 3), (529, 3), (400, 1), (401, 1), (500, 1)])
def test_reprises_limitees(reglage_modele, monkeypatch, code, attendu):
    from smolagents import LiteLLMModel

    from allergolab import modele

    appels, attentes = [], []

    class ErreurFournisseur(Exception):
        status_code = code

    def echouer(*args, **kwargs):
        appels.append(1)
        raise ErreurFournisseur("erreur simulée")

    monkeypatch.setattr(LiteLLMModel, "generate", echouer)
    monkeypatch.setattr(modele.time, "sleep", attentes.append)
    mesure = Mesures()
    client = modele.construire_modele(reglage_modele, mesure)
    with pytest.raises(Abstention):
        client.generate([])
    assert len(appels) == mesure.appels_modele == attendu
    assert len(attentes) == attendu - 1


def test_budget_avant_reseau(reglage_modele, monkeypatch):
    from smolagents import LiteLLMModel

    from allergolab.modele import construire_modele

    def interdit(*args, **kwargs):
        raise AssertionError("Aucun appel ne doit être envoyé")

    monkeypatch.setattr(LiteLLMModel, "generate", interdit)
    mesure = Mesures()
    client = construire_modele(replace(reglage_modele, budget_usd=0.000000001), mesure)
    with pytest.raises(Abstention, match="Budget"):
        client.generate([])
    assert mesure.appels_modele == 0
