# Changelog

## 0.6.1

- Supprime le bouton menu ajouté par la carte, qui recouvrait le bouton natif du thermostat.
- Réutilise le bouton d’informations Home Assistant existant pour ouvrir les données prédictives et les actions de réinitialisation.
- Conserve un accès explicite au dialogue Home Assistant standard depuis le panneau prédictif.

## 0.6.0

- Fournit une véritable carte Lovelace qui réutilise la carte thermostat native.
- Ajoute un menu dépliant avec les données de chauffe prédictive et les deux actions de réinitialisation.
- Charge automatiquement la ressource de la carte avec l’intégration, y compris lors d’une installation HACS.

## 0.5.7

- Applique `confirmed_off_period` même lorsque le défaut a déjà été effacé pendant le redémarrage.
- Refuse toujours cette confirmation si le chauffage est `on`, indisponible ou si une commande active est encore en attente.

## 0.5.6

- Ajoute à `predictive_thermostat.reset_fault` l'option explicite `confirmed_off_period` pour reprendre après une coupure prolongée.
- Cette option exige un état réel `off` et considère alors `min_off` et le cooldown comme déjà écoulés ; l'acquittement ordinaire reste conservateur.

## 0.5.5

- Limite chaque échantillon d'apprentissage à la période entre l'allumage confirmé et la première atteinte de la consigne.
- Exclut de la vitesse apprise la marche minimale, le dépassement et la régulation après la consigne.
- Ramène la durée prédite à zéro lorsque la prochaine consigne est déjà atteinte.

## Maintenance

- Retire le workflow GitHub Actions non fonctionnel ; les commandes locales de validation restent documentées.
- Ajoute une composition Lovelace native réunissant la carte thermostat et les deux actions d’acquittement.

## 0.5.4

- Permet à l'action d'acquittement d'abandonner une ancienne commande non confirmée lorsque le switch expose désormais un état réel `on` ou `off`.
- Redémarre la durée minimale et le cooldown depuis cet état confirmé avant toute nouvelle commande.

## 0.5.3

- Nettoie la notification persistante dès que le défaut est acquitté, y compris après un rechargement de l'intégration.
- Ajoute l'action administrateur `predictive_thermostat.reset_fault`, ciblée sur l'entité climate, avec vérification de l'état réel de l'actionneur et redémarrage des protections de cycle.

## 0.5.2

- Corrige l'acquittement d'un défaut verrouillé lors du rechargement des options.

## 0.5.1

- Classifie l’intégration comme service afin qu’elle apparaisse dans la liste des intégrations, plutôt que seulement parmi les entrées de helper.

## 0.5.0

- Entité climate unique avec OFF, HEAT et AUTO, planning hebdomadaire et dérogation.
- Prévision fallback locale, apprentissage borné, météo facultative et arrêt optimal désactivé par défaut.
- Protections de cycle, persistance privée migrable, diagnostics expurgés et support HACS.

## Recette

Suivre `docs/V1_TEST_INSTANCE.md` sur une instance Home Assistant de test, avec le mode observation activé. Une recette matérielle exige une validation explicite distincte.
