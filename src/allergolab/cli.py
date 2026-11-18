"""CLI autonome ; `cd agent` puis `uv run kit agent \"question\"`."""

import argparse
import json
import os
import sys
from pathlib import Path

from .configuration import Configuration
from .contrats import Demande, Plan


def afficher(objet):
    print(json.dumps(objet, ensure_ascii=False, indent=2, allow_nan=False))


def main(argv=None):
    for flux in (sys.stdout, sys.stderr):
        if hasattr(flux, "reconfigure"):
            flux.reconfigure(encoding="utf-8", errors="replace")
    parseur = argparse.ArgumentParser(description="ALLERGO LAB — backend scientifique autonome")
    commandes = parseur.add_subparsers(dest="commande", required=True)
    question = commandes.add_parser("agent", help="Poser une question en français")
    question.add_argument("question")
    question.add_argument(
        "--detail", action="store_true", help="Inclure preuves et mesures dans la sortie JSON"
    )
    analyse = commandes.add_parser("analyser", help="Exécuter un plan JSON, sans appel au modèle")
    analyse.add_argument("plan", help="Objet JSON du plan")
    commandes.add_parser("catalogue", help="Lister les colonnes et leurs définitions disponibles")
    commandes.add_parser("metriques", help="Mesures locales agrégées")
    evaluation = commandes.add_parser("evaluer", help="Évaluation hors ligne sur données fictives")
    evaluation.add_argument("--sortie", type=Path)
    commandes.add_parser("controle", help="Charger les données et lancer l'évaluation hors ligne")
    serveur = commandes.add_parser("servir", help="Lancer l'API")
    serveur.add_argument("--host", default="127.0.0.1")
    serveur.add_argument("--port", type=int, default=8000)
    arguments = parseur.parse_args(argv)
    try:
        if arguments.commande == "evaluer":
            from .evaluation import evaluer

            bilan = evaluer()
            if arguments.sortie:
                arguments.sortie.parent.mkdir(parents=True, exist_ok=True)
                arguments.sortie.write_text(json.dumps(bilan, ensure_ascii=False, indent=2), encoding="utf-8")
            afficher(bilan)
            return 0 if bilan["reussis"] == bilan["total"] and bilan["cache_verifie"] else 1
        configuration = Configuration.environnement()
        if arguments.commande == "servir":
            if arguments.host not in {"127.0.0.1", "::1", "localhost"} and not os.getenv(
                "ALLERGOLAB_CLE_API"
            ):
                raise ValueError(
                    "Définir ALLERGOLAB_CLE_API avant d'exposer le serveur hors de la machine locale."
                )
            import uvicorn

            from .api import creer_application

            uvicorn.run(
                creer_application(configuration),
                host=arguments.host,
                port=arguments.port,
                proxy_headers=False,
                access_log=False,
            )
            return 0
        from .service import Service

        service = Service(configuration)
        if arguments.commande == "catalogue":
            afficher(
                {
                    "empreinte": service.depot.empreinte,
                    "colonnes": [c for c in service.depot.catalogue.values() if not c["protegee"]],
                }
            )
        elif arguments.commande == "metriques":
            afficher(service.stockage.bilan())
        elif arguments.commande == "controle":
            from .evaluation import evaluer

            bilan = evaluer()
            bon = bilan["reussis"] == bilan["total"] and bilan["cache_verifie"]
            afficher(
                {
                    "donnees": "chargees",
                    "empreinte": service.depot.empreinte,
                    "evaluation": bilan,
                    "statut": "RÉUSSITE" if bon else "ÉCHEC",
                }
            )
            return 0 if bon else 1
        else:
            demande = (
                Demande(question=arguments.question)
                if arguments.commande == "agent"
                else Demande(plan=Plan.model_validate_json(arguments.plan))
            )
            rapport = service.traiter(demande)
            afficher(
                rapport.model_dump(mode="json")
                if getattr(arguments, "detail", False) or arguments.commande == "analyser"
                else rapport.reponse.model_dump(mode="json")
            )
            print(json.dumps(rapport.mesures.model_dump(), ensure_ascii=False), file=sys.stderr)
            return 1 if rapport.code == "erreur_interne" else 0
        return 0
    except KeyboardInterrupt:
        print("Interrompu.", file=sys.stderr)
        return 1
    except Exception as erreur:
        # Les erreurs de validation ne contiennent que des entrées fournies par l'utilisateur.
        from pydantic import ValidationError

        if isinstance(erreur, (ValueError, ValidationError)):
            print(f"Entrée ou configuration invalide : {erreur}", file=sys.stderr)
        else:
            print(
                f"Démarrage impossible ({type(erreur).__name__}) ; vérifier les données et la configuration.",
                file=sys.stderr,
            )
        return 1
