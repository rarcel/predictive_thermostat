# Modèle prédictif et apprentissage

## Objectif du modèle

Prédire le nombre de minutes nécessaires pour atteindre une cible future, avec une estimation de confiance :

`duration = f(T_inside, T_outside, T_target, recent_state)`

Le modèle doit être léger, explicable, robuste aux petites quantités de données et borné par des règles de sécurité.

## V0 — fallback conservateur

Avant apprentissage, utiliser :

`minutes = ignition_delay + degrees_to_gain / default_heating_rate + loss_margin`

où `loss_margin` augmente avec l'écart `T_inside - T_outside`. Toutes les valeurs sont configurables avec défauts prudents, puis l'estimation est bornée entre `min_preheat` et `max_preheat`.

## V1 — modèle recommandé

Commencer par une régression robuste sur la progression thermique ou la durée, avec caractéristiques peu nombreuses :

- degrés à gagner : `max(0, T_target - T_inside)` ;
- écart intérieur/extérieur : `T_inside - T_outside` ;
- interaction éventuelle entre degrés à gagner et écart intérieur/extérieur ;
- délai d'allumage estimé séparément.

Une forme initiale acceptable :

`minutes = c + a*gain + b*envelope_delta + d*gain*envelope_delta`

Ne conserver le terme d'interaction que si les données et les tests montrent qu'il améliore la stabilité. Le modèle sélectionné doit être documenté avec ses unités.

## Pourquoi ne pas faire du ML complexe

Le nombre de cycles domestiques est faible, les données sont bruitées et les changements (portes ouvertes, soleil, présence) ne sont pas tous observables. Un modèle complexe donnerait une confiance artificielle. La priorité est une correction progressive, plafonnée et observable.

## Construction d'un cycle exploitable

Un cycle commence lors de la confirmation réelle de chauffe, pas lors de la simple commande. Il se termine lorsque :

- la cible est atteinte ;
- le chauffage est arrêté ;
- la durée maximale est dépassée ;
- une donnée indispensable devient invalide ;
- une intervention manuelle rend l'observation ambiguë.

Enregistrer en mémoire puis agréger/persister :

- heure de commande et heure de chauffe confirmée ;
- températures intérieure/extérieure de départ ;
- cible ;
- durée jusqu'à cible ;
- température extérieure moyenne ou robuste durant le cycle ;
- maximum après atteinte/extinction pour estimer l'overshoot ;
- drapeaux de qualité.

## Rejet et pondération

Rejeter ou sous-pondérer :

- température intérieure indisponible ou sauts irréalistes ;
- changement manuel de cible en cours de cycle ;
- durée trop courte ;
- fenêtre comportant un redémarrage HA non réconcilié ;
- actionneur dont l'état réel est incertain ;
- pente incompatible avec le chauffage attendu ;
- température extérieure absente au-delà du fallback autorisé.

Utiliser une mise à jour robuste : poids décroissant des résidus extrêmes, taux d'apprentissage limité ou fenêtre glissante bornée. Un seul cycle ne peut jamais déplacer une prédiction de plus qu'un seuil configurable.

## Correction de l'erreur d'arrivée

Après un objectif programmé, calculer :

`arrival_error = actual_reach_time - target_time`

- positif : arrivée trop tardive ;
- négatif : arrivée trop précoce.

Mettre à jour une marge adaptative lentement et dans des bornes strictes. Ne pas confondre cette correction globale avec les paramètres physiques du modèle.

## Confiance

La confiance n'est pas une probabilité scientifique. C'est un indicateur borné `0..1` basé sur :

- nombre d'observations valides ;
- dispersion récente des erreurs ;
- distance entre les conditions courantes et les données déjà vues ;
- fraîcheur des données ;
- présence ou non de fallbacks.

Documenter précisément le calcul. Une confiance faible augmente éventuellement la marge de sécurité mais ne peut dépasser `max_preheat`.

## Overshoot

La V1 mesure l'overshoot mais ne met pas en œuvre un arrêt optimal prédictif. Elle peut réduire lentement la marge de préchauffage si une arrivée systématiquement trop tôt est confirmée. L'arrêt reste géré par cible, hystérésis et durée minimale de marche.

## Invariants de sécurité

- `min_preheat <= predicted_duration <= max_preheat`
- coefficients finis ; aucune valeur NaN/infini ne peut être persistée ;
- un modèle invalide est archivé/réinitialisé et le fallback est utilisé ;
- l'apprentissage ne commande jamais directement l'actionneur ;
- le contrôleur de cycle reste l'autorité finale.

