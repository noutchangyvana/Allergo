"""Régressions reproductibles sur une cohorte entièrement inventée, sans modèle."""

import json
import math
import statistics
import tempfile
from pathlib import Path

from .configuration import Configuration
from .contrats import Demande, Plan
from .service import Service

COHORTE_FICTIVE = """Patient_ID;Chip_Type;Age;Groupe;Score;Ara_h_2;Bet_v_1
1;A;20;X;1;0,2;1,0
2;A;22;X;2;0,4;1,2
3;A;24;X;3;0,6;1,4
4;A;26;X;4;0,8;1,6
5;A;28;X;5;1,0;1,8
6;A;40;Y;6;1,2;2,0
7;A;42;Y;7;1,4;2,2
8;A;44;Y;8;1,6;2,4
9;A;46;Y;9;1,8;2,6
10;A;48;Y;10;;2,8
11;B;50;Y;11;2,0;
12;B;;Y;12;2,2;
"""


def creer_fixture(dossier: Path) -> Configuration:
    donnees = dossier / "cohorte-fictive.csv"
    donnees.write_text(COHORTE_FICTIVE, encoding="utf-8")
    metadata = dossier / "definitions.json"
    metadata.write_text(
        json.dumps({"Score": {"quantitative": True, "description": "Score fictif de démonstration"}}),
        encoding="utf-8",
    )
    return Configuration(
        donnees=donnees,
        runtime=dossier / "runtime",
        nombre_cliniques=5,
        metadata=metadata,
        provenance="Cohorte fictive — aucune donnée réelle",
    )


def evaluer() -> dict:
    with tempfile.TemporaryDirectory(prefix="allergolab-evaluation-") as temporaire:
        service = Service(creer_fixture(Path(temporaire)))
        puce_a = [{"colonne": "Chip_Type", "operateur": "eq", "valeur": "A"}]
        cas = [
            ("comptage direct", Demande(question="Combien de lignes compte le tableau ?"), "reponse", 12),
            ("moyenne âge", Demande(plan=Plan(operation="decrire", colonne="Age")), "reponse", 390 / 11),
            (
                "proportion et absences",
                Demande(plan=Plan(operation="proportion", colonne="Ara_h_2", seuil=1, filtres=puce_a)),
                "reponse",
                500 / 9,
            ),
            (
                "filtre âge",
                Demande(
                    plan=Plan(
                        operation="compter", filtres=[{"colonne": "Age", "operateur": "lt", "valeur": 30}]
                    )
                ),
                "reponse",
                5,
            ),
            (
                "comparaison deux groupes",
                Demande(plan=Plan(operation="comparer", colonne="Age", groupe="Groupe")),
                "reponse",
                None,
            ),
            (
                "corrélation",
                Demande(plan=Plan(operation="correler", colonne="Age", seconde_colonne="Score")),
                "reponse",
                1.0,
            ),
            (
                "variable absente",
                Demande(plan=Plan(operation="decrire", colonne="Severite")),
                "abstention",
                None,
            ),
            (
                "dosages hétérogènes",
                Demande(plan=Plan(operation="decrire", colonne="Ara_h_2")),
                "abstention",
                None,
            ),
            (
                "identifiant",
                Demande(plan=Plan(operation="frequences", colonne="Patient_ID")),
                "abstention",
                None,
            ),
            (
                "petit groupe",
                Demande(plan=Plan(operation="comparer", colonne="Age", groupe="Chip_Type")),
                "abstention",
                None,
            ),
            (
                "causalité",
                Demande(question="Ara_h_2 provoque-t-il des réactions graves ?"),
                "abstention",
                None,
            ),
            ("ambiguïté", Demande(question="Les allergènes sont-ils dangereux ?"), "abstention", None),
        ]
        resultats, durees = [], []
        for nom, demande, statut, valeur in cas:
            rapport = service.traiter(demande)
            correct = rapport.reponse.statut == statut
            if valeur is not None:
                correct = (
                    correct
                    and isinstance(rapport.reponse.valeur, (int, float))
                    and math.isclose(rapport.reponse.valeur, valeur, abs_tol=1e-9)
                )
            resultats.append(
                {"cas": nom, "reussi": correct, "statut": rapport.reponse.statut, "code": rapport.code}
            )
            durees.append(rapport.mesures.duree_ms)
        cache = service.traiter(cas[0][1]).mesures.cache
        return {
            "jeu": "fictif",
            "total": len(cas),
            "reussis": sum(r["reussi"] for r in resultats),
            "cache_verifie": cache,
            "latence_mediane_ms": statistics.median(durees),
            "latence_p95_ms": sorted(durees)[math.ceil(0.95 * len(durees)) - 1],
            "mesures": service.stockage.bilan(),
            "resultats": resultats,
            "limite": "Mesure locale sur données fictives ; ne mesure pas la compréhension d'un modèle réel.",
        }
