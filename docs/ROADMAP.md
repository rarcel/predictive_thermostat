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

## Étape 3 — Planning interne et AUTO (0.3.0)

- modèle de planning ;
- Options Flow ;
- cible courante/prochaine ;
- mode `AUTO` ;
- dérogation jusqu'au prochain point ;
- gestion DST et tests.

Implémenté dans le dépôt : planning hebdomadaire local validé dans l'Options Flow, cible courante et suivante, mode `AUTO`, dérogation manuelle persistée jusqu'au prochain point et règles DST déterministes. AUTO applique seulement la cible active ; l'anticipation reste l'étape prédictive suivante. Les protections du contrôleur et le mode observation ont toujours priorité.

## Étape 4 — Prédiction fallback (0.4.0)

- prise en compte de la température extérieure ;
- estimateur conservateur sans apprentissage ;
- planification exacte du début ;
- attributs de diagnostic ;
- mode observation.

Implémenté dans le dépôt : estimateur local, léger, explicable et borné par les options ; la température extérieure intervient dans les pertes. Seules les hausses vers le prochain objectif peuvent être avancées. Sans sonde extérieure valide, aucune anticipation n'est faite. Le contrôleur de cycle reste l'autorité finale et le mode observation empêche toute commande réelle.

## Étape 5 — Collecte et apprentissage (0.5.0)

- détecteur de cycles ;
- filtrage qualité ;
- stockage versionné ;
- modèle robuste et confiance ;
- correction lente de l'erreur d'arrivée ;
- migrations et tests.

Implémenté dans le dépôt : validation de cycles de chauffe terminés, agrégat privé sans données brutes, mise à jour lente et bornée de la vitesse de chauffe et des pertes extérieures, et correction lente de l’erreur d’arrivée. L’état agrégé est restauré depuis le Store privé ; les cycles invalides sont ignorés.

## Étape 6 — Durcissement réel

- test sur entités factices ;
- observation sur installation ;
- activation contrôlée ;
- diagnostics, documentation HACS, icônes/brand si utile ;
- revue des scénarios de panne.

Durcissement de dépôt en cours : les tests couvrent le repli sans extérieur, le défaut d’actionneur, les commandes confirmées, les redémarrages de logique, les cycles courts, les DST et le déchargement sans commande. Les essais sur une installation, l’observation de prédictions réelles et toute activation matérielle restent explicitement hors du dépôt et exigent un accord distinct.

## Après V1

- arrêt optimal ;
- prévision de température extérieure ;
- actionneurs `climate` ou scripts ;
- événements calendrier/vacances ;
- carte Lovelace ;
- plusieurs zones ou source de chaleur partagée.
