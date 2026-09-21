# Architecture technique

## Modules

```text
custom_components/predictive_thermostat/
  __init__.py
  manifest.json
  const.py
  config_flow.py
  climate.py
  coordinator.py              # seulement si une coordination périodique est justifiée
  schedule.py
  model.py
  cycle_controller.py
  observations.py
  storage.py
  diagnostics.py
  services.yaml               # uniquement si des services sont réellement nécessaires
  strings.json
  translations/en.json
  translations/fr.json
tests/
  ...
```

Les noms peuvent évoluer, mais les responsabilités doivent rester séparées.

## Flux de décision

1. Un changement de température, d'état actionneur, d'option ou une échéance planifiée réveille le moteur.
2. Le scheduler résout la cible active et le prochain objectif.
3. Le modèle estime la durée nécessaire et sa confiance.
4. Le moteur détermine si la fenêtre de préchauffage a commencé.
5. Le contrôleur de cycle applique hystérésis et contraintes matérielles.
6. L'adaptateur Home Assistant envoie au plus une commande nécessaire.
7. Les transitions réelles alimentent l'observateur de cycle.
8. Une observation valide met à jour le modèle de façon bornée puis le persiste.

## Modèle d'état de contrôle

États internes suggérés :

- `off`
- `idle`
- `waiting_for_preheat`
- `preheating`
- `heating`
- `minimum_runtime`
- `cooldown`
- `actuator_starting`
- `actuator_stopping`
- `fault`

Ces états internes ne doivent pas être confondus avec les enums exposés par `ClimateEntity`.

## Actionneur

La V1 doit supporter au minimum un `switch`. Prévoir une abstraction (`HeaterAdapter`) afin d'ajouter plus tard un `climate`, un script ou des services spécifiques sans contaminer le moteur métier.

Interface conceptuelle :

```python
class HeaterAdapter(Protocol):
    async def async_turn_on(self) -> None: ...
    async def async_turn_off(self) -> None: ...
    def observed_state(self) -> HeaterObservedState: ...
```

Ne jamais déduire qu'une commande a réussi de l'absence d'exception : attendre l'état observé, avec timeout et politique de défaut.

## Événements plutôt que polling excessif

Écouter les changements des sondes et de l'actionneur. Programmer un rappel exactement au prochain instant intéressant : début prédit, transition du planning, fin d'une protection ou expiration d'un timeout. Un contrôle périodique lent peut servir de filet de sécurité, pas de moteur principal.

Lorsqu'une nouvelle température change fortement la prédiction, reprogrammer proprement le rappel sans dupliquer les callbacks.

## Planning et temps

- Utiliser le fuseau horaire configuré dans Home Assistant.
- Stocker le planning sous forme locale (jour, heure, température), jamais comme timestamp UTC permanent.
- Convertir chaque occurrence en date/heure consciente du fuseau.
- Définir et tester le comportement lors d'une heure inexistante ou répétée au changement DST.
- Une semaine vide ou invalide doit être refusée par le flow.

## Persistance

Séparer :

- configuration utilisateur durable dans la Config Entry / Options ;
- état appris et observations agrégées dans un stockage interne versionné ;
- état volatil de commande en mémoire, avec suffisamment de métadonnées persistées pour un redémarrage sûr.

Le format contient au minimum `schema_version`, coefficients/paramètres, statistiques suffisantes, nombre d'échantillons et derniers timestamps pertinents. Prévoir une migration explicite pour chaque changement de schéma.

## Entités et appareils

- Une entité `climate` activée par défaut.
- Les capteurs diagnostiques additionnels sont hors V1 ; préférer attributs et diagnostics.
- Associer l'entité à un device virtuel représentant le thermostat, sans revendiquer le device des sondes ou du poêle.
- Utiliser une identité stable dérivée de l'identifiant unique de la Config Entry, pas des noms d'entités.

## API du planning

Le planning est édité via l'Options Flow. Si l'UI standard ne permet pas un éditeur hebdomadaire ergonomique en une page, utiliser une séquence guidée simple. Ne pas ajouter de frontend custom en V1.

Le stockage conceptuel recommandé :

```json
{
  "monday": [{"time": "07:00", "temperature": 20.5}],
  "tuesday": [{"time": "07:00", "temperature": 20.5}]
}
```

Normaliser, trier et valider avant sauvegarde. Interdire deux objectifs à la même heure le même jour.

## Audit MCP

L'audit de l'installation réelle sert à produire un fichier local `docs/INSTALLATION_AUDIT.md` non générique contenant les entités proposées, leurs capacités et les contraintes observées. L'audit ne doit pas modifier Home Assistant. Ne jamais committer de secret ou de données privées brutes.

