# Proxmox VE

Le premier backend cible Proxmox VE via le provider Terraform `bpg/proxmox`. Le MVP clone un template cloud-init existant, configure CPU/RAM/disques/réseau et fournit les IP statiques.

Préparer dans Proxmox un template Linux cloud-init avec QEMU Guest Agent, stockage et bridge valides. `template_vm_id` doit référencer ce template. Le token API doit être limité aux permissions nécessaires au clone/configuration/démarrage des VM et à l'allocation du stockage.

Le MVP ne fabrique pas encore un template à partir d'une ISO brute. Une ISO sélectionnée est stockée dans le profil de déploiement et doit être associée à un profil unattended qualifié avant l'implémentation du workflow ISO complet.
