# ALLERGO LAB — backend autonome

Ce dossier contient le nouveau harnais scientifique. Il inclut désormais ses données et ses réglages locaux pour être transféré seul sur un autre ordinateur ; voir `DEMARRER_SUR_UN_AUTRE_ORDINATEUR.md`. Il fonctionne indépendamment de l'agent d'équipe : aucun fichier de `equipe/`, `kit/` ou `donnees/` n'est remplacé. Il fournit un moteur Python, une API HTTP, une CLI, un cache persistant, un journal de mesures et une évaluation hors ligne.

Les cinq responsabilités du document de conception sont réparties dans des modules spécialisés. Un modèle facultatif traduit la question en **plan typé** ; Pandas et SciPy calculent ; EVIDENCE contrôle ; des formulations déterministes restituent les résultats. Un seul appel logique au modèle est autorisé par défaut, sans second modèle de vérification ou de synthèse. Les analyses structurées et les quelques formulations directes reconnues ne font aucun appel au modèle.

## Démarrer

Depuis la racine du dépôt :

```console
cd agent
uv sync --frozen
uv run kit agent "Combien de lignes compte le tableau ?"
uv run kit agent "Quelle est la moyenne de Age ?" --detail
uv run allergolab servir
```

L'API démarre sur `http://127.0.0.1:8000` ; documentation interactive sur `/docs` et schéma sur `/openapi.json`. Depuis la racine, la commande équivalente du nouveau moteur est `uv run --project agent kit agent "question"`. La commande `uv run kit agent` à la racine continue d'appeler l'ancien point d'entrée du kit. **Le format exact `uv run kit agent "question"` fonctionne dans le dossier `agent/`.**

Une réponse CLI contient exactement `statut`, `valeur`, `justification`, conformément au contrat du concours. `--detail` ajoute les preuves et mesures dans un rapport ; les mesures sont aussi écrites sur stderr. Une abstention est une sortie valide, avec `valeur: null` ; une erreur interne produit un code de sortie 1.

## Sans modèle : calculs immédiatement disponibles

```console
uv run allergolab catalogue
uv run allergolab analyser '{"operation":"decrire","colonne":"Age","statistique":"mediane"}'
uv run allergolab analyser '{"operation":"compter","filtres":[{"colonne":"Age","operateur":"lt","valeur":30}]}'
uv run allergolab analyser '{"operation":"manquants","limite":10}'
```

Exemple HTTP :

```console
curl -X POST http://127.0.0.1:8000/v1/questions \
  -H 'Content-Type: application/json' \
  -d '{"plan":{"operation":"decrire","colonne":"Age","statistique":"mediane"}}'
```

On peut envoyer `{"question":"Combien de lignes compte le tableau ?"}` à la même route. Fournir une question **ou** un plan, jamais les deux. Les formulations directes sont volontairement limitées : comptage global, âge moyen/médian, statistique descriptive sur un nom exact de colonne, données manquantes. Une formulation non reconnue demande une clarification lorsque le modèle est désactivé.

| Opération | Paramètres principaux | Valeur principale |
| --- | --- | --- |
| `compter` | `filtres` facultatifs | Nombre d'observations, zéro inclus |
| `decrire` | `colonne`, `statistique` | Moyenne, médiane, minimum ou maximum |
| `manquants` | `colonne` facultative, `limite` | Description des cellules vides |
| `frequences` | `colonne`, `limite` | Effectifs des valeurs exactes |
| `proportion` | `colonne`, `seuil`, `comparateur` | Pourcentage ; intervalle de Wilson dans les preuves |
| `comparer` | `colonne` quantitative, `groupe` | P-valeur de Mann–Whitney bilatéral pour deux groupes |
| `correler` | `colonne`, `seconde_colonne` | Rho de Spearman sur paires complètes |
| `abstention` | `motif` | Valeur nulle et explication |

Les filtres sont combinés par ET : `eq`, `ne`, `lt`, `le`, `gt`, `ge`, `in`, `contient`, `manquant`, `present`. Les valeurs des filtres respectent les types du catalogue ; une colonne numérique demande des nombres JSON. `contient` est une recherche littérale, pas une recherche par expression régulière et pas un découpage de codes multivalués.

Les dosages nécessitent une sélection comportant un seul `Chip_Type` renseigné. Consulter le catalogue et le fichier pour connaître les codes réels de puce ; aucun code ou seuil n'est choisi par défaut. Pour une proportion en langage naturel, le seuil numérique doit apparaître explicitement dans la question. Le plan ne démontre pas la pertinence clinique du seuil : celle-ci reste à établir à partir du dictionnaire officiel.

## Activer la compréhension par modèle

Le modèle est **désactivé par défaut**. Les identifiants et les tarifs estimatifs sont lus dans `configuration/modeles.toml`, copié du projet initial, sans les recopier dans le code. Leur validité auprès du fournisseur reste à vérifier avant un usage réel. Seuls le catalogue technique et la question sont transmis au fournisseur ; aucun tableau ni dossier individuel n'est envoyé. Le texte de la question reste sous le contrôle de l'utilisateur.

Fournir dans l'environnement du processus :

```text
ALLERGOLAB_MODELE_ACTIF=true
ALLERGYLAB_CLE=<clé fournisseur>
```

La clé déjà rangée dans `~/.allergylab/cle` par le kit est aussi reconnue. `.env.example` documente les variables ; aucun fichier `.env` n'est chargé implicitement. Redémarrer le serveur après une modification de l'environnement.

Le planificateur utilise `smolagents.ToolCallingAgent` et un outil final qui valide le plan Pydantic. Il n'a ni interpréteur Python, ni outil de fichiers, ni outil réseau. Les calculs utilisent uniquement des méthodes préécrites. Une erreur, un plan invalide ou une tentative supplémentaire au-delà de la limite déclenchent une abstention. La réponse scientifique est construite à partir des calculs, sans reprendre un résultat libre généré par le modèle.

Le module `modele.py` est la seule porte vers le fournisseur. Il borne la sortie, le nombre d'appels, le budget estimatif et le temps d'attente réseau. Seules les erreurs 429/529 sont retentées, deux fois au plus, dans le délai disponible. Une erreur de crédit, d'authentification ou une autre erreur est finale. Le budget est une estimation locale fondée sur les tarifs configurés ; le plafond du compte fournisseur reste la limite financière effective. Aucun appel payant n'est nécessaire aux tests ou à l'évaluation fournie.

## Configuration

| Variable | Valeur par défaut / rôle |
| --- | --- |
| `ALLERGOLAB_DONNEES` | CSV livré dans `donnees/` à l’intérieur du projet |
| `ALLERGOLAB_REGLAGES` | `configuration/modeles.toml`, modèles et tarifs |
| `ALLERGOLAB_METADATA` | JSON facultatif de définitions scientifiques validées |
| `ALLERGOLAB_RUNTIME` | `agent/runtime/`, SQLite local ignoré par Git |
| `ALLERGOLAB_MODELE_ACTIF` | `false` |
| `ALLERGOLAB_CLE_API` | Secret HTTP distinct de la clé du fournisseur |

Les autres limites sont regroupées dans `Configuration` : 20 secondes pour la planification, 1 appel logique, budget estimé de 0,02 USD, 1 400 jetons de sortie, au moins 5 observations par groupe pour les tests, 4 analyses simultanées, 60 requêtes HTTP par minute, 512 entrées de cache et TTL d'une heure. La configuration Python permet de les adapter explicitement.

Le chargement respecte le séparateur `;`, les virgules décimales des dosages et les codes cliniques multivalués laissés en texte. Seules les cellules vides sont manquantes. Les 15 premières colonnes sont considérées cliniques par défaut ; configurer `nombre_cliniques` pour un fichier d'une autre structure. Le CSV et les métadonnées forment un **instantané chargé au démarrage** : redémarrer après remplacement du fichier.

Le catalogue distingue lecture numérique et signification quantitative. Les codes cliniques ne deviennent pas automatiquement des mesures continues. `Age`, `Age_of_onsets` et le bloc dosage sont les candidats quantitatifs par défaut, à condition que leur lecture soit effectivement numérique ; toute autre mesure demande une définition explicite. Aucune unité, signification des codes, définition de sévérité ou seuil clinique n'est inventé. La copie locale du fichier Excel reste à lire et valider par l'équipe ; elle n'est pas interprétée automatiquement et son statut est documenté dans `donnees/README.md`. Voir `configuration/metadata.exemple.json`.

## Page web

L'adresse `/` sert la page de l'équipe 4 : l'Assistant, l'onglet Explorer et la Méthode. Le code se trouve dans `src/allergolab/vitrine/`, branché par `app.py`.

- **Explorer** : les calculs des outils de l'équipe (seuil 0,3, code 9 « non renseigné », minimum de 30 patients testés), sans modèle et sans coût.
- **Assistant** : deux formulations sont calculées comme l'Explorer (« Quel pourcentage des patients testés est sensibilisé à Ara_h_2 ? », « Quels sont les cinq allergènes les plus fréquents parmi les patients testés ? ») ; les autres passent par le moteur. Sans modèle, seules les formulations simples reçoivent une réponse.
- La page publique n'utilise jamais le modèle, sauf si `ALLERGOLAB_PAGE_MODELE=true` est défini en plus de `ALLERGOLAB_MODELE_ACTIF=true`. Les questions sont limitées à 30 par minute et par instance.

En local : `uv run uvicorn app:app --port 8000`, puis ouvrir http://127.0.0.1:8000.

## API pour le frontend

| Route | Usage |
| --- | --- |
| `GET /health` | Disponibilité du processus, sans données de cohorte |
| `GET /v1/catalogue` | Variables, types et définitions disponibles |
| `POST /v1/questions` | Question ou plan → réponse, preuve, mesures et identifiant |
| `GET /v1/metriques` | Latence moyenne, coût estimatif, cache et motifs d'abstention |

L'en-tête `X-API-Key` est obligatoire lorsque `ALLERGOLAB_CLE_API` est défini. Sans clé, l'accès aux routes de données est limité à la machine locale ; la CLI refuse une écoute publique sans clé. Les en-têtes de proxy ne sont pas acceptés par le serveur fourni. Les corps HTTP sont limités à 32 Kio, les questions à 4 000 caractères, les listes de valeurs à 64 éléments et les filtres à 12. Les identifiants individuels sont bloqués dans les outils et masqués dans le catalogue public.

Une abstention scientifique est un HTTP 200 avec son motif ; une entrée invalide donne 422, une surcharge 503, une limite HTTP 429 et une erreur interne 500. Une clé incorrecte donne 401. L'API expose les nombres agrégés d'une cohorte : ces contrôles ne constituent pas une garantie d'anonymisation contre l'inférence à partir de petites sélections.

## Preuves, cache et mesures

Chaque rapport comprend le plan exécuté, l'empreinte de version CSV/métadonnées, la source, la population totale, l'effectif filtré, l'effectif exploitable, les absences, la méthode, les détails numériques, les limites et les contrôles EVIDENCE. EVIDENCE recalcule les effectifs et les principaux dénominateurs, vérifie la cohérence des valeurs et interdit NaN/Infinity. Il ne prouve pas à lui seul la bonne traduction de toute question libre ni toutes les hypothèses d'un test statistique.

Le cache est indexé par l'entrée exacte, la version des données, les métadonnées, la configuration et le contenu du code du moteur. Une entrée est revérifiée avant restitution. Des verrous empêchent les requêtes identiques simultanées d'entraîner plusieurs planifications dans un processus. Un cache touché rapporte zéro jeton et zéro coût pour cette requête.

SQLite conserve au maximum 10 000 événements de télémétrie : identifiant, version des données, statut, code, latence, cache, jetons et coût estimatif. La télémétrie ne conserve pas le texte des questions, les secrets ou les dossiers patients. Le **cache** conserve les réponses agrégées et leurs plans, qui peuvent contenir les critères de sélection ; protéger le dossier `runtime/` comme les données de travail. Les erreurs internes ne publient pas les messages bruts du fournisseur.

## Vérifier et améliorer

```console
uv run pytest -q
uv run ruff check src tests
uv run allergolab evaluer --sortie runtime/evaluation.json
uv run allergolab controle
uv run allergolab metriques
```

L'évaluation utilise une cohorte inventée ; elle couvre les réponses calculées, les absences, les filtres, les comparaisons, les corrélations, les abstentions et le cache. Elle publie les résultats par cas, la latence médiane, le p95 observé, les appels et le coût. Les tests couvrent aussi les contrats, EVIDENCE, les requêtes concurrentes, l'invalidation du cache, le planificateur simulé et l'API. Aucun réseau ni vraie clé requis.

Pour améliorer le produit : ajouter les échecs observés comme cas de régression sur des données synthétiques, compléter le dictionnaire validé, puis comparer qualité, abstention, latence et coût avant de changer les règles ou le modèle. Le moteur n'auto-modifie pas ses méthodes scientifiques en production. Le benchmark hors ligne ne mesure pas les performances d'un modèle réel ; une évaluation séparée avec les questions du concours reste nécessaire.

## Organisation

```text
agent/
  src/allergolab/
    contrats.py       plans et réponses Pydantic
    configuration.py  réglages et chemins internes au projet
    donnees.py        chargement et catalogue
    routage.py        chemins directs et règles de périmètre
    modele.py         planification optionnelle et limites fournisseur
    analyse.py        calculs Pandas/SciPy
    evidence.py       vérification déterministe
    service.py        orchestration commune
    stockage.py       cache et télémétrie SQLite
    api.py            FastAPI
    cli.py            commandes kit et allergolab
    evaluation.py     cohorte fictive et mesure de régression
  tests/
  configuration/      modèles et exemples de métadonnées
  donnees/            CSV et dictionnaire de travail copiés
  DEMARRER_SUR_UN_AUTRE_ORDINATEUR.md
  pyproject.toml
  uv.lock
```

## Portée de cette version

Ce socle fonctionne sur un seul processus avec un instantané de cohorte. SQLite, les verrous et la limite de débit sont adaptés à une démonstration locale ; les limites de débit et la déduplication ne sont pas distribuées entre plusieurs instances. Une mise en production avec plusieurs équipes demandera authentification par utilisateur, séparation des cohortes, stockage partagé, terminaison TLS et exploitation supervisée. Aucun hébergement ni déploiement externe n'est effectué ici.

Les tests sont exploratoires, sans gestion longitudinale, ajustement pour facteurs de confusion ou correction automatique des comparaisons multiples. Spearman ne publie pas de p-valeur asymptotique lorsque l'effectif est inférieur ou égal à 500. Mann–Whitney compare les distributions ; son interprétation ne devient une comparaison de médianes que sous des hypothèses supplémentaires.

Un branchement dans le harnais d'évaluation du kit original reste une étape distincte : son point d'entrée est `equipe.agent.repondre` et sa télémétrie globale est spécifique au kit. Cette version conserve le contrat de réponse mais ne prétend pas écrire les coûts dans le journal global de `kit.modele` ni inclure automatiquement ce nouveau dossier dans les instantanés d'équipe du kit.

Références techniques : [ToolCallingAgent et outils](https://huggingface.co/docs/smolagents/en/reference/agents), [cycle de vie FastAPI](https://fastapi.tiangolo.com/advanced/events/), [Mann–Whitney SciPy](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.mannwhitneyu.html), [limites de Spearman SciPy](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.spearmanr.html).


Les chemins relatifs des variables de fichiers sont résolus par rapport au dossier du projet, pas au répertoire courant du terminal. L’installation sur une autre machine utilise `uv sync --frozen` pour recréer les dépendances adaptées à cette machine.
