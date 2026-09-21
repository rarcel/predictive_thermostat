# Predictive Thermostat

Custom integration Home Assistant générique, locale et paramétrable pour les chauffages à forte inertie, en premier lieu les poêles à granulés. À terme, chaque point du planning interne exprimera une **température à atteindre à une heure donnée**, avec anticipation selon les températures intérieure/extérieure et un modèle thermique explicable.

## Version actuelle : 0.1.0 — observation uniquement

Ce premier jalon crée **une seule entité climate par zone**, avec un appareil virtuel et une configuration via l'interface. Les sources sont choisies librement : aucune dépendance aux entités d'une installation particulière, à ESPHome ou à Zigbee2MQTT.

**Cette version ne chauffe pas.** Elle ne contient aucun appel de service de chauffage, y compris au démarrage, au rechargement, à la suppression ou au passage OFF. Le thermostat existant continue à piloter le matériel. OFF désigne l'absence de demande de cette intégration : ce n'est ni une commande d'arrêt du poêle ni une indication de son état physique.

Fonctionnalités présentes :

- Config Flow et Options Flow pour sélectionner/changer les deux sondes et le switch ;
- identité stable par zone, préservée lors des changements de sources ;
- suivi des renommages des sources enregistrées dans le registre HA ;
- affichage des mesures avec conversion °C/°F vers les unités configurées dans HA ;
- état dégradé en cas de mesure invalide ou d'actionneur indisponible ;
- diagnostics sans identifiants privés et traductions française/anglaise.

Le planning, les consignes manuelles, la régulation, les protections de cycle, les prédictions et l'apprentissage **ne sont pas encore implémentés**. Il n'y a donc pas encore de prédictions à comparer. Ces fonctions seront livrées selon [la feuille de route](docs/ROADMAP.md), avec observation avant activation réelle et protections matérielles prioritaires sur le prédictif.

## Prérequis

- Home Assistant **2026.9.3**, version actuellement testée ; les autres versions ne sont pas encore validées.
- Deux entités `sensor` distinctes avec `device_class: temperature` et unité °C ou °F. Choisir des sondes locales pour conserver un fonctionnement entièrement local.
- Une entité `switch` représentant la demande de chauffage, uniquement observée dans cette version. Une entité enregistrée temporairement indisponible peut être sélectionnée : aucun essai d'allumage n'est effectué.

Il n'est pas nécessaire d'installer Python manuellement sur Home Assistant OS. Python ≥ 3.14.2 concerne l'environnement de développement conforme à la version HA ciblée. Aucun helper supplémentaire n'est requis.

## Installation manuelle

Ces instructions décrivent les opérations à effectuer vous-même sur l'instance choisie. Les tests de ce dépôt ne déploient rien automatiquement dans Home Assistant. Pour une première découverte, une instance de test est recommandée.

1. Récupérer le contenu de ce dépôt (copie locale ou archive).
2. Dans le répertoire de configuration Home Assistant, celui qui contient `configuration.yaml`, créer `custom_components` s'il n'existe pas.
3. Copier **uniquement** le dossier `custom_components/predictive_thermostat` du dépôt dans ce répertoire. Ne pas copier l'environnement de développement, les tests ou l'audit personnel.
4. Vérifier que le manifeste est directement à l'emplacement ci-dessous, sans niveau de dossier supplémentaire :

   ```text
   <configuration Home Assistant>/
     configuration.yaml
     custom_components/
       predictive_thermostat/
         __init__.py
         manifest.json
         const.py
         config_flow.py
         climate.py
         sources.py
         diagnostics.py
         strings.json
         translations/
           en.json
           fr.json
   ```

   Sur Home Assistant OS, le répertoire de configuration est généralement `/config`. Sur Home Assistant Container, il correspond au volume monté dans `/config`.
5. Redémarrer Home Assistant pour charger la nouvelle intégration.
6. Ouvrir **Paramètres → Appareils et services → Ajouter une intégration**, puis rechercher **Predictive Thermostat**.
7. Saisir un nom de zone, sélectionner les sondes intérieure/extérieure et le switch de chauffage. Valider : une entité climate est créée, sans commande du switch.

Ne pas ajouter de bloc `predictive_thermostat:` dans `configuration.yaml` : la configuration se fait exclusivement par Config Entry. Ne pas remplacer le dossier Core `generic_thermostat`.

La distribution HACS et la publication officielle ne font pas partie de ce jalon. L'installation documentée est manuelle ; aucune URL de dépôt public n'est présumée.

## Utilisation et paramètres

L'entité affiche la température intérieure et le mode OFF uniquement. Elle ne propose ni consigne ni mode HEAT/AUTO. Ses attributs :

| Attribut | Signification |
| --- | --- |
| `control_state` | Toujours `observation` dans ce jalon |
| `observation_only` | Toujours `true`, non désactivable dans cette version |
| `outdoor_temperature` | Température extérieure dans les mêmes unités HA que l'intérieur, ou `null` |
| `heater_available` | Le switch sélectionné a un état on/off ; cela ne confirme pas une flamme |
| `fallback_reason` | Source intérieure, extérieure ou actionneur indisponible/invalide, sinon `null` |

Une mesure intérieure manquante ou invalide rend l'entité indisponible. La perte de l'extérieur ou du switch conserve l'affichage intérieur avec un état dégradé. Les dernières mesures numériques sont affichées telles que fournies par les sources : **ce jalon ne détecte pas encore une mesure figée mais toujours numérique**. Il n'en tire aucune décision de chauffe.

Pour changer les sources, ouvrir l'intégration dans **Paramètres → Appareils et services**, puis son bouton **Configurer / Options** selon l'interface. Le changement recharge uniquement cette intégration ; l'identité de la zone est conservée. Un même actionneur ne peut pas être attribué à deux zones de Predictive Thermostat. Le composant ne vérifie pas les autres contrôleurs utilisant cet actionneur et ne les modifie pas.

Les sources enregistrées dans le registre HA sont suivies après renommage. Pour une source sans identité enregistrée, la référence reste son entity_id : après renommage, sélectionner la nouvelle source dans les options. Le nom de zone et l'entité peuvent être renommés par les fonctions habituelles de Home Assistant.

Les paramètres thermiques, durées minimales, cooldown, planning et limites de consigne seront configurables dans les futurs jalons. Aucun réglage propre à un logement n'est imposé. Le planning utilisera le fuseau configuré dans Home Assistant.

## Mise à jour et suppression

Pour mettre à jour, remplacer uniquement le dossier de cette custom integration par celui de la nouvelle version, puis redémarrer Home Assistant. Lire les notes de version avant toute future version capable de commander le chauffage.

Pour supprimer, retirer l'entrée Predictive Thermostat depuis **Appareils et services**. Si elle n'est plus utilisée pour aucune zone, retirer son dossier de custom_components, puis redémarrer. Cette version n'envoie pas d'ordre au chauffage lors de la suppression et ne modifie pas le thermostat existant.

## Dépannage

- **Intégration absente de la recherche** : vérifier le chemin exact du manifeste, redémarrer HA et recharger la page du navigateur. Consulter les journaux pour les erreurs de chargement.
- **Sonde absente du sélecteur** : vérifier son domaine sensor et sa classe temperature dans les attributs HA. Une sonde exposant seulement une unité sans classe de température n'est pas sélectionnable par ce flow.
- **Zone indisponible** : vérifier la sonde intérieure et son unité. unknown, unavailable, NaN et infini ne sont pas des températures acceptées.
- **Switch indisponible** : l'observation reste possible ; un appareil débranché peut expliquer cet état. Le composant ne tente aucune reconnexion par commande.
- **Impossible d'allumer avec cette entité** : comportement normal de la version 0.1.0. Utiliser le contrôleur existant.

Les diagnostics téléchargeables indiquent seulement la version de schéma, le mode observation et si les références des sources se résolvent. Ils n'incluent ni identifiants d'entités, ni nom de zone, ni mesures. Les états et références restent néanmoins stockés localement par les mécanismes habituels de Home Assistant.

## Développement et validation

Voir [DEVELOPMENT.md](docs/DEVELOPMENT.md) pour l'environnement isolé et les commandes de test. La CI exécute lint, format, mypy et les tests contre Home Assistant 2026.9.3 sans accès à une installation domestique.

L'audit d'installation est un document local ignoré par Git ; il ne doit pas accompagner une distribution publique. Les tests utilisent exclusivement des entités factices.

