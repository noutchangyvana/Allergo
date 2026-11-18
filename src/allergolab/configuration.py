"""Configuration locale ; pas de secret conservé dans les objets de réglage."""

import os
from dataclasses import dataclass
from pathlib import Path

DOSSIER = Path(__file__).resolve().parents[2]
NOM_DONNEES = "allergenchipchallenge-data-corrected-final-hdh-sfa.csv"


@dataclass(frozen=True)
class Configuration:
    donnees: Path = DOSSIER / "donnees" / NOM_DONNEES
    runtime: Path = DOSSIER / "runtime"
    reglages: Path = DOSSIER / "configuration" / "modeles.toml"
    metadata: Path | None = None
    nombre_cliniques: int = 15
    modele_actif: bool = False
    modele: str = "developpement"
    delai_modele_s: float = 20
    budget_usd: float = 0.02
    jetons_sortie_max: int = 1400
    appels_max: int = 1
    effectif_min: int = 5
    cache_max: int = 512
    cache_ttl_s: int = 3600
    requetes_minute: int = 60
    analyses_simultanees: int = 4
    provenance: str = "Allergen Chip Challenge — cohorte locale"

    def __post_init__(self):
        if (
            min(
                self.effectif_min,
                self.cache_max,
                self.cache_ttl_s,
                self.requetes_minute,
                self.analyses_simultanees,
                self.jetons_sortie_max,
                self.appels_max,
            )
            < 1
        ):
            raise ValueError("Les limites doivent être strictement positives.")
        if self.delai_modele_s <= 0 or self.budget_usd <= 0 or self.nombre_cliniques < 0:
            raise ValueError("Délais, budget ou nombre de colonnes cliniques invalides.")

    @classmethod
    def environnement(cls):
        valeurs = {}
        for champ in ("donnees", "runtime", "reglages", "metadata"):
            if valeur := os.getenv(f"ALLERGOLAB_{champ.upper()}"):
                chemin = Path(valeur).expanduser()
                # Un chemin relatif reste lié au projet, même lancé depuis un autre dossier.
                valeurs[champ] = (chemin if chemin.is_absolute() else DOSSIER / chemin).resolve()
        valeurs["modele_actif"] = os.getenv("ALLERGOLAB_MODELE_ACTIF", "false").lower() == "true"
        return cls(**valeurs)
