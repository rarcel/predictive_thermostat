# Instructions du dépôt

## Mission

Construire `predictive_thermostat`, une custom integration Home Assistant générique, locale et explicable, optimisée en premier lieu pour un poêle à granulés. Elle doit atteindre une température à une heure donnée en anticipant le démarrage selon la température intérieure, la température extérieure et le comportement thermique appris.

## Principes non négociables

- Exposer une seule entité utilisateur principale de domaine `climate` par zone.
- Ne pas créer une constellation de helpers ou de capteurs techniques.
- Le planning est interne à l'intégration et chaque point signifie « température à atteindre à cette heure ».
- Ne jamais modifier ni surcharger l'intégration Core `generic_thermostat`.
- Implémenter une intégration autonome inspirée de son comportement utile.
- Toute commande du chauffage passe par un contrôleur de cycle centralisé et testable.
- Un modèle prédictif ne doit jamais contourner les protections matérielles.
- Fonctionnement local uniquement, sans cloud ni LLM à l'exécution.
- Les paramètres et données appris sont privés par défaut et expurgés des diagnostics.

## Méthode de travail

1. Avant de coder, lire tous les documents de `docs/`.
2. Si le MCP Home Assistant est disponible, commencer par l'audit en lecture seule décrit dans `prompts/02_ha_audit.md`.
3. Ne jamais écrire dans Home Assistant via MCP sans accord explicite de l'utilisateur.
4. Inspecter les conventions de la version Home Assistant ciblée dans la documentation officielle ou le code Core installé avant d'utiliser une API incertaine.
5. Livrer par incréments verticaux testables selon `docs/ROADMAP.md`.
6. Pour chaque incrément : tests d'abord ou simultanément, implémentation, lint/type-check, tests complets, puis mise à jour de la documentation.
7. Ne pas masquer une hypothèse métier : la documenter et la rendre configurable lorsqu'elle dépend du matériel.

## Contraintes techniques

- Python pris en charge par la version Home Assistant ciblée.
- Async natif ; aucune I/O bloquante dans la boucle événementielle.
- Config Entry uniquement ; pas de configuration YAML en V1.
- Config Flow et Options Flow avec sélecteurs d'entités adaptés.
- Traductions au minimum en anglais et en français.
- Stockage interne versionné et migrable via les mécanismes Home Assistant appropriés.
- Désabonnement de tous les listeners lors du déchargement.
- Rechargement propre de la Config Entry après changement structurel d'options.
- Identifiants uniques stables ; ne jamais dépendre d'un `entity_id` comme identité durable.
- Services et appels d'entités validés avant usage ; erreurs visibles et sûres.
- Aucun secret, historique brut ou identifiant sensible dans les logs normaux.

## Architecture du code attendue

Séparer strictement :

- `schedule` : résolution du point courant et du prochain objectif ;
- `model` : prédiction et mise à jour statistique, sans dépendance Home Assistant ;
- `cycle_controller` : machine à états et protections ON/OFF ;
- `observations` : construction/validation des cycles d'apprentissage ;
- `climate` : adaptation Home Assistant, sans mathématique métier complexe ;
- `storage` : sérialisation versionnée ;
- `config_flow` et `options_flow` : configuration utilisateur.

Le cœur (`schedule`, `model`, `cycle_controller`) doit pouvoir être testé sans démarrer Home Assistant.

## Qualité et validation

- `pytest` couvre les unités, les changements de jour, DST, indisponibilités, redémarrages et cycles courts.
- Tester le temps avec une horloge injectée ; ne pas appeler directement `datetime.now()` dans le cœur.
- Tester des propriétés/invariants : jamais de redémarrage pendant le cooldown, anticipation bornée, aucune commande rapide répétée.
- Utiliser Ruff et mypy si compatibles avec le scaffold choisi.
- Viser une couverture élevée du cœur métier, sans utiliser la couverture comme substitut aux scénarios.
- Chaque correction de bug ajoute un test de non-régression.

## Sécurité du chauffage

- Le mode prédictif n'augmente jamais la température cible au-delà de la cible planifiée/manuelle.
- Une donnée absente ou invalide provoque un fallback conservateur, jamais une boucle de commandes.
- Les durées minimale de marche, minimale d'arrêt et le cooldown ont priorité absolue.
- Après redémarrage, réconcilier l'état réel de l'actionneur avant toute décision.
- Une commande d'allumage/arrêt ne doit pas être répétée tant que l'état attendu n'est pas confirmé ou que le délai configurable n'est pas expiré.
- En cas de défaut d'actionneur, conserver l'état de défaut, journaliser clairement et cesser les tentatives rapides.

## Hors périmètre sans décision explicite

- carte Lovelace personnalisée ;
- prévisions météo ;
- optimisation tarifaire ;
- contrôle de plusieurs chauffages par une même entité ;
- refroidissement/climatisation ;
- arrêt optimal ;
- publication HACS officielle ou dépôt Home Assistant Core.

