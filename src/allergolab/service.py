"""Harnais : router → planifier → calculer → vérifier → restituer → mesurer."""

import hashlib
import json
import logging
import time
from dataclasses import asdict
from pathlib import Path
from threading import BoundedSemaphore, RLock
from uuid import uuid4

from pydantic import ValidationError

from . import __version__
from .analyse import executer
from .configuration import Configuration
from .contrats import Demande, Mesures, Preuve, Rapport, Reponse
from .donnees import Abstention, Depot
from .evidence import verifier
from .routage import garde_question, plan_direct, verifier_seuil_question
from .stockage import Stockage

LOGGER = logging.getLogger(__name__)


class Service:
    def __init__(self, configuration: Configuration | None = None, planificateur=None):
        self.configuration = configuration or Configuration.environnement()
        self.depot = Depot(self.configuration)
        self.stockage = Stockage(self.configuration)
        self.planificateur = planificateur
        self.places = BoundedSemaphore(self.configuration.analyses_simultanees)
        # Verrous par compartiment : éviter les appels identiques en concurrence sans croissance illimitée.
        self.verrous = [RLock() for _ in range(64)]
        sources = b"".join(p.read_bytes() for p in sorted(Path(__file__).parent.glob("*.py")))
        self.version_moteur = hashlib.sha256(sources).hexdigest()

    def _cle(self, demande: Demande):
        entree = {
            "demande": demande.model_dump(mode="json"),
            "donnees": self.depot.empreinte,
            "configuration": {k: str(v) for k, v in asdict(self.configuration).items()},
            "version": __version__,
            "moteur": self.version_moteur,
        }
        return hashlib.sha256(json.dumps(entree, sort_keys=True, ensure_ascii=False).encode()).hexdigest()

    def traiter(self, demande: Demande) -> Rapport:
        debut = time.perf_counter()
        mesures = Mesures(route="structuree" if demande.plan else "directe")
        rapport = Rapport(
            identifiant=uuid4().hex,
            reponse=Reponse(statut="abstention", valeur=None, justification="Analyse non terminée."),
            mesures=mesures,
        )
        acquis = self.places.acquire(blocking=False)
        try:
            if not acquis:
                raise Abstention("Le moteur est occupé ; réessayer dans quelques instants.", "surcharge")
            cle = self._cle(demande)
            with self.verrous[int(cle[:8], 16) % len(self.verrous)]:
                # La politique scientifique s'applique aussi avant toute lecture du cache.
                if demande.question:
                    garde_question(demande.question)
                contenu = self.stockage.lire(cle)
                if contenu and contenu.get("preuve"):
                    try:
                        reponse = Reponse.model_validate(contenu["reponse"])
                        preuve = Preuve.model_validate(contenu["preuve"])
                        if demande.plan is not None and preuve.plan != demande.plan:
                            raise Abstention(
                                "Le plan du cache ne correspond pas à la demande.", "cache_invalide"
                            )
                        verifier(self.depot, reponse, preuve)
                        rapport.reponse, rapport.preuve = reponse, preuve
                        mesures.cache = True
                        return rapport
                    except (ValidationError, Abstention, KeyError, TypeError):
                        pass  # Recalculer une entrée corrompue, sans la publier.
                plan = demande.plan
                if plan is None:
                    plan = plan_direct(demande.question, self.depot)
                    if plan is None:
                        if not self.configuration.modele_actif:
                            raise Abstention(
                                "Cette formulation nécessite une planification ; activer le modèle "
                                "ou fournir un plan structuré et préciser les variables.",
                                "clarification_requise",
                            )
                        mesures.route = "modele"
                        if self.planificateur is None:
                            from .modele import planifier

                            self.planificateur = planifier
                        plan = self.planificateur(demande.question, self.depot, self.configuration, mesures)
                    verifier_seuil_question(demande.question, plan)
                reponse, preuve = executer(self.depot, plan)
                verifier(self.depot, reponse, preuve)
                rapport.reponse, rapport.preuve = reponse, preuve
                self.stockage.memoriser(cle, rapport)
        except Abstention as erreur:
            rapport.reponse = Reponse(statut="abstention", valeur=None, justification=str(erreur))
            rapport.preuve = None
            rapport.code = erreur.code
        except Exception as erreur:
            # Ne jamais exposer messages fournisseur, chemins locaux ou valeurs de cellules.
            LOGGER.error("Analyse interrompue (%s), requête %s", type(erreur).__name__, rapport.identifiant)
            rapport.reponse = Reponse(
                statut="abstention",
                valeur=None,
                justification="Erreur interne pendant l'analyse ; transmettre l'identifiant de requête au mainteneur.",
            )
            rapport.preuve = None
            rapport.code = "erreur_interne"
        finally:
            if acquis:
                self.places.release()
            mesures.duree_ms = (time.perf_counter() - debut) * 1000
            try:
                self.stockage.noter(rapport, self.depot.empreinte)
            except Exception as erreur:
                LOGGER.error("Télémétrie indisponible (%s)", type(erreur).__name__)
        return rapport

    def repondre(self, question: str) -> dict:
        """Adaptateur au contrat du concours : exactement trois clés."""
        return self.traiter(Demande(question=question)).reponse.model_dump(mode="json")
