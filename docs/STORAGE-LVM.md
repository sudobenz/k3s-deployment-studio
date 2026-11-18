# Partitionnement et LVM

Cible OS : GPT, EFI, /boot selon distribution, PV LVM, VG système et LV root utilisant `100%FREE` du VG. Le disque données est distinct, jamais ajouté au VG système, réservé à Longhorn.

Le playbook MVP ne formate aucun disque automatiquement. `/dev/sdb` n'est pas une identité fiable. Avant d'ajouter le rôle de formatage, exiger un identifiant `/dev/disk/by-id/`, vérifier taille/modèle/série, refuser le disque racine et demander une confirmation explicite.
