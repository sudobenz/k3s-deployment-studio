# Sécurité

- Aucun secret dans tfvars, deployment.json, inventaire ou journaux.
- Le token Proxmox est injecté via `TF_VAR_proxmox_api_token` au processus Terraform. En production, intégrer Windows Credential Manager, Secret Service/libsecret ou macOS Keychain.
- TLS Proxmox vérifié ; pas de mode insecure dans l'UI.
- SSH host key checking activé ; enrôler les empreintes avant Ansible.
- Les proxies authentifiés ne doivent pas contenir de mot de passe dans les variables persistées.
- `terraform apply` demande une confirmation ; aucun destroy automatique.
- Le state Terraform contient des métadonnées sensibles et doit être protégé.
