"""SQLite local : cache borné et télémétrie sans texte de question ni dossier patient."""

import json
import sqlite3
import time
from contextlib import contextmanager
from threading import Lock

from .configuration import Configuration
from .contrats import Rapport


class Stockage:
    def __init__(self, configuration: Configuration):
        configuration.runtime.mkdir(parents=True, exist_ok=True)
        self.chemin = configuration.runtime / "allergolab.sqlite3"
        self.configuration = configuration
        self.verrou = Lock()
        with self.connexion() as connexion:
            connexion.executescript("""
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS cache (
                    cle TEXT PRIMARY KEY, expiration REAL NOT NULL, contenu TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS evenements (
                    identifiant TEXT PRIMARY KEY, date REAL NOT NULL, empreinte TEXT NOT NULL,
                    statut TEXT NOT NULL, code TEXT NOT NULL, route TEXT NOT NULL,
                    duree_ms REAL NOT NULL, cache INTEGER NOT NULL, appels INTEGER NOT NULL,
                    entree INTEGER NOT NULL, sortie INTEGER NOT NULL, cout REAL NOT NULL
                );
            """)

    @contextmanager
    def connexion(self):
        connexion = sqlite3.connect(self.chemin, timeout=5)
        try:
            with connexion:
                yield connexion
        finally:
            connexion.close()

    def lire(self, cle: str):
        with self.connexion() as connexion:
            ligne = connexion.execute(
                "SELECT contenu FROM cache WHERE cle=? AND expiration>?", (cle, time.time())
            ).fetchone()
        if ligne is None:
            return None
        try:
            return json.loads(ligne[0])
        except (ValueError, TypeError):
            return None

    def memoriser(self, cle: str, rapport: Rapport):
        contenu = json.dumps(
            {
                "reponse": rapport.reponse.model_dump(mode="json"),
                "preuve": rapport.preuve.model_dump(mode="json") if rapport.preuve else None,
            },
            ensure_ascii=False,
            allow_nan=False,
        )
        with self.verrou, self.connexion() as connexion:
            connexion.execute("DELETE FROM cache WHERE expiration<=?", (time.time(),))
            connexion.execute(
                "INSERT OR REPLACE INTO cache VALUES (?, ?, ?)",
                (cle, time.time() + self.configuration.cache_ttl_s, contenu),
            )
            connexion.execute(
                "DELETE FROM cache WHERE cle IN (SELECT cle FROM cache ORDER BY expiration DESC LIMIT -1 OFFSET ?)",
                (self.configuration.cache_max,),
            )

    def noter(self, rapport: Rapport, empreinte: str):
        m = rapport.mesures
        with self.connexion() as connexion:
            connexion.execute(
                "INSERT INTO evenements VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    rapport.identifiant,
                    time.time(),
                    empreinte,
                    rapport.reponse.statut,
                    rapport.code,
                    m.route,
                    m.duree_ms,
                    int(m.cache),
                    m.appels_modele,
                    m.jetons_entree,
                    m.jetons_sortie,
                    m.cout_estime_usd,
                ),
            )
            connexion.execute(
                "DELETE FROM evenements WHERE identifiant IN (SELECT identifiant FROM evenements ORDER BY date DESC LIMIT -1 OFFSET 10000)"
            )

    def bilan(self):
        with self.connexion() as connexion:
            total, abstentions, caches, duree, cout, appels = connexion.execute(
                "SELECT COUNT(*), COALESCE(SUM(statut='abstention'),0), COALESCE(SUM(cache),0), "
                "COALESCE(AVG(duree_ms),0), COALESCE(SUM(cout),0), COALESCE(SUM(appels),0) FROM evenements"
            ).fetchone()
            codes = dict(connexion.execute("SELECT code, COUNT(*) FROM evenements GROUP BY code"))
        return {
            "requetes": total,
            "abstentions": abstentions,
            "cache": caches,
            "duree_moyenne_ms": duree,
            "cout_estime_usd": cout,
            "appels_modele": appels,
            "codes": codes,
            "retention_max": 10000,
        }
