# Carte thermostat avec actions d’acquittement

Cette composition utilise uniquement des cartes natives Home Assistant. Elle conserve la carte `thermostat` officielle et place dessous deux raccourcis vers `predictive_thermostat.reset_fault`. Elle ne nécessite aucune ressource JavaScript ni carte HACS.

Dans l’éditeur du tableau de bord, ajoutez une carte manuelle puis collez :

```yaml
type: vertical-stack
cards:
  - type: thermostat
    entity: climate.poele
    name: Poêle
  - type: grid
    columns: 2
    square: false
    cards:
      - type: shortcut
        label: Acquitter
        icon: mdi:alert-circle-check
        tap_action:
          action: perform-action
          perform_action: predictive_thermostat.reset_fault
          target:
            entity_id: climate.poele
      - type: shortcut
        label: Reprendre après coupure
        icon: mdi:power-cycle
        tap_action:
          action: perform-action
          perform_action: predictive_thermostat.reset_fault
          target:
            entity_id: climate.poele
          data:
            confirmed_off_period: true
          confirmation:
            text: >-
              Confirmer que le chauffage est réellement resté hors tension
              pendant au moins la durée minimale d’arrêt et le cooldown ?
```

Le bouton **Acquitter** conserve toutes les temporisations de protection. Le bouton **Reprendre après coupure** exige que le switch soit réellement `off`, puis considère `min_off` et le cooldown comme déjà écoulés. Sa confirmation ne doit être validée qu’après une coupure assez longue ayant réellement privé le chauffage d’alimentation.

Pour une autre zone, remplacez les deux occurrences de `climate.poele` par l’identifiant de son thermostat prédictif. Le champ `name` est facultatif.

Sur une version Home Assistant antérieure à 2026.5 qui ne connaît pas la carte `shortcut`, remplacez chaque `type: shortcut` par `type: button` et `label` par `name`. Les actions restent identiques.
