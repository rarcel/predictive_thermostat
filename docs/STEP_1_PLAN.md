# Décisions proposées et plan de l'étape 1

Statut : plan initial approuvé puis implémenté localement au jalon 0.1.0. Voir README.md et DEVELOPMENT.md pour les capacités livrées et leur validation. Les propositions pour les étapes ultérieures restent distinctes de ce scaffold.

## Invariants applicables à chaque décision

Une seule entité climate principale par zone ; planning interne avec température à atteindre à l'heure indiquée ; température extérieure dans la prédiction ; modèle local, léger et explicable ; aucune commande courte ou répétée ; protections matérielles prioritaires ; observation avant activation réelle. Les décisions ci-dessous sont toutes subordonnées à ces sept invariants. Le Core generic_thermostat et l'installation existante restent intacts.

## API vérifiées

Référence cible : **Core 2026.9.3**, version observée par MCP. Vérification du code public au tag correspondant et des documents officiels, sans exécuter du code sur HA. Ce contrôle documentaire ne vaut pas test d'installation.

| Sujet | Vérification et choix |
| --- | --- |
| Python | Le [pyproject au tag 2026.9.3](https://raw.githubusercontent.com/home-assistant/core/2026.9.3/pyproject.toml) exige >=3.14.2. Tester d'abord HA 2026.9.3 sur Python 3.14 compatible, sous Linux en CI ; aucune compatibilité ancienne annoncée sans tests. |
| ClimateEntity | Le [code climate](https://raw.githubusercontent.com/home-assistant/core/2026.9.3/homeassistant/components/climate/__init__.py) expose l'adaptation async dont async_set_temperature. Les [enums du tag](https://raw.githubusercontent.com/home-assistant/core/2026.9.3/homeassistant/components/climate/const.py) contiennent OFF, HEAT, AUTO et HVACAction.PREHEATING. Étape 1 : OFF uniquement et action OFF, lecture intérieure et attribut control_state=observation ; ne pas annoncer une chauffe simulée comme une action physique. HEAT étape 2, AUTO étape 3, PREHEATING seulement lors d'une chauffe anticipée confirmée. |
| Config Flow | [Documentation officielle](https://developers.home-assistant.io/docs/core/integration/config_flow/) : manifest config_flow=true, classe ConfigFlow avec domain, étapes async_step_*, VERSION et création d'entrée. La documentation actuelle emploie probatio, également dépendance du tag : ne pas recopier aveuglément un ancien exemple voluptuous. Sélecteurs sensor/temperature pour les sondes et switch pour l'actionneur ; validation côté serveur également. |
| Cycle Config Entry | [Code du tag](https://raw.githubusercontent.com/home-assistant/core/2026.9.3/homeassistant/config_entries.py) : attendre async_forward_entry_setups ; async_unload_platforms pour le déchargement ; runtime_data pour l'état typé. Conserver les désabonnements et les exécuter au retrait. |
| Options Flow | [Documentation](https://developers.home-assistant.io/docs/core/integration/options_flow/) et code config_entries du tag : OptionsFlowWithReload recharge après changement d'options. Ne pas lui ajouter un update listener. Utiliser self.config_entry fourni par HA. Éditeur de planning guidé à l'étape 3, pas de formulaire matériel actif à l'étape 1. |
| Stockage | [Store au tag](https://raw.githubusercontent.com/home-assistant/core/2026.9.3/homeassistant/helpers/storage.py) : version, minor_version, private=True, atomic_writes=True ; async_load, async_save/async_delay_save et migration _async_migrate_func(old_major_version, old_minor_version, old_data). Réserver ce stockage aux données agrégées et métadonnées de sécurité, avec validation du schéma ; ce flag private n'est pas un chiffrement. Implémentation aux incréments concernés. |
| Événements et timers | [Helpers event au tag](https://raw.githubusercontent.com/home-assistant/core/2026.9.3/homeassistant/helpers/event.py) : async_track_state_change_event et async_track_point_in_utc_time renvoient des callbacks d'annulation. Un seul rappel métier reprogrammable, annulation de l'ancien avant remplacement et au déchargement. Horloge injectée dans le cœur ; durées de protection mesurées avec une horloge monotone en session. |
| Diagnostics | [Documentation officielle](https://developers.home-assistant.io/docs/core/integration/diagnostics/) : async_get_config_entry_diagnostics et async_redact_data. Préférer un résumé construit par liste blanche ; exclure entités/noms privés, planning détaillé, coefficients et historique. Ne pas sérialiser runtime_data ou l'entrée entière sans filtrage. |

La tentative de consultation du config_flow de generic_thermostat a échoué ; aucune conclusion n'en dépend. Les API ci-dessus seront confirmées par les tests sur la version épinglée au scaffold. La disponibilité d'un environnement Python local et la compatibilité du paquet de fixtures HA restent à vérifier à cette étape.

## Composant générique et paramétrable

L'intégration est destinée à plusieurs utilisateurs et installations. INSTALLATION_AUDIT.md est un cas de validation, pas la configuration par défaut du produit. L'utilisateur confirme que climate.poele fonctionne correctement et que le poêle est simplement débranché : le projet n'a pas pour objectif de réparer le contrôle existant.

- Config Flow : nom de zone, choix des sondes intérieure/extérieure et de l'actionneur compatible, sans référence imposée à ESPHome, Zigbee2MQTT ou aux entités de l'audit. V1 : actionneur switch ; abstraction extensible pour d'autres méthodes ultérieurement.
- Options Flow, au fil des incréments : planning, bornes de consigne et pas, hystérésis, polarité logique si nécessaire, marche minimale, arrêt minimal, cooldown, timeout de confirmation, délai d'allumage, vitesse initiale de chauffe, marge de pertes, bornes d'anticipation, fraîcheur des sondes et fallback extérieur, apprentissage et observation. Chaque paramètre précise unité, domaine valide et effet ; les changements structurels déclenchent un rechargement propre.
- Les valeurs initiales générales sont documentées et validées ; les valeurs issues de cet audit sont seulement des propositions pour cette installation. Aucun nom d'entité, planning domestique, seuil 15–24 °C ou fuseau Europe/Paris ne sera codé en dur. Le fuseau provient de Home Assistant ; les températures sont converties depuis les unités déclarées vers une unité interne cohérente et affichées selon les unités configurées dans HA.
- Chaque zone possède son planning, son modèle et ses paramètres privés. Les éventuelles automatisations de ralenti, ventilation, présence ou entretien appartiennent à l'installation et ne sont pas requises par le composant.
- Les tests utilisent des entités factices et plusieurs configurations : noms arbitraires, sources d'intégrations différentes, limites distinctes, unités °C/°F et fuseaux avec/sans DST aux incréments concernés. Le scaffold vérifie déjà que les entités sélectionnées, et aucune entité domestique implicite, sont utilisées.

Ces paramètres respectent les sept invariants ci-dessus : une configuration ne permet jamais au modèle prédictif de contourner les protections, d'augmenter la cible ou de commander en observation. La généralité n'ajoute pas de helpers ni de second chauffage par zone.

## Décisions logicielles recommandées

1. **Intégration autonome et identité** : une Config Entry par zone ; UUID durable généré à la création, utilisé pour le unique_id du climate et le device virtuel. Références aux sources résolues via le registre quand possible ; ne pas dériver l'identité de la zone d'un entity_id. Refuser une seconde entrée utilisant le même actionneur ; prévoir tests de renommage/rechargement.
2. **Observation dès le scaffold** : aucune voie d'appel de service chauffage à l'étape 1. L'option d'activation réelle n'est pas proposée avant le contrôleur sûr. La lecture d'une sonde indisponible dégrade l'état sans activer le chauffage. L'interface doit expliquer que l'intégration observe et ne régule pas encore.
3. **Contrôle futur** : HeaterAdapter switch unique et cycle_controller autorité finale ; distinguer accusé d'état du relais et chauffe physique. Une commande en attente bloque les doublons ; expiration => défaut persistant, sans retry automatique rapide. OFF est une demande d'arrêt soumise aux protections ; ne pas présenter ce bouton comme un arrêt d'urgence matériel.
4. **Planning futur** : stockage hebdomadaire en heure locale dans le fuseau configuré dans Home Assistant (Europe/Paris pour l'installation auditée), objectifs triés et uniques, dernière cible reconduite sur les jours sans point, semaine vide refusée. Hausse anticipée sans dépasser la prochaine cible ; dérogation jusqu'au prochain point. Proposition DST : heure inexistante reportée au premier instant valide, heure répétée exécutée une seule fois à la première occurrence ; définir la priorité en cas de collision après report et la tester (dernier point nominal applicable).
5. **Prédiction future** : fallback borné avec gain intérieur et pertes liées à l'extérieur, puis régression robuste minimale sans interaction initiale. Aucun coefficient appris avec cet historique. Sonde extérieure périmée => dégradation explicite, sans dépendance météo distante. Les paramètres de simulation ne sont pas une validation matérielle.
6. **Migration réelle différée** : conserver le thermostat actuel pendant l'observation, puis préparer un basculement garantissant un seul contrôleur effectif et une seule entité principale au quotidien. Les commandes de ralenti et le thermostat salle_manger demandent une décision spécifique ; ne pas ajouter silencieusement un second actionneur à la V1.

Les paramètres constructeur, l'emplacement des sondes, le planning souhaité et le lien entre thermostats restent à confirmer avant mise en service. Ils ne bloquent pas l'étape 1. La règle DST et la politique de défaut sont des recommandations à valider, pas des faits observés.

## Incrément vertical proposé

1. Vérifier l'environnement de tests et épingler les dépendances compatibles avec HA 2026.9.3 / Python >=3.14.2.
2. Écrire les tests de flow, validation, identité, création d'une seule entité, setup/unload/reload et observation sans appels de services.
3. Créer le manifeste, le Config Flow minimal (zone, sondes, switch candidat), les traductions anglaise/française et l'entité passive. Une source temporairement indisponible peut être sélectionnée si son registre valide son type ; aucune validation ne doit allumer un appareil.
4. Ajouter les tests de changement de mesure, données invalides, listeners retirés, stabilité d'identité, diagnostic expurgé et absence de commande à chaque transition du cycle de vie.
5. Exécuter localement Ruff, mypy et tous les tests sur la version épinglée, puis valider le manifeste. Documenter l'installation sur instance factice et les limites OFF/observation. Aucun test sur l'instance domestique.

Pas de moteur prédictif, de planning opérationnel, de commande switch, d'apprentissage ni de déploiement pendant cet incrément. L'architecture réserve schedule.py, model.py, cycle_controller.py, observations.py, storage.py et un adaptateur, créés uniquement avec leurs incréments et tests. Aucun coordinator, services.yaml ou capteur supplémentaire sans besoin démontré.

## Liste exacte des fichiers à créer à l'étape 1

```text
.gitignore
pyproject.toml
requirements_test.txt
custom_components/predictive_thermostat/__init__.py
custom_components/predictive_thermostat/manifest.json
custom_components/predictive_thermostat/const.py
custom_components/predictive_thermostat/config_flow.py
custom_components/predictive_thermostat/climate.py
custom_components/predictive_thermostat/diagnostics.py
custom_components/predictive_thermostat/strings.json
custom_components/predictive_thermostat/translations/en.json
custom_components/predictive_thermostat/translations/fr.json
tests/__init__.py
tests/conftest.py
tests/test_config_flow.py
tests/test_init.py
tests/test_climate.py
tests/test_diagnostics.py
tests/test_translations.py
docs/DEVELOPMENT.md
```

Les fichiers ci-dessus ont été créés ; README.md et docs/ROADMAP.md ont été mis à jour. sources.py a été ajouté pour isoler la résolution des références et les conversions, et tests/test_zones.py pour les scénarios multi-zones et de restauration. L'Options Flow de sélection des sources est livré dès ce jalon dans config_flow.py ; l'éditeur du planning reste à l'étape 3. Aucun état partagé ne justifie encore runtime_data. Le code HA installé utilise voluptuous dans ses sélecteurs ; cette API est utilisée et testée dans le scaffold. Les URL de dépôt du manifeste seront déterminées à partir du dépôt réel, pas inventées.
