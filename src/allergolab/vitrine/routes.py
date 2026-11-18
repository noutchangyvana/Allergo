"""Les adresses de la page : la page elle-même, l'onglet Explorer et les questions de l'Assistant.

Une question passe d'abord par deux formulations que l'Explorer sait calculer (prévalence
d'un allergène, classement des plus fréquents), puis par le moteur (routage, EVIDENCE).
Rien ne fait appel au modèle tant que le moteur ne l'active pas ; même activé, la page
publique ne l'utilise que si ALLERGOLAB_PAGE_MODELE=true, car chaque question coûterait.
"""

import json
import os
import re
import threading
import time
from collections import deque
from pathlib import Path
from urllib.parse import urlsplit

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from pydantic import ValidationError

from allergolab.contrats import Demande
from allergolab.donnees import normaliser
from allergolab.vitrine import analyses, commun, explorer

FICHIERS = Path(__file__).resolve().parent / "fichiers"
PAGE = FICHIERS / "page_interface.html"
VERSION_SCHEMA = "2"
QUESTIONS_PAR_MINUTE = 30

NOMBRES = {
    "trois": 3, "quatre": 4, "cinq": 5, "six": 6, "sept": 7, "huit": 8, "neuf": 9, "dix": 10,
    "quinze": 15, "vingt": 20,
}
PREVALENCE = re.compile(r"quel pourcentage des patients testes est sensibilise a ([\w.\-]+) \?")
CLASSEMENT = re.compile(r"quels sont les (\w+) allergenes les plus frequents parmi les patients testes \?")


def resultat(etat, valeur, texte, debut, source, analyse=None, etapes=None, cout=0.0):
    """La forme que la page attend : etat, valeur, texte, mesures, etapes, cout, analyse."""
    duree = f"{(time.perf_counter() - debut) * 1000:.0f} ms"
    return {
        "version_schema": VERSION_SCHEMA, "etat": etat, "valeur": valeur, "texte": texte,
        "mesures": [source, duree], "etapes": etapes or [], "cout": cout, "analyse": analyse,
    }


def code_dosage(texte):
    """Le nom exact d'une colonne de dosage écrite sans tenir compte de la casse, ou None."""
    d = commun.dictionnaire()
    trouves = [c for c in d.index[d["bloc"] == "dosage"] if c.casefold() == texte.casefold()]
    return trouves[0] if len(trouves) == 1 else None


def par_explorer(question, debut):
    """Les deux questions calculées comme l'Explorer, avec les règles de l'équipe ; None sinon."""
    texte = " ".join(normaliser(question).split()).replace(" ?", "?").replace("?", " ?")
    trouve = PREVALENCE.fullmatch(texte)
    if trouve and (code := code_dosage(trouve.group(1))):
        r = analyses.prevalence(code)
        ligne = r["ligne"]
        if ligne["patients_testes"] < commun.MINIMUM_PATIENTS:
            return resultat("abstention", None, f"{code} n'est testé que chez {ligne['patients_testes']} patients : "
                            f"moins de {commun.MINIMUM_PATIENTS}, le pourcentage serait trop fragile.", debut, "Calcul de l'Explorer")
        bas, haut = ligne["intervalle_confiance_95"]
        texte = (f"{ligne['patients_positifs']} patients sur {ligne['patients_testes']} testés pour {code} ont un dosage "
                 f"≥ {commun.SEUIL_POSITIF} (toutes puces), soit {ligne['pourcentage']} % (IC 95 % : de {bas} à {haut} %).")
        return resultat("reponse", ligne["pourcentage"], texte, debut, "Calcul de l'Explorer", analyse=r)
    trouve = CLASSEMENT.fullmatch(texte)
    if trouve:
        mot = trouve.group(1)
        nombre = NOMBRES.get(mot) or (int(mot) if mot.isdigit() else None)
        if nombre:
            r = analyses.classement(nombre=nombre)
            if not r["lignes"]:
                return resultat("abstention", None, "Aucun allergène n'atteint le minimum de patients testés.", debut, "Calcul de l'Explorer")
            codes = [x["code"] for x in r["lignes"]]
            texte = (f"Classement par pourcentage de patients sensibilisés (dosage ≥ {commun.SEUIL_POSITIF}) parmi les testés, "
                     f"sur les {r['nombre_eligibles']} allergènes testés chez au moins {commun.MINIMUM_PATIENTS} patients.")
            return resultat("reponse", ", ".join(codes), texte, debut, "Calcul de l'Explorer", analyse=r)
    return None


def par_moteur(service, question, debut):
    """Toute autre question : le moteur (routage, plan, calcul, EVIDENCE), sans texte libre du modèle."""
    rapport = service.traiter(Demande(question=question))
    m, reponse = rapport.mesures, rapport.reponse
    etapes = []
    if rapport.preuve is not None:
        etapes.append({
            "code": json.dumps(rapport.preuve.plan.model_dump(mode="json", exclude_defaults=True), ensure_ascii=False),
            "resultat": json.dumps({"methode": rapport.preuve.methode, "details": rapport.preuve.details,
                                    "controles": rapport.preuve.controles}, ensure_ascii=False, default=str)[:2000],
        })
    etat = "erreur" if rapport.code in {"erreur_interne", "surcharge"} else reponse.statut
    source = f"Moteur ({m.route}, {m.appels_modele} appel(s) au modèle{', cache' if m.cache else ''})"
    return resultat(etat, reponse.valeur, reponse.justification, debut, source, etapes=etapes, cout=m.cout_estime_usd)


def ajouter_page(application: FastAPI, service):
    """Ajoute à l'API les adresses de la page. Le service est celui du moteur, déjà prêt."""
    passages, verrou = deque(), threading.Lock()

    def trop_de_questions():
        with verrou:
            maintenant = time.monotonic()
            while passages and passages[0] <= maintenant - 60:
                passages.popleft()
            if len(passages) >= QUESTIONS_PAR_MINUTE:
                return True
            passages.append(maintenant)
            return False

    @application.get("/", include_in_schema=False)
    def page():
        return HTMLResponse(PAGE.read_text(encoding="utf-8"))

    @application.get("/fond_paysage.jpg", include_in_schema=False)
    def fond():
        return FileResponse(FICHIERS / "fond_paysage.jpg", media_type="image/jpeg")

    @application.get("/avatar/cumulus.avatar.json", include_in_schema=False)
    def avatar():
        return FileResponse(FICHIERS / "cumulus.avatar.json", media_type="application/json")

    @application.get("/colonnes", tags=["page"])
    def liste_colonnes():
        """Les noms de colonnes par bloc et la nomenclature des allergènes : aucune donnée de patient."""
        d = commun.dictionnaire()
        corps = {bloc: d.index[d["bloc"] == bloc].tolist() for bloc in ("dosage", "clinique")}
        return dict(corps, noms=explorer.noms())

    vues = {
        "resume": lambda p: explorer.resume(),
        "classement": lambda p: explorer.classement(p.get("puce") or None),
        "allergene": lambda p: explorer.fiche_allergene(p["code"]),
        "clinique": lambda p: explorer.clinique(p["colonne"], p.get("puce") or None),
    }

    @application.get("/explorer/{vue}", tags=["page"])
    def vue_explorer(vue: str, request: Request):
        """L'onglet Explorer : les calculs de l'équipe, sans modèle et sans coût."""
        if vue not in vues:
            return JSONResponse({"erreur": "Vue inconnue."}, status_code=404)
        try:
            return vues[vue](dict(request.query_params))
        except (ValueError, KeyError) as erreur:
            return JSONResponse({"erreur": str(erreur).strip("'\"")}, status_code=400)

    @application.post("/question", tags=["page"])
    async def question(request: Request):
        """Une question de l'Assistant, au format de la page."""
        debut = time.perf_counter()
        origine = request.headers.get("origin")
        if origine and urlsplit(origine).netloc != request.headers.get("host"):
            return JSONResponse({"erreur": "Origine refusée."}, status_code=403)
        if trop_de_questions():
            return resultat("erreur", None, "Trop de questions en une minute : réessaie dans un instant.", debut, "Limite")
        try:
            texte = str((await request.json()).get("question", "")).strip()
        except (ValueError, AttributeError):
            texte = ""
        if not texte:
            return resultat("erreur", None, "La question est vide.", debut, "Page")
        if len(texte) > 4000:
            return resultat("erreur", None, "La question est trop longue (4 000 caractères au plus).", debut, "Page")
        if service.configuration.modele_actif and os.getenv("ALLERGOLAB_PAGE_MODELE", "").lower() != "true":
            return resultat("erreur", None, "Le modèle est activé sur ce serveur, mais pas pour la page publique : "
                            "définir ALLERGOLAB_PAGE_MODELE=true pour l'autoriser, en sachant que chaque question coûte.",
                            debut, "Page")
        try:
            return par_explorer(texte, debut) or par_moteur(service, texte, debut)
        except ValidationError:
            return resultat("erreur", None, "La question n'a pas pu être lue.", debut, "Page")
