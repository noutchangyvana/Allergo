"""Ce que les outils de l'équipe partagent : le tableau, chargé une seule fois, et nos règles de lecture.

Ce fichier n'est pas un outil. Les règles ci-dessous sont des choix de l'équipe :
si vous en changez une, changez-la ici, et tous les outils suivent.
"""

import math

from allergolab.vitrine.donnees import charger, colonnes

PUCES = ("ALEX", "ISAC_V1", "ISAC_V2")

# Seuil de positivité d'un dosage : une valeur >= 0,3 compte comme « sensibilisé ».
# C'est le seuil usuel des fabricants (ISU-E pour ISAC, kUA/L pour ALEX).
# Le dictionnaire officiel ne le donne pas : c'est un choix de l'équipe.
SEUIL_POSITIF = 0.3

# Le dictionnaire officiel : 9 = « Non renseigné », « sans objet », « non disponible ».
# Ces colonnes cliniques utilisent ce code ; on ne le compte jamais comme une vraie réponse.
CODE_NON_RENSEIGNE = "9"
COLONNES_AVEC_CODE_9 = (
    "Rural_or_urban_area",
    "Treatment_of_rhinitis",
    "Treatment_of_athsma",
    "Age_of_onsets",
    "Skin_Symptoms",
    "Treatment_of_atopic_dematitis",
)

# En dessous de ce nombre de patients, un pourcentage est trop fragile pour conclure.
MINIMUM_PATIENTS = 30

_cache = {}


def tableau():
    """Le tableau complet, lu une seule fois (le relire à chaque appel d'outil serait lent)."""
    if "tableau" not in _cache:
        _cache["tableau"] = charger()
    return _cache["tableau"]


def dictionnaire():
    """kit/colonnes.csv : bloc, lecture, et puces qui mesurent chaque colonne."""
    if "dictionnaire" not in _cache:
        _cache["dictionnaire"] = colonnes().set_index("colonne")
    return _cache["dictionnaire"]


def utiliser_tableau(autre_tableau, autre_dictionnaire):
    """Pour les tests seulement : fait travailler les outils sur une petite table inventée."""
    _cache["tableau"] = autre_tableau
    _cache["dictionnaire"] = autre_dictionnaire.set_index("colonne")


def verifier_colonne(nom, bloc=None):
    """Lève une erreur claire si la colonne n'existe pas (ou n'est pas du bon bloc)."""
    d = dictionnaire()
    if nom not in d.index:
        raise ValueError(f"La colonne {nom!r} n'existe pas. Utilise chercher_colonnes pour trouver le bon nom.")
    if bloc and d.loc[nom, "bloc"] != bloc:
        raise ValueError(f"La colonne {nom!r} est du bloc {d.loc[nom, 'bloc']}, pas du bloc {bloc}.")


def patients(puce=None):
    """Les lignes du tableau, toutes ou celles d'une seule puce."""
    t = tableau()
    if puce is None:
        return t
    if puce not in PUCES:
        raise ValueError(f"Puce inconnue : {puce!r}. Les puces sont : {', '.join(PUCES)}.")
    return t[t["Chip_Type"] == puce]


def puces_qui_mesurent(nom):
    """Les puces pour lesquelles la colonne est renseignée."""
    ligne = dictionnaire().loc[nom]
    return [p for p in PUCES if bool(ligne.get(f"puce_{p}", False))]


def lire_dosage(serie):
    """Sépare un dosage en trois : mesures valides, valeurs vides (non testé), valeurs négatives (invalides)."""
    vides = serie.isna()
    invalides = serie < 0  # quelques cellules valent -1 : ce n'est pas une mesure
    valides = serie[~vides & ~invalides]
    return valides, int(vides.sum()), int(invalides.sum())


def codes(serie):
    """Les codes d'une colonne clinique en texte, une ligne par code : « 1, 3 » donne 1 et 3."""
    texte = serie.dropna().astype(str).str.replace(".0", "", regex=False)
    return texte.str.split(",").explode().str.strip()


def pourcentage(partie, total):
    """Un pourcentage arrondi à une décimale ; None si le total est nul (on ne divise pas par zéro)."""
    return round(100 * partie / total, 1) if total else None


def intervalle_wilson(partie, total):
    """L'intervalle de confiance à 95 % d'un pourcentage (méthode de Wilson), en [bas, haut] ; None si total nul.

    Pourquoi : 16 % sur 50 patients et 16 % sur 4 000 ne pèsent pas pareil. L'intervalle le montre.
    Wilson reste juste près de 0 % et de 100 %, là où la formule « p ± 1,96 × erreur » déraille.
    """
    if not total:
        return None
    z, p = 1.959963984540054, partie / total
    centre = (p + z * z / (2 * total)) / (1 + z * z / total)
    marge = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / (1 + z * z / total)
    return [round(max(0.0, 100 * (centre - marge)), 1), round(min(100.0, 100 * (centre + marge)), 1)]
