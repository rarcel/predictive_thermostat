# Plan de tests

## Tests unitaires purs

### Planning

- cible courante et prochain objectif pour chaque jour ;
- passage dimanche/lundi ;
- plusieurs points dans une journée ;
- planning avec jours groupés puis normalisés ;
- changement d'heure été/hiver ;
- heure locale inexistante et heure répétée ;
- planning invalide ou doublon.

### Modèle

- prédiction fallback sans échantillon ;
- bornes minimale/maximale ;
- durée croissante quand les degrés à gagner augmentent ;
- effet cohérent d'une température extérieure plus froide ;
- données aberrantes rejetées ;
- mise à jour limitée après un cycle extrême ;
- sérialisation et migration ;
- confiance faible hors domaine appris.

### Contrôleur de cycle

- hystérésis standard ;
- durée minimale de marche prioritaire ;
- cooldown prioritaire ;
- absence de doubles commandes ;
- confirmation tardive de l'actionneur ;
- timeout et passage en défaut ;
- récupération après redémarrage ;
- passage `AUTO` / `HEAT` / `OFF` ;
- préchauffage annulé si la cible ou le planning change.

## Tests d'intégration Home Assistant

- Config Flow complet, doublons et aborts ;
- Options Flow et rechargement ;
- setup/unload/reload de Config Entry ;
- restauration après redémarrage ;
- changement d'état des capteurs ;
- commande réelle simulée du switch ;
- entité indisponible ;
- attributs et modes supportés ;
- diagnostics expurgés ;
- traductions présentes.

## Scénarios bout en bout simulés

1. **Matin froid sans apprentissage** : 17 °C dedans, -5 °C dehors, cible 20,5 °C à 07:00. Le fallback démarre dans la fenêtre bornée.
2. **Matin doux après apprentissage** : mêmes températures intérieure/cible, +12 °C dehors. Le démarrage est plus tardif que dans le scénario froid.
3. **Cooldown** : nouvelle demande pendant la période minimale d'arrêt. Aucun redémarrage avant échéance.
4. **Sonde extérieure perdue** : dernière valeur fraîche puis fallback ; aucune oscillation de commande.
5. **Redémarrage HA pendant chauffe** : état actionneur réconcilié ; pas de nouvelle commande ON dupliquée.
6. **Dérogation** : consigne manuelle en `AUTO`, maintenue jusqu'au prochain point puis reprise du planning.
7. **DST** : l'objectif reste attaché à l'heure locale selon la politique documentée.

## Critères de livraison

- tous les tests passent sur la matrice Python/HA définie par le projet ;
- lint et type-check passent ;
- aucune I/O bloquante détectée dans le chemin courant ;
- aucun callback/listener restant après unload ;
- aucun cycle court dans les scénarios de test ;
- installation et configuration documentées depuis une instance propre ;
- test manuel sur une entité factice avant tout essai sur le poêle réel.

## Validation réelle progressive

1. Mode observation uniquement : prédictions visibles, aucune commande.
2. Comparaison des prédictions aux cycles existants.
3. Essai commandé avec présence humaine et anticipation plafonnée.
4. Plusieurs jours avec revue des logs et erreurs d'arrivée.
5. Extension graduelle de la fenêtre d'anticipation.

Le mode observation est fortement recommandé avant activation réelle, même s'il est implémenté comme option avancée.

