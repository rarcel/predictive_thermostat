# Feuille de route

## Étape 0 — Audit et décisions

- audit MCP Home Assistant en lecture seule ;
- identifier sonde intérieure, extérieure, actionneur et états réels du poêle ;
- relever délais d'allumage/extinction et automatisations concurrentes ;
- produire `docs/INSTALLATION_AUDIT.md` ;
- confirmer le périmètre et les défauts de sécurité avec l'utilisateur.

Sortie : aucune modification de Home Assistant.

## Étape 1 — Scaffold installable

Implémentation locale 0.1.0 : entité passive OFF/observation, choix générique des sources, Options Flow de sources avec rechargement, suivi des renommages, °C/°F, diagnostics expurgés, traductions FR/EN et tests. Installation manuelle documentée dans README.md. Aucune commande ni installation sur l'instance domestique. Le planning et les prédictions restent aux étapes suivantes.

- manifeste, Config Flow minimal, traductions ;
- création/déchargement d'une Config Entry ;
- entité climate sans commande prédictive ;
- tests de base et CI.

## Étape 2 — Thermostat sûr non prédictif (0.2.0)

- lecture sonde intérieure ;
- adapter `switch` ;
- `OFF` et `HEAT` ;
- hystérésis, durée minimale de marche, cooldown ;
- réconciliation et timeouts ;
- tests de machine à états.

Implémenté dans le dépôt : contrôleur de cycle pur à horloge injectée, adaptateur `switch`, persistance privée versionnée, reprise prudente, timeout et défaut verrouillé, Options Flow de protections et mode observation par défaut. Le contrôle réel n'est effectué qu'après désactivation explicite du mode observation ; aucun déploiement ou essai matériel n'est réalisé par le projet.

Ce jalon doit être fiable avant tout apprentissage.

## Étape 3 — Planning interne et AUTO

- modèle de planning ;
- Options Flow ;
- cible courante/prochaine ;
- mode `AUTO` ;
- dérogation jusqu'au prochain point ;
- gestion DST et tests.

## Étape 4 — Prédiction fallback

- prise en compte de la température extérieure ;
- estimateur conservateur sans apprentissage ;
- planification exacte du début ;
- attributs de diagnostic ;
- mode observation.

## Étape 5 — Collecte et apprentissage

- détecteur de cycles ;
- filtrage qualité ;
- stockage versionné ;
- modèle robuste et confiance ;
- correction lente de l'erreur d'arrivée ;
- migrations et tests.

## Étape 6 — Durcissement réel

- test sur entités factices ;
- observation sur installation ;
- activation contrôlée ;
- diagnostics, documentation HACS, icônes/brand si utile ;
- revue des scénarios de panne.

## Après V1

- arrêt optimal ;
- prévision de température extérieure ;
- actionneurs `climate` ou scripts ;
- événements calendrier/vacances ;
- carte Lovelace ;
- plusieurs zones ou source de chaleur partagée.
