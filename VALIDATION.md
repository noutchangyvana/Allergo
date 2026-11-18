# Validation du backend autonome

Les tests du nouveau backend utilisent exclusivement une cohorte fictive. Les appels au fournisseur sont simulés et le réseau externe est interdit pendant les tests. Aucun appel payant n'a été exécuté pour cette validation.

Résultats obtenus :

- `pytest -q` : **62 passed** en 1,95 seconde sur cette machine après correction de la portabilité.
- `ruff check src tests` : **All checks passed!**
- `ruff format src tests` : **20 files left unchanged**.
- Évaluation : **12 scénarios sur 12 réussis**, cache vérifié, zéro appel au modèle.
- `allergolab controle` : **RÉUSSITE**, chargement du CSV et évaluation fictive validés.
- `kit agent "Combien de lignes compte le tableau ?"` dans `agent/` : réponse au contrat valide, code de sortie 0, aucun appel au modèle.

Sur cette exécution locale de l'évaluation fictive, la médiane des requêtes était de 1,33 ms et le p95 observé de 3,27 ms, hors import des bibliothèques et démarrage. Ces nombres ne préjugent pas des temps d'une question libre avec fournisseur distant, ni d'un gain par rapport à l'agent précédent qui n'était pas disponible.

Commandes à lancer depuis `agent/` :

```console
uv run pytest -q
uv run ruff check src tests
uv run ruff format --check src tests
uv run allergolab evaluer
uv run allergolab controle
```

Le contrôle du nouveau backend vérifie que son CSV se charge et que ses scénarios scientifiques fictifs passent. Il ne certifie ni les définitions cliniques du dictionnaire Excel, ni les performances d'un modèle réel.

Le kit d'origine a également été testé sans modifier son code : **115 tests passent et 8 échouent**. Ces huit échecs viennent du dictionnaire `donnees/acc-dictionnaire-final.xls`, déjà modifié avant cette intervention, dont l'empreinte diffère de celle publiée dans `kit/empreintes.toml`. La commande `uv run kit controle --hors-ligne` à la racine échoue pour la même raison ; les autres points du contrôle passent. Le fichier Excel a été conservé tel quel.

Tous les nouveaux fichiers applicatifs, tests, dépendances verrouillées et documentation sont contenus dans `agent/`. Les anciens points d'entrée et les modifications préexistantes ont été conservés. Les commandes `kit` du nouveau projet se lancent dans `agent/`, ou via `uv run --project agent kit ...` depuis la racine.

## Vérification du transfert

Les fichiers de données et les réglages ont été copiés à l'identique dans le projet. Les chemins par défaut sont internes à `agent/` et les chemins relatifs configurés sont indépendants du dossier courant.

Une archive sans `.venv` ni caches Python a été extraite sous un autre chemin contenant des espaces, sans dossier `kit/` ou `donnees/` voisin. Un environnement Python neuf y a été créé par `uv sync --frozen --offline` à partir du cache de paquets de la machine. Résultats :

- Installation : réussite.
- Question au format `kit agent`, lancée depuis un dossier extérieur au projet : réponse correcte au contrat, code 0.
- Suite de tests dans le dossier extrait : **62 passed** en 6,86 secondes.
- Évaluation dans le dossier extrait : **12 scénarios sur 12 réussis**.

L'archive finale conserve le code testé et contient également cette documentation mise à jour. Son intégrité est vérifiée fichier par fichier. Le test porte sur un changement de dossier et d'environnement sur la machine actuelle, pas sur un autre système d'exploitation. Sur une machine sans cache de dépendances, la première installation nécessite Internet.

