# Développement du jalon 0.3.0

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
- `settings.py` : paramètres matériels validés et sérialisables.
- `schedule.py` : planning hebdomadaire local pur, normalisé et testé aux changements DST.
- `cycle_controller.py` : machine à états pure avec horloge injectée ; elle impose hystérésis, durées minimales, cooldown, confirmation et défaut verrouillé.
- `heater_adapter.py` : seule passerelle vers un `switch`, avec validation d'état et de service.
- `runtime.py` : sérialise les événements HA, le stockage, le timer et les décisions ; il ne commande jamais au déchargement.
- `storage.py` : Store privé, versionné et validé à la lecture.
- `climate.py` : adaptation Home Assistant des modes OFF/HEAT et de la consigne, sans logique thermique complexe.
- `diagnostics.py` : résumé par liste blanche sans référence privée.

Le choix de sources et le planning sont stockés dans Config Entry / Options, schéma 1. Les options portent aussi les protections matérielles. Le Store privé conserve l'état de contrôle et une éventuelle dérogation AUTO jusqu'au prochain point ; il ne figure pas dans les diagnostics. Le mode observation est la valeur par défaut ; le test matériel demeure hors de ce dépôt.

Le Core 2026.9.3 installé fournit des sélecteurs utilisant voluptuous ; le Config Flow utilise cette API, validée par les tests réels du framework. Cela précise le repérage documentaire initial, qui mentionnait aussi probatio dans la documentation récente.

## Validation

Les validations à exécuter restent Ruff (lint et format), mypy et pytest sur Python 3.14.7 / HA 2026.9.3, avec `--disable-socket --allow-unix-socket`.

Les fixtures créent une instance HA de test en mémoire avec des entités factices. Elles n'utilisent ni MCP, URL domestique, ni jeton. Les scénarios de cycle de vie vérifient l'absence de commande au déchargement. Les scénarios de contrôle utilisent des services switch factices ; ils couvrent le mode observation, la confirmation unique d'une commande et le verrouillage lors d'une indisponibilité.

La suite vérifie les flows, les doublons, les sources hors ligne, le changement de sources avec un seul reload, les identités, les unités, les mesures invalides, les renommages et suppressions, la désinscription des listeners, les diagnostics expurgés, les traductions et le manifeste minimal.

La CI GitHub est fournie mais son exécution distante dépend de la publication du dépôt. Le manifeste n'invente ni URL de documentation publique ni codeowner : ils devront être renseignés lorsque le dépôt public et ses mainteneurs seront connus, avant une validation de distribution HACS/hassfest complète. Le chargement du manifeste et de l'intégration est vérifié localement par Home Assistant lui-même ; ce n'est pas une certification Home Assistant ou HACS.

## Limites

Les tests ne valident pas les protections propres à un poêle réel. Aucun essai matériel, déploiement domestique ou parcours graphique manuel n'est effectué. La détection d'une température numérique figée, les conversions K, le planning, la prédiction, le modèle appris et leurs migrations restent hors de ce jalon.
