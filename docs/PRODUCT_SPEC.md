# Spécification produit

## Problème

Un thermostat classique applique une nouvelle consigne à l'heure programmée. Avec un poêle à granulés, la pièce n'atteint la température souhaitée que bien plus tard. Le produit doit anticiper le démarrage, apprendre le comportement réel du logement et rester simple à utiliser.

## Objet principal

Une Config Entry représente une zone et crée une entité principale :

`climate.<nom_de_zone>`

Elle s'appuie sur :

- une sonde de température intérieure ;
- une sonde de température extérieure ;
- un actionneur ou une entité de chauffage compatible ;
- un planning hebdomadaire intégré.

## Sémantique du planning

Chaque point est un objectif à atteindre, pas une simple commande différée.

Exemple :

| Jours | Heure | Température |
| --- | ---: | ---: |
| Lun–Ven | 07:00 | 20,5 °C |
| Lun–Ven | 09:00 | 18,0 °C |
| Lun–Ven | 17:30 | 20,5 °C |
| Lun–Ven | 22:30 | 17,0 °C |
| Sam–Dim | 08:30 | 20,5 °C |
| Sam–Dim | 23:00 | 17,0 °C |

À tout instant, le moteur doit déterminer sans ambiguïté :

- la cible actuellement active ;
- le prochain point futur ;
- sa date/heure absolue dans le fuseau Home Assistant ;
- si une hausse future justifie un préchauffage.

## Modes HVAC

- `OFF` : aucune demande de chauffage ; arrêt soumis aux protections nécessaires.
- `HEAT` : consigne manuelle permanente, régulation classique avec hystérésis.
- `AUTO` : planning actif et préchauffage prédictif autorisé.

Actions attendues : `OFF`, `IDLE`, `HEATING` et, si l'API de la version ciblée le permet correctement, `PREHEATING`. Sinon, exposer l'état de préchauffage par un attribut stable sans inventer une valeur d'enum.

## Dérogation manuelle

En `AUTO`, un changement manuel de température crée par défaut une dérogation jusqu'au prochain point du planning. L'Options Flow pourra proposer :

- jusqu'au prochain point (défaut) ;
- durée fixe configurable ;
- permanente jusqu'à reprise explicite du mode `AUTO`.

La V1 peut n'implémenter que le comportement par défaut, à condition de garder un modèle de données extensible.

## Configuration initiale

Le Config Flow demande :

- nom de zone ;
- capteur intérieur ;
- capteur extérieur ;
- actionneur de chauffage et méthode de commande ;
- comportement actif de l'actionneur si nécessaire ;
- planning initial ou planning minimal guidé.

L'Options Flow gère :

- planning hebdomadaire ;
- hystérésis froide/chaude ;
- durée minimale de marche ;
- durée minimale d'arrêt/cooldown ;
- délai d'allumage estimé initial ;
- anticipation minimale et maximale ;
- marge de sécurité ;
- comportement en cas de sonde extérieure indisponible ;
- activation de l'apprentissage.

## Attributs diagnostiques de l'entité

Limiter les attributs à des données utiles et de faible cardinalité :

- `schedule_target_temperature`
- `next_target_temperature`
- `next_target_time`
- `predicted_start_time`
- `predicted_heating_minutes`
- `prediction_confidence`
- `learning_samples`
- `last_prediction_error_minutes`
- `control_state`
- `fallback_reason` lorsque pertinent

Ne pas exposer tout l'historique ni les coefficients bruts dans l'état. Les diagnostics téléchargés peuvent contenir un résumé expurgé.

## Disponibilité et fallback

- Sonde intérieure invalide : aucune nouvelle décision ON, état indisponible ou dégradé explicite.
- Sonde extérieure invalide : utiliser la dernière valeur fraîche pendant une durée bornée, puis un fallback configuré/conservateur.
- Modèle non entraîné : estimation initiale conservatrice et bornée.
- Actionneur indisponible : aucune répétition rapide ; défaut visible.
- Redémarrage HA : restaurer le modèle, relire les entités, réconcilier l'état physique, puis seulement décider.

## Critères de réussite V1

- Configuration sans YAML.
- Une seule entité principale au quotidien.
- Un objectif programmé est résolu correctement sur sept jours et les changements DST.
- Le chauffage démarre à l'heure prédite dans la limite de la précision de la boucle HA.
- L'anticipation varie de façon cohérente avec l'écart à la cible et les conditions extérieures.
- Aucun cycle court n'est provoqué par le prédictif.
- Le système reste utilisable et sûr sans données apprises.
- Les données apprises persistent après redémarrage et sont migrables.

