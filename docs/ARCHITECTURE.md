# Architecture

Application native PySide6 : aucun serveur HTTP ni navigateur intégré.

- `app/ui` : assistant graphique.
- `app/core/models.py` : modèle de configuration et validations.
- `app/core/generator.py` : génération Terraform, inventaire et playbooks Ansible.
- `terraform` : provider Proxmox `bpg/proxmox`, clones cloud-init depuis un template.
- `ansible` : préparation OS et proxy.
- `os-profiles` : profils de qualification par distribution.
- `imported-kit` : archive Authentik ou Keycloak conservée sans modification.

Le nombre de machines est une collection dynamique, bornée à 1–20 dans le MVP. L'interface permet d'ajouter/supprimer des machines ou de saisir directement le nombre souhaité.
