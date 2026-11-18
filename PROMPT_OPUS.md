# Prompt de reprise pour Opus 5.5

Tu reprends le développement d'ALLERGO LAB, un assistant de recherche en allergologie. Je te fournis **uniquement le dossier `agent/`**. Il contient désormais le CSV de travail sous `donnees/`, une copie locale du dictionnaire et les réglages sous `configuration/modeles.toml`. Tu n'as pas accès à l'ancien agent, au dépôt complet ou au dossier `kit/`. Le statut de la copie du dictionnaire est documenté dans `donnees/README.md` : ne la présente pas comme une copie certifiée du fichier officiel.

Ton objectif est de comprendre le backend existant, d'en expliquer le fonctionnement, puis de le finaliser comme moteur scientifique portable, fiable, rapide et économe. Travaille sur le code fourni, conserve ce qui fonctionne et vérifie les améliorations. Le périmètre est la partie agent et son API ; aucune interface graphique n'est demandée.

Le nom Opus 5.5 désigne ici le modèle auquel je confie cette reprise de développement. Il ne constitue pas une instruction de remplacer le modèle utilisé par l'application ni une preuve de son identifiant API ou de son tarif.

## 1. Produit attendu

ALLERGO LAB permet à un chercheur de poser des questions sur une cohorte : effectifs, distributions, données manquantes, proportions, comparaisons et associations entre variables.

Les principes sont les suivants :

- Les nombres viennent des données et des fonctions Python, jamais d'une estimation du modèle.
- Le modèle traduit une demande en plan d'analyse ; il ne génère pas de code à exécuter.
- Les analyses utilisent des méthodes prédéfinies, vérifiées et documentées.
- Le système doit expliquer pourquoi il peut répondre ou pourquoi il s'abstient.
- Les unités, seuils et codes cliniques doivent avoir une définition vérifiée.
- Une association ne démontre pas une causalité et une sensibilisation ne suffit pas à conclure à une allergie clinique.
- Les appels au modèle sont limités et mesurés ; les demandes simples doivent pouvoir éviter ces appels.

Les cinq responsabilités imaginées pour le produit sont l'orchestrateur, l'explorateur, l'analyste scientifique, EVIDENCE et le synthétiseur. Elles sont actuellement réparties entre des modules Python et un planificateur facultatif. Il n'y a pas cinq modèles indépendants qui dialoguent à chaque question.

## 2. Architecture effectivement fournie

Le projet utilise Python 3.12, `uv`, Pandas, SciPy, Pydantic via les dépendances installées, FastAPI, Uvicorn, SQLite et `smolagents[litellm]==1.26.0`. Les dépendances sont verrouillées dans `uv.lock`. Les tests utilisent pytest et HTTPX ; Ruff contrôle le code.

Lis au minimum `README.md`, `VALIDATION.md`, `pyproject.toml`, puis les sources et les tests. Les rôles des fichiers dans `src/allergolab/` sont :

| Fichier | Responsabilité actuelle |
| --- | --- |
| `contrats.py` | Schémas fermés des demandes, filtres, plans, réponses, preuves et mesures |
| `configuration.py` | Chemins, activation du modèle et limites de fonctionnement |
| `donnees.py` | Chargement du CSV, catalogue technique, validation des colonnes et application des filtres |
| `routage.py` | Reconnaissance limitée de questions simples et règles d'abstention précoce |
| `modele.py` | Unique porte vers le fournisseur ; planification par ToolCallingAgent et limites d'appels |
| `analyse.py` | Calculs scientifiques prédéfinis avec Pandas/SciPy |
| `evidence.py` | Vérification des effectifs, dénominateurs et résultats publiés |
| `service.py` | Orchestration commune à la CLI et à l'API |
| `stockage.py` | Cache SQLite et télémétrie locale |
| `api.py` | API HTTP, clé d'accès facultative en local, limites de corps et de débit |
| `cli.py` | Commandes `kit` et `allergolab` |
| `evaluation.py` | Cohorte fictive, scénarios de régression et mesures |

Le dossier `tests/` contient les tests scientifiques, du harnais, de l'API et du planificateur simulé. `configuration/metadata.exemple.json` est un exemple de métadonnées, pas le dictionnaire scientifique officiel.

## 3. Déroulement d'une demande

Une demande contient une question en texte ou un plan JSON structuré, un seul des deux.

1. Pydantic valide sa structure et ses limites.
2. Le service vérifie la capacité disponible et les règles de périmètre.
3. Il cherche un résultat dans le cache, indexé par l'entrée, les données, les métadonnées, la configuration et le code du moteur.
4. Une entrée de cache est contrôlée par EVIDENCE avant restitution. Cette vérification peut refaire des calculs : le gain garanti par conception concerne surtout l'évitement d'une nouvelle planification, pas la suppression de tout calcul statistique.
5. Sans cache, un plan structuré est directement utilisé. Une question simple reconnue produit un plan sans modèle.
6. Pour une autre formulation, le modèle doit être activé. Il reçoit la question et le catalogue, puis propose un plan typé par l'outil `final_answer`. Les lignes du tableau ne lui sont pas transmises. Le contenu de la question reste toutefois fourni par l'utilisateur.
7. Le moteur vérifie les variables, types, filtres et préconditions, puis exécute une méthode prédéfinie.
8. EVIDENCE contrôle la cohérence des résultats avec les données.
9. Une réponse déterministe est construite à partir des résultats validés, avec les preuves et limites disponibles.
10. La réponse est mise en cache et les mesures sont enregistrées. Une erreur ou une analyse injustifiée entraîne une abstention explicite.

Le contrat de réponse court est exactement :

```json
{
  "statut": "reponse",
  "valeur": 42,
  "justification": "Une à trois phrases expliquant le résultat calculé."
}
```

La valeur ci-dessus illustre le format et ne correspond pas à la cohorte. En cas d'abstention, `statut` vaut `abstention` et `valeur` vaut `null`. Le rapport détaillé contient aussi l'identifiant de requête, les preuves, les mesures et un code de résultat.

Les opérations actuelles sont `compter`, `decrire`, `manquants`, `frequences`, `proportion`, `comparer`, `correler` et `abstention`. Les filtres sont combinés par ET. La comparaison disponible est Mann–Whitney pour deux groupes ; la corrélation est Spearman ; les proportions ont un intervalle de Wilson. Les cellules multivaluées sont conservées telles quelles.

## 4. État réel et limites

Il s'agit d'un socle implémenté et testé, pas d'un produit scientifiquement finalisé.

Lors de la dernière validation, 62 tests et 12 scénarios fictifs passaient, y compris après extraction dans un nouveau dossier et reconstruction de l'environnement Python. Aucun appel payant n'a été effectué pour cette validation. Relance les tests dans ton environnement avant d'annoncer tes résultats. Les latences consignées dans `VALIDATION.md` concernent des calculs locaux sur données fictives, hors démarrage ; elles ne mesurent ni le modèle réel ni une amélioration par rapport à l'ancien agent.

Le modèle est désactivé par défaut. Le routage sans modèle reconnaît seulement quelques formulations. La qualité de traduction de questions libres n'a pas été validée avec un fournisseur réel. Un plan JSON valide peut encore mal représenter l'intention du chercheur ; les contrôles numériques ne suffisent pas à détecter toutes ces erreurs.

Une correction de portabilité a été réalisée après la version initiale : les chemins par défaut du CSV et des réglages sont maintenant internes au projet. Les fichiers nécessaires ont été copiés à l'identique dans le dossier transmis ; aucune dépendance au dossier `kit/` voisin n'est requise. Les chemins relatifs configurés se résolvent par rapport au projet. Vérifie le fonctionnement après extraction dans un nouveau dossier et reconstruction de `.venv` avec `uv sync --frozen`. La lecture éventuelle de `~/.allergylab/cle` est un mécanisme de compatibilité, pas un prérequis ; aucune clé n'est incluse.

Le dictionnaire officiel n'est pas interprété automatiquement. Le catalogue actuel contient surtout des informations techniques. Certains paramètres, dont les 15 premières colonnes cliniques, proviennent du format initial et doivent devenir explicites pour un autre fichier. Les unités et codages ne sont pas scientifiquement validés par le simple chargement du CSV.

La gestion des méthodes est limitée : pas de correction automatique des comparaisons multiples, d'ajustement pour facteurs de confusion, d'analyse longitudinale ou de plan composé d'une suite d'analyses. Le minimum d'effectif configuré est une règle pratique, pas une garantie universelle de puissance statistique.

L'application utilise un seul processus et un instantané de cohorte chargé au démarrage. Les verrous, la déduplication et la limite de débit ne sont pas distribués. L'authentification par utilisateur, les droits sur plusieurs cohortes et l'exploitation de production restent à concevoir si ce périmètre devient nécessaire. Les agrégats sur de petits groupes ne constituent pas à eux seuls une anonymisation.

La compatibilité actuelle avec le concours porte sur le contrat de réponse et la commande lancée dans ce projet. L'intégration aux traces, coûts et instantanés du kit original reste distincte et ne peut pas être certifiée sans ce kit.

## 5. Travail demandé pour finaliser, dans cet ordre

**A. Auditer l'existant.** Relance les tests disponibles, explique les défauts concrets et distingue ce qui est implémenté, simulé ou dépendant d'un fichier absent. Corrige les problèmes identifiés avant d'étendre le périmètre.

**B. Consolider la portabilité.** Vérifie la correction déjà implémentée et conserve l’absence de dépendance obligatoire à la disposition du dépôt d’origine. Prévois une configuration locale documentée pour les chemins, le fournisseur, le modèle et les tarifs, sans inventer d'identifiant API. Déclare explicitement les dépendances importées directement. Fournis une démonstration autonome avec la cohorte fictive déjà présente. Un dossier fraîchement copié doit pouvoir exécuter ses tests et sa démo sans `../kit/` ni `../donnees/`. L'absence de données réelles doit produire un message utile, sans données de remplacement présentées comme réelles.

**C. Compléter le contrat scientifique des données.** Prépare un schéma validé de dictionnaire : types sémantiques, unités, codes autorisés, valeurs multiples, absences, rôle des identifiants et disponibilité par puce. Rends explicites les hypothèses de chargement. Prévois comment importer et valider le dictionnaire officiel lorsqu'il sera fourni ; en attendant, utilise uniquement des exemples fictifs clairement identifiés.

**D. Fiabiliser la compréhension.** Mesure la traduction question → plan, notamment pour les filtres, négations, comparateurs, dénominateurs, unités, groupes et seuils. Élargis les formulations directes lorsque cela est justifié par des cas de test. Refuse ou demande une précision pour les contraintes impossibles à représenter. Si tu ajoutes une clarification, documente son état et son contrat ; ne prétends pas qu'un historique conversationnel existe déjà.

**E. Renforcer les méthodes et EVIDENCE.** Vérifie les préconditions, les effectifs exploitables, la gestion des absences et la correspondance entre demande, plan et conclusion. Ajoute des méthodes seulement si elles répondent à un besoin défini et peuvent être testées. Ne choisis pas un test uniquement parce qu'il produit une p-valeur. Conserve la distinction entre résultat descriptif, association exploratoire et conclusion causale.

**F. Mesurer les performances et coûts.** Sépare démarrage, planification, calcul, vérification et restitution. Compare cache actif/inactif et questions simples/complexes avec des mesures reproductibles. Vérifie les limites de temps, de reprises et de budget, y compris dans les couches du fournisseur. Optimise seulement après mesure. N'active pas de dépenses supplémentaires sur la seule base de ce prompt ; prépare une validation avec le fournisseur réel et précise ce qui n'a pas été testé.

**G. Finaliser l'API et la documentation.** Conserve un moteur commun à la CLI et à l'API, des erreurs exploitables et des sorties stables. Documente ce qui est prêt pour une démonstration locale et ce qui manque pour un service en production. Prépare un adaptateur d'intégration au kit si pertinent, mais n'annonce pas sa compatibilité complète sans le kit.

**H. Organiser l'amélioration continue.** Ajoute les échecs reproductibles comme régressions sur données synthétiques. Compare exactitude, abstentions justifiées et injustifiées, latence et coût avant chaque modification. Aucune auto-modification des méthodes scientifiques en production. Les résultats scientifiques réels nécessiteront les données et définitions réelles.

## 6. Commandes initiales et critères de fin

Depuis la racine du projet fourni, celle qui contient `pyproject.toml` :

```console
uv sync --frozen
uv run pytest -q
uv run ruff check src tests
uv run ruff format --check src tests
uv run allergolab evaluer
```

Le CSV fourni doit permettre le contrôle et une question simple sans configuration supplémentaire. Si un autre transfert omet ce CSV, l'absence doit produire une erreur utile et ne doit pas bloquer les travaux sur données synthétiques. Continue les travaux indépendants avec les fixtures synthétiques.

Le livrable doit inclure :

1. Une explication claire du fonctionnement réel et de l'organisation finale.
2. Les corrections et améliorations implémentées, avec leur raison.
3. Une installation et une démonstration reproductibles depuis le seul dossier fourni.
4. Les commandes de vérification et leurs résultats effectivement obtenus.
5. Une évaluation distinguant calculs, compréhension du langage, abstention, latence et coût.
6. Une liste courte des éléments restant dépendants du CSV réel, du dictionnaire officiel, du fournisseur ou du kit d'évaluation.

Commence par inspecter le code, puis réalise les améliorations possibles. Ne t'arrête pas à une proposition d'architecture et ne présente jamais une fonctionnalité prévue comme déjà opérationnelle.
