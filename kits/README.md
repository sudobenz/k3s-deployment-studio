# Archives de kits applicatifs

Ce répertoire ne contient volontairement aucune archive Authentik ou Keycloak.
Les kits sont distribués séparément de K3s Deployment Studio.

## Sélectionner un kit dans l'application

1. Ouvrir K3s Deployment Studio.
2. Dans l'onglet **Projet & OS**, choisir **authentik** ou **keycloak** dans le champ **Kit applicatif**.
3. Dans la fenêtre de sélection, choisir le fichier ZIP complet correspondant au kit sélectionné. Le fichier peut se trouver dans n'importe quel dossier du poste ; son nom est libre.
4. Vérifier que le nom de l'archive sélectionnée apparaît dans l'interface.

Le bouton **Choisir le ZIP…** permet de sélectionner une autre archive à tout moment.

L'application contrôle le type du kit à partir des scripts qui caractérisent son archive. Elle refuse une archive Keycloak lorsque le type Authentik est sélectionné, et inversement.

## Traitement de l'archive

Lors de la génération du projet, l'archive sélectionnée est copiée sans modification dans le dossier `imported-kit/` du workspace généré. L'application produit également un manifeste `config/kit-handoff.json` qui indique le type et le nom de l'archive retenue.

La sélection et la copie de l'archive ne lancent pas les scripts du kit. Les paramètres spécifiques à l'environnement doivent être vérifiés avant tout déploiement.

Les archives de kits ne doivent pas être ajoutées au dépôt Git de K3s Deployment Studio. Elles peuvent contenir des paramètres d'infrastructure ou des informations sensibles.
