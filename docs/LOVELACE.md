# Carte Predictive Thermostat

L’intégration fournit sa propre carte Lovelace. Elle reprend la carte thermostat officielle pour les commandes quotidiennes. Le bouton d’informations en haut à droite conserve exactement son comportement Home Assistant standard. Un bouton **Détails prédictifs** est affiché immédiatement sous la carte native, sans passer par le chargeur de fonctionnalités imbriquées du frontend.

Après l’installation ou la mise à jour, redémarrez Home Assistant puis rechargez complètement le navigateur. La ressource JavaScript est enregistrée automatiquement ; il n’est pas nécessaire de l’ajouter dans **Tableaux de bord > Ressources** ni d’installer une carte HACS séparée.

Dans l’éditeur du tableau de bord, ajoutez une carte manuelle :

```yaml
type: custom:predictive-thermostat-card
entity: climate.poele
name: Poêle
```

Seul `entity` est obligatoire. Il doit désigner l’entité `climate` créée par Predictive Thermostat. `name` remplace facultativement le nom affiché par la carte thermostat.

Le bouton **Détails prédictifs** ouvre un panneau qui présente notamment :

- l’état du contrôleur, la disponibilité du chauffage, un défaut éventuel et la commande en attente ;
- la température extérieure, la consigne planifiée et le prochain objectif ;
- l’heure de démarrage prévue, la durée de chauffe estimée et la confiance ;
- la température extérieure réellement utilisée et sa source (prévision ou sonde) ;
- le détail du calcul : allumage, montée en température, pertes extérieures, marge et correction d'arrivée ;
- la vitesse de chauffe et le facteur de pertes appris, le nombre de cycles et un éventuel motif de repli.

**Acquitter le défaut** conserve toutes les temporisations de protection. **Reprendre après coupure longue** exige une confirmation, vérifie que l’actionneur est réellement `off` et qu’aucune commande n’est en attente, puis considère la durée minimale d’arrêt et le cooldown comme écoulés. Cette seconde action ne doit être confirmée qu’après une coupure ayant réellement maintenu le chauffage hors tension assez longtemps.

La carte ne change ni le planning, ni les calculs, ni les protections matérielles. Une seule entité `climate` reste l’interface principale de chaque zone.

La ressource utilise une URL différente à chaque version et demande de ne pas être mise en cache. Cela évite qu'un reverse proxy qui ignore les paramètres de requête conserve une ancienne carte. Le proxy doit transmettre sans réécriture le chemin `/predictive_thermostat/` vers Home Assistant.

Si la carte affiche « Custom element doesn't exist » ou « Erreur de configuration », redémarrez Home Assistant, retirez toute ressource Predictive Thermostat ajoutée manuellement, videz le cache du site pour l'adresse concernée et faites un rechargement forcé. Vérifiez ensuite que la version chargée est au moins `0.7.5`.
