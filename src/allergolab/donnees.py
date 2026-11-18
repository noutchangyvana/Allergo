"""Chargement immuable et catalogue technique, sans inférer le sens des codes."""

import hashlib
import io
import json
import unicodedata

import numpy as np
import pandas as pd

from .configuration import Configuration


class Abstention(ValueError):
    def __init__(self, message: str, code: str = "analyse_impossible"):
        super().__init__(message)
        self.code = code


def normaliser(texte: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", texte.casefold()) if not unicodedata.combining(c))


class Depot:
    def __init__(self, configuration: Configuration):
        contenu = configuration.donnees.read_bytes()
        metadata = configuration.metadata.read_bytes() if configuration.metadata else b"{}"
        definitions = json.loads(metadata)
        if not isinstance(definitions, dict):
            raise ValueError("Les métadonnées doivent être un objet JSON indexé par colonne.")
        tableau = pd.read_csv(
            io.BytesIO(contenu),
            sep=";",
            encoding="utf-8-sig",
            dtype=str,
            keep_default_na=False,
            na_values=[""],
        )
        if tableau.columns.duplicated().any() or tableau.empty:
            raise ValueError("Le fichier doit contenir des observations et des noms de colonnes uniques.")
        # pandas renomme silencieusement les doublons : contrôler aussi l'en-tête original.
        import csv

        entete = next(csv.reader(io.StringIO(contenu.decode("utf-8-sig")), delimiter=";"))
        if len(entete) != len(set(entete)):
            raise ValueError("Le fichier contient des noms de colonnes dupliqués.")
        self.catalogue = {}
        for position, nom in enumerate(tableau.columns):
            dosage = position >= configuration.nombre_cliniques
            serie = tableau[nom]
            if dosage:
                tableau[nom] = pd.to_numeric(serie.str.replace(",", ".", regex=False), errors="raise")
            elif not serie.str.contains(r",|[^\W\d_]", regex=True, na=False).any():
                tableau[nom] = pd.to_numeric(serie, errors="raise")
            numerique = pd.api.types.is_numeric_dtype(tableau[nom])
            if numerique and np.isinf(tableau[nom].dropna().to_numpy(dtype=float)).any():
                raise ValueError(f"La colonne {nom} contient une valeur infinie.")
            definition = definitions.get(nom, {})
            if not isinstance(definition, dict):
                raise ValueError(f"La définition de {nom} doit être un objet JSON.")
            self.catalogue[nom] = {
                "colonne": nom,
                "bloc": "dosage" if dosage else "clinique",
                "lecture": "nombre" if numerique else "texte",
                "quantitative": definition.get("quantitative", dosage or nom in {"Age", "Age_of_onsets"})
                is True,
                "description": str(definition.get("description", "Définition scientifique non renseignée"))[
                    :300
                ],
                "unite": definition.get("unite"),
                "codage": definition.get("codage", {}),
                "protegee": nom.casefold() in {"patient_id", "patientid", "id", "identifiant"}
                or definition.get("protegee") is True,
            }
        self._tableau = tableau
        self.configuration = configuration
        self.empreinte = hashlib.sha256(contenu + b"\0" + metadata).hexdigest()
        self.nombre = len(tableau)

    def resoudre(self, nom: str) -> str:
        if nom in self.catalogue:
            return nom
        correspondances = [c for c in self.catalogue if normaliser(c) == normaliser(nom)]
        if len(correspondances) == 1:
            return correspondances[0]
        raise Abstention(
            f"Variable absente ou ambiguë : {nom}. Consulter le catalogue des colonnes.", "variable_absente"
        )

    def verifier_colonne(self, nom: str, quantitative: bool = False) -> str:
        nom = self.resoudre(nom)
        definition = self.catalogue[nom]
        if definition["protegee"]:
            raise Abstention(
                "Les identifiants individuels ne sont pas exposés par les outils.", "identifiant_protege"
            )
        if quantitative and (definition["lecture"] != "nombre" or not definition["quantitative"]):
            raise Abstention(
                f"{nom} n'a pas de définition quantitative validée ; préciser le dictionnaire.",
                "codage_non_valide",
            )
        return nom

    def selectionner(self, filtres):
        masque = pd.Series(True, index=self._tableau.index)
        for filtre in filtres:
            nom = self.verifier_colonne(filtre.colonne)
            serie = self._tableau[nom]
            op, valeur = filtre.operateur, filtre.valeur
            if op in {"eq", "ne", "in"}:
                valeurs = valeur if isinstance(valeur, list) else [valeur]
                numerique = pd.api.types.is_numeric_dtype(serie)
                if any(
                    (numerique and isinstance(v, (str, bool))) or (not numerique and not isinstance(v, str))
                    for v in valeurs
                ):
                    raise Abstention(
                        "Le type de la valeur du filtre ne correspond pas à celui de la colonne.",
                        "filtre_invalide",
                    )
            if op in {"lt", "le", "gt", "ge"}:
                self.verifier_colonne(nom, quantitative=True)
                if isinstance(valeur, (str, bool, list)):
                    raise Abstention("Un filtre numérique demande une valeur numérique.", "filtre_invalide")
            if op in {"eq", "ne", "lt", "le", "gt", "ge"}:
                courant = getattr(serie, op)(valeur) & serie.notna()
            elif op == "in":
                courant = serie.isin(valeur) & serie.notna()
            elif op == "contient":
                if not isinstance(valeur, str):
                    raise Abstention("Le filtre contient demande un texte.", "filtre_invalide")
                # Comparaison littérale : aucune expression régulière venant du modèle.
                courant = serie.astype("string").str.contains(valeur, regex=False, na=False)
            elif op == "manquant":
                courant = serie.isna()
            else:
                courant = serie.notna()
            masque &= courant.fillna(False)
        return self._tableau.loc[masque].copy()
