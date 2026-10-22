# Modèle prédictif et apprentissage

## Objectif du modèle

Prédire le nombre de minutes nécessaires pour atteindre une cible future, avec une estimation de confiance :

`duration = f(T_inside, T_outside, T_target, recent_state)`

Le modèle doit être léger, explicable, robuste aux petites quantités de données et borné par des règles de sécurité.

## V0 — fallback conservateur

Avant apprentissage, utiliser :

`minutes = ignition_delay + degrees_to_gain / default_heating_rate + loss_margin`

où `loss_margin` augmente avec l'écart `T_inside - T_outside`. Toutes les valeurs sont configurables avec défauts prudents, puis l'estimation est bornée entre `min_preheat` et `max_preheat`.

## V1 — modèle implémenté

La durée courante est calculée en minutes par :

`ignition_delay + gain / learned_heating_rate + max(0, T_inside - T_outside_used) * learned_loss_factor + preheat_margin + mean_arrival_error`

`T_outside_used` est la prévision horaire à l'heure cible lorsqu'elle est disponible, sinon la sonde extérieure. Le résultat est borné entre `min_preheat` et `max_preheat`. L'entité `climate` expose la température et la source utilisées, chaque terme de cette somme ainsi que le résultat avant bornage.

La vitesse de chauffe est mise à jour sur les cycles confirmés jusqu'à la première atteinte de la consigne. Le facteur de pertes est ajusté lentement à partir de la durée résiduelle expliquée par l'écart intérieur/extérieur. La correction d'arrivée est une moyenne exponentielle lente et distincte des paramètres physiques.

## Évolution possible

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

Un cycle commence lors de la confirmation réelle de chauffe, pas lors de la simple commande. Il n'est ouvert que si la température intérieure est strictement inférieure à la cible. Sa mesure utile se termine à la première mesure valide qui atteint la cible, même si l'actionneur reste ensuite allumé à cause de sa durée minimale de marche ou de la régulation. Cette période postérieure ne doit jamais entrer dans l'estimation de la vitesse de chauffe.

Un cycle est abandonné sans apprentissage lorsque :

- le chauffage est arrêté avant que la cible soit atteinte ;
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

L'observation reste active après l'heure cible afin d'apprendre aussi un retard. Elle est abandonnée lors d'une consigne manuelle ou d'un changement de mode. Si la cible n'est toujours pas atteinte après `max_preheat`, l'erreur enregistrée est plafonnée à cette valeur.

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

- si la cible est déjà atteinte, `predicted_duration = 0` ; sinon `min_preheat <= predicted_duration <= max_preheat` ;
- coefficients finis ; aucune valeur NaN/infini ne peut être persistée ;
- un modèle invalide est archivé/réinitialisé et le fallback est utilisé ;
- l'apprentissage ne commande jamais directement l'actionneur ;
- le contrôleur de cycle reste l'autorité finale.

