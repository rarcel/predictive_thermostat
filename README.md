# Predictive Thermostat

`predictive_thermostat` est une custom integration Home Assistant locale et paramétrable, conçue d'abord pour des chauffages à forte inertie tels qu'un poêle à granulés. Elle expose **une seule entité `climate` principale par zone**. Son planning interne signifie « température à atteindre à cette heure » ; la température extérieure alimente une prédiction explicable, locale et légère.

## Version actuelle : 0.7.6 — ressource Lovelace chargée avant le tableau de bord

L’intégration propose `OFF`, `HEAT` manuel et `AUTO`, une consigne, un planning hebdomadaire, un adaptateur `switch`, un contrôleur de cycle centralisé, une anticipation fallback, un apprentissage local, une météo facultative et un arrêt optimal facultatif. Elle peut commander le switch de chauffage lorsque le mode observation est explicitement désactivé. Le modèle ne peut jamais augmenter la consigne au-delà de la prochaine cible planifiée, ni contourner les protections matérielles.

L'intégration est créée en **mode observation**. Dans ce mode, elle calcule la décision qui serait prise mais n'appelle jamais le switch. Pour autoriser le contrôle réel en `HEAT` ou `AUTO`, désactivez explicitement cette option après avoir vérifié le câblage, la polarité, les délais constructeur et l'absence de contrôleur concurrent.

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

## Installation HACS

Après publication du dépôt Git, ajouter le dépôt dans **HACS → Intégrations → Menu → Dépôts personnalisés**, avec la catégorie **Integration**, puis installer **Predictive Thermostat**. Redémarrer Home Assistant et suivre ensuite le Config Flow décrit ci-dessus. La publication HACS ne déploie ni ne configure automatiquement une zone ; le mode observation reste activé à la création.

## Utilisation sûre

L'entité climate démarre en `OFF`, avec le mode observation actif. Une consigne et les modes `OFF`/`HEAT`/`AUTO` sont proposés pour permettre l'observation de la décision de cycle. Aucune action sur l'entité ne commande alors le switch.

En `AUTO`, le planning interne résout la cible active et le prochain objectif. Chaque ligne quotidienne utilise le format `HH:MM=température`, par exemple `06:30=19, 18:00=21`. Chaque jour doit contenir au moins un horaire unique ; les objectifs sont des températures **à atteindre** à leur heure. Pour une prochaine hausse, le fallback calcule une fenêtre de préchauffage bornée à partir du délai d'allumage, du gain à obtenir, de la température extérieure et d'une marge configurable. Une absence de température extérieure supprime l'anticipation et conserve le changement de cible à l'heure prévue. Une modification manuelle de consigne pendant `AUTO` devient une dérogation jusqu'au prochain point, puis le planning reprend. Les horaires sont conservés en heure locale Home Assistant. Une heure inexistante au passage à l'heure d'été est reportée au premier instant valide ; une heure répétée en automne est exécutée une seule fois, lors de sa première occurrence.

L'apprentissage mesure exclusivement le temps entre l'allumage réellement confirmé et la première atteinte de la consigne. La marche minimale, le dépassement et la régulation après cette première atteinte ne sont pas intégrés à la vitesse de chauffe. Si la prochaine consigne est déjà atteinte, la durée prédite est nulle. Pour une hausse planifiée, l'écart entre l'heure réelle d'atteinte et l'heure cible est aussi appris, y compris lorsque la cible est atteinte en retard. Une action manuelle annule cette observation pour ne pas attribuer son effet au modèle.

La durée est la somme explicable du délai d'allumage, du temps nécessaire au gain de température, de la correction liée à l'écart intérieur/extérieur, de la marge configurée et de la correction moyenne d'arrivée. Le résultat est ensuite borné par les durées minimale et maximale de préchauffage. Lorsque la météo est configurée, la prévision à l'heure de l'objectif est prioritaire ; la sonde extérieure sert de repli.

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
| Délai d’allumage, vitesse, pertes, marge, préchauffage min./max. | Hypothèses explicables du fallback, en minutes et °C/minute. Elles bornent l’anticipation, sans remplacer les protections de cycle. |
| Prévision météo facultative | Prévision horaire pour le prochain objectif. En cas d’échec, la sonde extérieure locale reste utilisée. |
| Arrêt optimal | Désactivé par défaut. Il peut demander un arrêt avant une baisse planifiée, mais les durées minimales de marche et de cooldown restent prioritaires. |

Les changements d'options rechargent proprement l'intégration. Vérifiez que l'actionneur n'est pas aussi piloté par une automatisation, un thermostat ou un autre composant : l'intégration ne les désactive pas et ne les modifie pas. Un même switch ne peut pas être associé à deux zones Predictive Thermostat.

### Parcours recommandé

1. Créez la zone avec les deux sondes et le switch, puis gardez **Mode observation** activé.
2. Saisissez un planning simple sur tous les jours, par exemple `06:30=19; 22:30=17`. Utilisez de préférence le point pour les décimales : `07:15=20.5`. La virgule `20,5` reste acceptée.
3. Vérifiez pendant quelques transitions les attributs `schedule_target_temperature`, `next_target_time`, `predicted_start_time`, `prediction_outdoor_temperature`, `prediction_outdoor_source`, `prediction_reason` et `fallback_reason`.
4. Si une entité météo est disponible, sélectionnez-la dans les options ; elle est facultative et la sonde extérieure conserve le rôle de repli.
5. Comparez les horaires prédits aux températures réelles. `learning_samples`, `learned_heating_rate`, `learned_loss_factor` et `last_prediction_error_minutes` montrent les agrégats appris. Les attributs `prediction_ignition_minutes`, `prediction_temperature_gain_minutes`, `prediction_outdoor_loss_minutes`, `prediction_margin_minutes` et `prediction_arrival_correction_minutes` détaillent chaque terme du calcul courant.

`control_state` décrit la décision interne (`idle`, `heating`, `cooldown`, `minimum_runtime`, `fault` ou `observation`). `pending_command` signale un ordre en attente de confirmation. `fault_reason` impose de corriger le problème puis de l’acquitter explicitement dans les options ; l’intégration ne relance pas rapidement le switch.

En cas de défaut verrouillé, corrigez d'abord sa cause puis cochez **Acquitter et réinitialiser un défaut verrouillé** dans les options. Cette action recharge l'intégration ; elle ne force pas de commande immédiate. Les attributs `control_state`, `fault_reason`, `pending_command`, `heater_available` et `fallback_reason` permettent d'examiner la situation sans exposer les références privées des sources dans les diagnostics.

L'action `predictive_thermostat.reset_fault` permet aussi d'acquitter le défaut sans ouvrir les options. Elle refuse l'acquittement si l'état du chauffage n'est pas confirmé. Une ancienne commande encore en attente est abandonnée au profit de l'état `on` ou `off` réellement observé, puis les protections de cycle redémarrent intégralement avant toute nouvelle commande.

La carte fournie ajoute ces actions à la carte thermostat. Le bouton d’informations natif conserve le dialogue Home Assistant standard et un bouton **Détails prédictifs**, placé sous le réglage de température, ouvre les informations propres à l’intégration :

```yaml
type: custom:predictive-thermostat-card
entity: climate.poele
name: Poêle
```

N'utilisez `confirmed_off_period: true` que lorsque le chauffage est resté réellement hors tension assez longtemps. Un acquittement ordinaire conserve le redémarrage complet de `min_off` et du cooldown afin d'empêcher les répétitions rapides après un simple défaut de commande.

La confirmation de durée d'arrêt reste applicable si le défaut a déjà disparu après le redémarrage. Elle exige toujours un switch à `off` et refuse d'annuler une commande active.

La [documentation de la carte Lovelace](docs/LOVELACE.md) détaille son installation, les informations affichées et les deux réinitialisations. Sa ressource est chargée automatiquement par l’intégration et ne demande pas une seconde installation HACS.

## Limites connues

- L’actionneur V1 est un `switch` uniquement ; les scripts et entités climate comme actionneurs ne sont pas encore pris en charge.
- La prévision météo est facultative et se replie sur la sonde extérieure locale. Aucune météo distante n’est imposée.
- La confiance du modèle est un indicateur interne, pas une garantie de précision thermique.
- L’intégration ne remplace jamais les sécurités internes, thermostats de sûreté ou consignes du fabricant.

## Mise à jour, suppression et dépannage

Pour mettre à jour, remplacez le seul dossier de l'intégration puis redémarrez Home Assistant. Pour la retirer, supprimez d'abord son entrée dans **Appareils et services**, puis son dossier si aucune zone ne l'utilise. Le déchargement et la suppression n'envoient aucune commande au switch.

- **Sonde intérieure indisponible ou trop ancienne** : la régulation suspend les nouvelles demandes de chauffe, conserve l'entité climate visible et crée une notification persistante. Cette notification se ferme après la prochaine mesure intérieure valide. Les protections de durée minimale restent prioritaires.
- **Switch indisponible** : une fois le switch de nouveau confirmé `on` ou `off`, le défaut d'indisponibilité est levé automatiquement. Les protections de cycle repartent de l'état observé. Les défauts de commande, de timeout ou de stockage restent verrouillés et demandent un acquittement dans les options.
- **Mode HEAT ne change rien** : vérifiez d'abord que le mode observation est toujours actif ; c'est le comportement prévu par défaut.
- **Intégration absente** : vérifiez le chemin de `manifest.json`, redémarrez HA et consultez les journaux de chargement.

Les diagnostics expurgent les noms et identifiants de sources, les mesures et les données d'apprentissage. Le stockage privé conserve seulement l'état de contrôle nécessaire à une reprise sûre ; il est versionné et validé avant lecture.

## Développement

Voir [le guide de développement](docs/DEVELOPMENT.md). Les tests n'utilisent que des entités factices et ne contactent pas une installation Home Assistant domestique. L'audit local d'installation est ignoré par Git et ne fait pas partie de la distribution.

Avant toute installation, suivre la [checklist d’instance de test](docs/V1_TEST_INSTANCE.md). Elle permet de vérifier le planning, le fallback météo, les protections de cycle et le mode observation sans poêle réel.
