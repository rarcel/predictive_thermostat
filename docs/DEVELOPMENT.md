# Développement du jalon 0.1.0

## Environnement isolé

Utiliser Linux (ou WSL) et Python >=3.14.2. La combinaison validée localement est Python 3.14.7, Home Assistant 2026.9.3 et pytest-homeassistant-custom-component 0.13.366. Ne pas exécuter les tests dans le répertoire de configuration du Home Assistant domestique.

```sh
python3.14 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements_test.txt
ruff check custom_components tests
ruff format --check custom_components tests
mypy
pytest -q --disable-socket --allow-unix-socket
```

Avec uv déjà installé : `uv venv --python 3.14.7 .venv`, puis `uv pip install -r requirements_test.txt`. Sous WSL, préférer un environnement dans le système de fichiers Linux si la copie des dépendances sur un volume Windows échoue ; le dépôt peut rester sur le volume Windows. Les versions directes sont épinglées ; les dépendances transitives sont résolues par l'installateur.

## Architecture actuelle

- `__init__.py` : chargement/déchargement de la plateforme climate uniquement.
- `config_flow.py` : validation des sources, création de zone, OptionsFlowWithReload. Aucun test matériel lors du flow.
- `sources.py` : références stables de registre, résolution après renommage et conversion des températures.
- `climate.py` : entité passive et listeners annulés au retrait. Aucune interface de commande du chauffage.
- `diagnostics.py` : résumé par liste blanche sans référence privée.

Le choix de sources est stocké dans Config Entry / Options, schéma 1. Il n'y a ni modèle appris ni fichier Store dans ce jalon, ni besoin de runtime_data partagé ou de coordinateur. Les modules métier sont ajoutés avec leurs tests aux étapes suivantes.

Le Core 2026.9.3 installé fournit des sélecteurs utilisant voluptuous ; le Config Flow utilise cette API, validée par les tests réels du framework. Cela précise le repérage documentaire initial, qui mentionnait aussi probatio dans la documentation récente.

## Validation

Résultat local du 21 septembre 2026 : **27 tests réussis**, Ruff (lint et format) et mypy réussis sur Python 3.14.7 / HA 2026.9.3. Tests exécutés avec `--disable-socket --allow-unix-socket`. Les scénarios incluent deux zones indépendantes, la restauration de références sérialisées et le rejet d'un débordement numérique lors d'une conversion.

Les fixtures créent une instance HA de test en mémoire avec des entités factices. Elles n'utilisent pas le MCP, d'URL domestique ou de jeton. Les tests de cycle de vie interceptent tous les appels de service et vérifient qu'aucun n'est émis. Un autre scénario passe par les vrais services climate et des services switch factices pour vérifier que les commandes refusées ne sont pas transmises.

La suite vérifie les flows, les doublons, les sources hors ligne, le changement de sources avec un seul reload, les identités, les unités, les mesures invalides, les renommages et suppressions, la désinscription des listeners, les diagnostics expurgés, les traductions et le manifeste minimal.

La CI GitHub est fournie mais son exécution distante dépend de la publication du dépôt. Le manifeste n'invente ni URL de documentation publique ni codeowner : ils devront être renseignés lorsque le dépôt public et ses mainteneurs seront connus, avant une validation de distribution HACS/hassfest complète. Le chargement du manifeste et de l'intégration est vérifié localement par Home Assistant lui-même ; ce n'est pas une certification Home Assistant ou HACS.

## Limites

Les tests valident l'adaptation HA et l'absence de commandes, pas les protections d'un poêle réel. Aucun essai matériel, déploiement domestique ou parcours graphique manuel n'est effectué. La détection d'une température numérique figée, les conversions K, le planning, la régulation, le modèle et leurs migrations restent hors de ce jalon.
