# Démarrer sur un autre ordinateur

Le dossier `agent/` peut être extrait dans un emplacement différent, y compris avec des espaces dans le chemin. Il contient le code, les tests, les dépendances verrouillées, le CSV de travail et les réglages locaux du modèle. Il ne nécessite plus de dossier `kit/` ou `donnees/` à côté de lui.

## Installation

Installer `uv` sur l'ordinateur destinataire, puis ouvrir un terminal **dans le dossier extrait qui contient `pyproject.toml`** :

```console
uv sync --frozen
uv run kit agent "Combien de lignes compte le tableau ?"
uv run allergolab evaluer
uv run allergolab servir
```

`uv sync --frozen` recrée un environnement `.venv` propre à ce nouvel ordinateur et installe les versions inscrites dans `uv.lock`. Une connexion Internet est nécessaire lors de la première installation si Python 3.12 et les paquets ne sont pas déjà disponibles en cache. Il ne faut pas copier l'ancien `.venv` : il dépend de l'installation Python et du système de la machine d'origine.

La première commande de question utilise le CSV fourni et ne nécessite aucune clé d'IA. L'évaluation utilise uniquement des données fictives. L'API écoute sur `http://127.0.0.1:8000` ; ses exemples sont disponibles sur `/docs`.

## Données et configuration

Les chemins par défaut sont maintenant internes au dossier :

- CSV : `donnees/allergenchipchallenge-data-corrected-final-hdh-sfa.csv`.
- Dictionnaire copié : `donnees/acc-dictionnaire-final.xls`, dont le statut est expliqué dans `donnees/README.md`.
- Identifiants de modèles et tarifs estimatifs : `configuration/modeles.toml`.
- Données de fonctionnement créées automatiquement : `runtime/`.

Pour changer de CSV, définir `ALLERGOLAB_DONNEES`. Un chemin absolu peut viser un autre emplacement du nouvel ordinateur ; un chemin relatif est interprété à partir du dossier du projet, indépendamment du dossier depuis lequel la commande est lancée. Les mêmes règles s'appliquent à `ALLERGOLAB_REGLAGES`, `ALLERGOLAB_METADATA` et `ALLERGOLAB_RUNTIME`.

Le modèle est désactivé par défaut. Pour activer les questions qui nécessitent une planification, configurer `ALLERGOLAB_MODELE_ACTIF=true` et fournir sa propre clé via `ALLERGYLAB_CLE` dans l'environnement du nouveau processus. Aucune clé n'est fournie dans l'archive. `.env.example` explique les variables, mais n'est pas chargé automatiquement. Les réglages du modèle proviennent du projet initial et n'ont pas été validés par un appel au fournisseur.

## Vérification

```console
uv run pytest -q
uv run allergolab controle
```

La reconstruction de l'environnement permet d'utiliser les paquets adaptés au système destinataire. La vérification du transfert a été faite dans un autre dossier et un environnement Python neuf sur la machine de développement ; elle ne remplace pas un essai sur chaque système d'exploitation cible.

