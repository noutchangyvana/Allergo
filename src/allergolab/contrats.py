"""Contrats fermés : le modèle propose un plan, jamais du code exécutable."""

from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictBool,
    StrictFloat,
    StrictInt,
    StrictStr,
    model_validator,
)

Scalaire = StrictStr | StrictInt | StrictFloat | StrictBool
Nombre = StrictInt | StrictFloat


class Contrat(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class Filtre(Contrat):
    colonne: str = Field(min_length=1, max_length=160)
    operateur: Literal["eq", "ne", "lt", "le", "gt", "ge", "in", "contient", "manquant", "present"]
    valeur: Scalaire | Annotated[list[Scalaire], Field(max_length=64)] | None = None

    @model_validator(mode="after")
    def verifier_valeur(self):
        if self.operateur in {"manquant", "present"}:
            if self.valeur is not None:
                raise ValueError("Un filtre de présence ne prend pas de valeur.")
        elif self.valeur is None:
            raise ValueError("Le filtre demande une valeur explicite.")
        elif (self.operateur == "in") != isinstance(self.valeur, list):
            raise ValueError("Seul le filtre in prend une liste de valeurs.")
        return self


class Plan(Contrat):
    operation: Literal[
        "compter", "decrire", "manquants", "frequences", "proportion", "comparer", "correler", "abstention"
    ]
    colonne: str | None = Field(default=None, max_length=160)
    seconde_colonne: str | None = Field(default=None, max_length=160)
    groupe: str | None = Field(default=None, max_length=160)
    filtres: list[Filtre] = Field(default_factory=list, max_length=12)
    seuil: Nombre | None = None
    comparateur: Literal["ge", "gt", "eq"] = "ge"
    statistique: Literal["moyenne", "mediane", "minimum", "maximum"] = "moyenne"
    limite: int = Field(default=20, ge=1, le=25, strict=True)
    motif: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def verifier_plan(self):
        if (
            self.operation in {"decrire", "frequences", "proportion", "comparer", "correler"}
            and not self.colonne
        ):
            raise ValueError("Cette analyse demande une colonne explicite.")
        if self.operation == "proportion" and self.seuil is None:
            raise ValueError("Une proportion demande un seuil explicite, sans valeur implicite.")
        if self.operation == "comparer" and not self.groupe:
            raise ValueError("Une comparaison demande une colonne de groupe.")
        if self.operation == "correler" and not self.seconde_colonne:
            raise ValueError("Une corrélation demande deux colonnes.")
        if self.operation == "abstention" and not self.motif:
            raise ValueError("Une abstention demande un motif.")
        if self.operation not in {"comparer"} and self.groupe is not None:
            raise ValueError("Le groupe n'est utilisable que pour comparer.")
        if self.operation != "correler" and self.seconde_colonne is not None:
            raise ValueError("La seconde colonne n'est utilisable que pour corréler.")
        if self.operation != "proportion" and self.seuil is not None:
            raise ValueError("Le seuil n'est utilisable que pour une proportion.")
        if self.operation == "compter" and self.colonne is not None:
            raise ValueError(
                "Compter porte sur des observations ; utiliser un filtre de présence pour une colonne."
            )
        if self.operation == "abstention" and (self.colonne or self.filtres):
            raise ValueError("Une abstention n'exécute aucun filtre ni calcul.")
        return self


class Reponse(Contrat):
    statut: Literal["reponse", "abstention"]
    valeur: Nombre | str | None
    justification: str = Field(min_length=1)

    @model_validator(mode="after")
    def verifier_statut(self):
        if self.statut == "abstention" and self.valeur is not None:
            raise ValueError("Une abstention a une valeur nulle.")
        if self.statut == "reponse" and (self.valeur is None or self.valeur == ""):
            raise ValueError("Une réponse doit contenir une valeur.")
        return self


class Preuve(Contrat):
    source: str
    empreinte: str
    plan: Plan
    methode: str
    population: int = Field(ge=0)
    selection: int = Field(ge=0)
    exploitables: int = Field(ge=0)
    manquants: int = Field(ge=0)
    details: dict = Field(default_factory=dict)
    limites: list[str] = Field(default_factory=list)
    controles: list[str] = Field(default_factory=list)


class Mesures(Contrat):
    duree_ms: float = Field(default=0, ge=0)
    cache: bool = False
    appels_modele: int = 0
    jetons_entree: int = 0
    jetons_sortie: int = 0
    cout_estime_usd: float = 0
    route: Literal["directe", "structuree", "modele", "abstention"] = "structuree"


class Rapport(Contrat):
    identifiant: str
    reponse: Reponse
    preuve: Preuve | None = None
    mesures: Mesures = Field(default_factory=Mesures)
    code: str = "ok"


class Demande(Contrat):
    question: str | None = Field(default=None, min_length=1, max_length=4000)
    plan: Plan | None = None

    @model_validator(mode="after")
    def une_entree(self):
        if (self.question is None) == (self.plan is None):
            raise ValueError("Fournir une question ou un plan, un seul des deux.")
        if self.question is not None and not self.question.strip():
            raise ValueError("La question ne peut pas être vide.")
        return self
