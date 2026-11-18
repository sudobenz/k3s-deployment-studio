# Avant production

1. Qualifier et construire les templates cloud-init par distribution/version.
2. Développer le vrai workflow ISO Proxmox : upload, média de réponse, boot order, console, détection de fin, installation et conversion en template.
3. Ajouter matrice de compatibilité OS × K3s × Authentik/Keycloak.
4. Développer les adaptateurs de kit : lire config.env, mapper IP/VIP/proxy/stockage puis exécuter les scripts dans un ordre validé.
5. Intégrer un coffre de secrets OS.
6. Ajouter VMware/Hyper-V/Libvirt après Proxmox.
7. Qualifier les profils unattended pour chaque version de distribution.
8. Identifier les disques par /dev/disk/by-id/ et valider le serial avant formatage Longhorn.
9. Tests E2E sur Proxmox de laboratoire : reboot, SSH, proxy d'entreprise et installation hors ligne.
