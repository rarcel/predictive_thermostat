# Predictive Thermostat

`predictive_thermostat` est une custom integration Home Assistant locale et paramétrable, conçue d'abord pour des chauffages à forte inertie tels qu'un poêle à granulés. Elle expose **une seule entité `climate` principale par zone**. Son planning interne futur signifiera toujours « température à atteindre à cette heure » ; la température extérieure servira à une prédiction explicable, locale et légère.

## Version actuelle : 0.3.0 — planning interne et AUTO, sans prédiction

Cette étape apporte `OFF`, `HEAT` manuel et `AUTO`, une consigne, un planning interne hebdomadaire, un adaptateur `switch` et un contrôleur de cycle centralisé. La prédiction et l'apprentissage ne sont pas encore disponibles. Le modèle futur ne pourra jamais augmenter la consigne au-delà de la cible manuelle ou planifiée, ni contourner les protections matérielles.

L'intégration est créée en **mode observation**. Dans ce mode, elle calcule la décision qui serait prise mais n'appelle jamais le switch. Pour autoriser le mode HEAT réel, il faut désactiver explicitement cette option après avoir vérifié le câblage, la polarité, les délais constructeur et l'absence de contrôleur concurrent. Cette documentation ne déploie ni ne modifie aucune installation Home Assistant.

Le contrôleur applique, dans cet ordre :

- une hystérésis configurable autour de la consigne ;
- une durée minimale de marche ;
- une durée minimale d'arrêt et un cooldown après arrêt ;
- une commande en attente jusqu'à confirmation de l'état réel ;
- un verrouillage de défaut en cas de switch indisponible, erreur ou timeout, sans nouvelle tentative rapide.

Une donnée intérieure absente, invalide ou trop ancienne conduit à une demande d'arrêt conservatrice ; la durée minimale de marche reste prioritaire. Après un redémarrage, l'état réel du switch est relu avant toute décision. Une commande interrompue est verrouillée jusqu'à acquittement explicite dans les options.

## Prérequis

- Home Assistant **2026.9.3**, version validée par la suite de tests.
- Deux entités `sensor` distinctes de classe `temperature`, en °C ou °F, pour l'intérieur et l'extérieur.
- Une entité `switch` qui représente de façon fiable une demande de chauffage. L'intégration ne déduit pas une flamme, une température de fumées ou un défaut matériel.
- Les valeurs documentées par le fabricant pour les durées d'allumage, d'extinction et les restrictions de cycles. Les valeurs proposées sont des valeurs de départ, jamais une garantie de compatibilité matérielle.

Les sources sont choisies au moment de la configuration ; aucune entité propre à une installation, aucun helper et aucun cloud ne sont requis.

## Installation manuelle

Effectuez ces opérations sur l'instance Home Assistant de votre choix, de préférence une instance de test.

1. Récupérez le dépôt.
2. Dans le répertoire qui contient `configuration.yaml`, créez `custom_components` si nécessaire.
3. Copiez uniquement `custom_components/predictive_thermostat` dans ce dossier.
4. Vérifiez que `manifest.json` est directement sous `<configuration>/custom_components/predictive_thermostat/`.
5. Redémarrez Home Assistant.
6. Ouvrez **Paramètres → Appareils et services → Ajouter une intégration**, recherchez **Predictive Thermostat**, puis sélectionnez le nom de zone, les deux sondes et le switch.

Sur Home Assistant OS et Home Assistant Container, le répertoire de configuration est en général `/config`. N'ajoutez aucun bloc YAML `predictive_thermostat:` et ne remplacez jamais `generic_thermostat` du Core.

## Utilisation sûre

L'entité climate démarre en `OFF`, avec le mode observation actif. Une consigne et les modes `OFF`/`HEAT`/`AUTO` sont proposés pour permettre l'observation de la décision de cycle. Aucune action sur l'entité ne commande alors le switch.

En `AUTO`, le planning interne résout la cible active et le prochain objectif. Chaque ligne quotidienne utilise le format `HH:MM=température`, par exemple `06:30=19, 18:00=21`. Chaque jour doit contenir au moins un horaire unique ; les objectifs sont des températures **à atteindre** à leur heure, sans anticipation à cette étape. Une modification manuelle de consigne pendant `AUTO` devient une dérogation jusqu'au prochain point, puis le planning reprend. Les horaires sont conservés en heure locale Home Assistant. Une heure inexistante au passage à l'heure d'été est reportée au premier instant valide ; une heure répétée en automne est exécutée une seule fois, lors de sa première occurrence.

Pour préparer un essai contrôlé sur une instance de test, ouvrez **Configurer / Options** de l'intégration et renseignez toutes les options :

| Option | Rôle |
| --- | --- |
| `Mode observation` | Laisser activé tant que l'essai réel n'est pas explicitement décidé. Désactivé, le switch peut être commandé. |
| `Logique de l’interrupteur inversée` | À activer seulement si `on` signifie physiquement « pas de demande ». |
| `Durée minimale de marche`, `Durée minimale d’arrêt`, `Refroidissement` | Protections de cycle en secondes, à définir d'après la documentation matérielle. |
| `Délai de confirmation de commande` | Durée maximale pendant laquelle l'intégration attend le nouvel état du switch. |
| `Âge maximal de la sonde intérieure` | Au-delà, la température est considérée inconnue. |
| `Hystérésis` | Écart de démarrage et d'arrêt autour de la consigne. |
| Limites, pas et consigne initiale | Bornes de la consigne ; ces valeurs sont stockées en °C, indépendamment de l'unité d'affichage HA. |
| Objectifs du lundi au dimanche | Planning local interne, une ou plusieurs entrées `HH:MM=°C` par jour. |

Les changements d'options rechargent proprement l'intégration. Vérifiez que l'actionneur n'est pas aussi piloté par une automatisation, un thermostat ou un autre composant : l'intégration ne les désactive pas et ne les modifie pas. Un même switch ne peut pas être associé à deux zones Predictive Thermostat.

En cas de défaut verrouillé, corrigez d'abord sa cause puis cochez **Acquitter et réinitialiser un défaut verrouillé** dans les options. Cette action recharge l'intégration ; elle ne force pas de commande immédiate. Les attributs `control_state`, `fault_reason`, `pending_command`, `heater_available` et `fallback_reason` permettent d'examiner la situation sans exposer les références privées des sources dans les diagnostics.

## Limites de cette étape

- Pas de prédiction, de préchauffage, d'apprentissage ou d'arrêt optimal. `AUTO` suit la cible courante : il ne cherche pas encore à atteindre la prochaine cible à l'heure demandée.
- La température extérieure est déjà configurée et affichée, mais n'influence pas encore la décision. Elle sera une entrée de l'estimateur thermique local et explicable à l'étape suivante.
- L'adaptateur V0.2 accepte un `switch` uniquement. Les scripts et entités climate comme actionneurs sont hors périmètre.
- L'intégration ne remplace pas les sécurités internes, thermostats de sûreté ou notices du poêle.

## Mise à jour, suppression et dépannage

Pour mettre à jour, remplacez le seul dossier de l'intégration puis redémarrez Home Assistant. Pour la retirer, supprimez d'abord son entrée dans **Appareils et services**, puis son dossier si aucune zone ne l'utilise. Le déchargement et la suppression n'envoient aucune commande au switch.

- **Sonde indisponible ou trop ancienne** : l'entité affiche l'état dégradé et n'émet aucune commande répétée.
- **Switch indisponible** : le contrôle réel est verrouillé en défaut ; rétablissez le switch puis acquittez le défaut.
- **Mode HEAT ne change rien** : vérifiez d'abord que le mode observation est toujours actif ; c'est le comportement prévu par défaut.
- **Intégration absente** : vérifiez le chemin de `manifest.json`, redémarrez HA et consultez les journaux de chargement.

Les diagnostics expurgent les noms et identifiants de sources, les mesures et les données d'apprentissage. Le stockage privé conserve seulement l'état de contrôle nécessaire à une reprise sûre ; il est versionné et validé avant lecture.

## Développement

Voir [le guide de développement](docs/DEVELOPMENT.md). Les tests n'utilisent que des entités factices et ne contactent pas une installation Home Assistant domestique. L'audit local d'installation est ignoré par Git et ne fait pas partie de la distribution.
