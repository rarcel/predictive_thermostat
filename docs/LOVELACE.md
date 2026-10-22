# Carte Predictive Thermostat

L’intégration fournit sa propre carte Lovelace. Elle reprend la carte thermostat officielle pour les commandes quotidiennes et réutilise son unique bouton d’informations en haut à droite. Ce bouton ouvre les informations de chauffe prédictive et les actions de réinitialisation, sans ajouter une seconde icône par-dessus la carte.

Après l’installation ou la mise à jour, redémarrez Home Assistant puis rechargez complètement le navigateur. La ressource JavaScript est enregistrée automatiquement ; il n’est pas nécessaire de l’ajouter dans **Tableaux de bord > Ressources** ni d’installer une carte HACS séparée.

Dans l’éditeur du tableau de bord, ajoutez une carte manuelle :

```yaml
type: custom:predictive-thermostat-card
entity: climate.poele
name: Poêle
```

Seul `entity` est obligatoire. Il doit désigner l’entité `climate` créée par Predictive Thermostat. `name` remplace facultativement le nom affiché par la carte thermostat.

Le panneau présente notamment :

- l’état du contrôleur, la disponibilité du chauffage, un défaut éventuel et la commande en attente ;
- la température extérieure, la consigne planifiée et le prochain objectif ;
- l’heure de démarrage prévue, la durée de chauffe estimée et la confiance ;
- la source de la prédiction, le nombre de cycles appris et un éventuel motif de repli.

**Acquitter le défaut** conserve toutes les temporisations de protection. **Reprendre après coupure longue** exige une confirmation, vérifie que l’actionneur est réellement `off` et qu’aucune commande n’est en attente, puis considère la durée minimale d’arrêt et le cooldown comme écoulés. Cette seconde action ne doit être confirmée qu’après une coupure ayant réellement maintenu le chauffage hors tension assez longtemps.

Le bouton **Informations Home Assistant** du panneau ouvre ensuite le dialogue standard de l’entité, avec son historique et ses réglages. Cette étape séparée évite de modifier les composants internes du frontend Home Assistant, qui ne fournissent pas d’API publique pour ajouter une section au dialogue `climate`.

La carte ne change ni le planning, ni les calculs, ni les protections matérielles. Une seule entité `climate` reste l’interface principale de chaque zone.

Si la carte affiche « Custom element doesn't exist », redémarrez Home Assistant, videz le cache de l’application ou faites un rechargement forcé de la page. Vérifiez ensuite que la version chargée de l’intégration est au moins `0.6.1`.
