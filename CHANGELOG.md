# Changelog

## 0.5.5

- Limite chaque échantillon d'apprentissage à la période entre l'allumage confirmé et la première atteinte de la consigne.
- Exclut de la vitesse apprise la marche minimale, le dépassement et la régulation après la consigne.
- Ramène la durée prédite à zéro lorsque la prochaine consigne est déjà atteinte.

## Maintenance

- Retire le workflow GitHub Actions non fonctionnel ; les commandes locales de validation restent documentées.

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
