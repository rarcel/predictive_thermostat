# Préparer une instance de test V1

1. Utiliser une instance Home Assistant de test et copier uniquement `custom_components/predictive_thermostat`.
2. Créer des sondes factices intérieure et extérieure, un switch factice et, si nécessaire, une entité météo de test.
3. Ajouter une seule zone Predictive Thermostat et laisser le mode observation activé.
4. Vérifier les attributs de planning, de préchauffage, de fallback et d’apprentissage pendant plusieurs transitions planifiées.
5. Vérifier qu’une prévision indisponible revient à la sonde extérieure locale et qu’aucune commande n’est répétée.
6. Ne désactiver le mode observation qu’après validation des polarités, durées minimales, cooldown, automatisations concurrentes et protections du fabricant.

Cette procédure ne constitue pas une autorisation d’essai sur le poêle réel. Toute activation matérielle exige une décision explicite et la présence d’une personne.
