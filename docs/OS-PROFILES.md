# Profils OS et ISO

Catalogue prévu : Ubuntu, Debian, Rocky Linux, AlmaLinux, RHEL, SUSE/openSUSE et ISO custom.

Le MVP déploie par template cloud-init. Pour une ISO personnalisée, un profil unattended explicite est obligatoire. Méthodes usuelles : Ubuntu autoinstall, Debian preseed ou mécanisme supporté par la version, RHEL-like Kickstart, SUSE AutoYaST. Le contenu exact dépend de la version et de l'image. Ne jamais supposer qu'une ISO personnalisée accepte cloud-init.
