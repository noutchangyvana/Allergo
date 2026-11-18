"""API locale, mêmes contrats et moteur que la commande du concours."""

import hmac
import os
import time
from collections import deque
from contextlib import asynccontextmanager
from threading import Lock

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse

from . import __version__
from .configuration import Configuration
from .contrats import Demande, Rapport
from .service import Service


class CorpsLimite:
    """Limiter aussi les corps sans Content-Length, avant le parseur JSON."""

    def __init__(self, app, limite: int = 32768):
        self.app, self.limite = app, limite

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        corps = bytearray()
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            corps.extend(message.get("body", b""))
            if len(corps) > self.limite:
                reponse = JSONResponse({"detail": "Corps de requête trop volumineux."}, status_code=413)
                return await reponse(scope, receive, send)
            if not message.get("more_body", False):
                break
        transmis = False

        async def recevoir():
            nonlocal transmis
            if not transmis:
                transmis = True
                return {"type": "http.request", "body": bytes(corps), "more_body": False}
            return await receive()

        return await self.app(scope, recevoir, send)


def creer_application(
    configuration: Configuration | None = None, service: Service | None = None, cle_api: str | None = None
) -> FastAPI:
    configuration = configuration or (service.configuration if service else Configuration.environnement())
    secret = cle_api if cle_api is not None else os.getenv("ALLERGOLAB_CLE_API", "")
    passages = deque()
    verrou = Lock()

    @asynccontextmanager
    async def cycle_vie(application):
        application.state.service = service or Service(configuration)
        yield

    application = FastAPI(
        title="ALLERGO LAB",
        version=__version__,
        lifespan=cycle_vie,
        description="Analyses de cohorte calculées, vérifiées et traçables.",
    )
    application.add_middleware(CorpsLimite)

    def autoriser(request: Request, x_api_key: str | None = Header(default=None)):
        if secret:
            if not x_api_key or not hmac.compare_digest(x_api_key.encode(), secret.encode()):
                raise HTTPException(401, "Clé d'accès API absente ou incorrecte.")
        elif not request.client or request.client.host not in {"127.0.0.1", "::1", "localhost", "testclient"}:
            raise HTTPException(403, "Accès sans clé limité à la machine locale.")
        with verrou:
            maintenant = time.monotonic()
            while passages and passages[0] <= maintenant - 60:
                passages.popleft()
            if len(passages) >= configuration.requetes_minute:
                raise HTTPException(
                    429,
                    "Limite de requêtes atteinte ; réessayer dans une minute.",
                    headers={"Retry-After": "60"},
                )
            passages.append(maintenant)

    @application.get("/health")
    def sante():
        return {"statut": "pret", "version": __version__}

    @application.get("/v1/catalogue", dependencies=[Depends(autoriser)])
    def catalogue(request: Request):
        depot = request.app.state.service.depot
        return {
            "empreinte": depot.empreinte,
            "source": depot.configuration.provenance,
            "colonnes": [c for c in depot.catalogue.values() if not c["protegee"]],
        }

    @application.post("/v1/questions", response_model=Rapport, dependencies=[Depends(autoriser)])
    def question(demande: Demande, request: Request):
        rapport = request.app.state.service.traiter(demande)
        if rapport.code == "surcharge":
            return JSONResponse(
                rapport.model_dump(mode="json"), status_code=503, headers={"Retry-After": "2"}
            )
        if rapport.code == "erreur_interne":
            return JSONResponse(rapport.model_dump(mode="json"), status_code=500)
        return rapport

    @application.get("/v1/metriques", dependencies=[Depends(autoriser)])
    def metriques(request: Request):
        return request.app.state.service.stockage.bilan()

    return application
