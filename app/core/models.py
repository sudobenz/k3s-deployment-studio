from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any
import ipaddress, re

@dataclass
class Machine:
    name: str
    ipv4_cidr: str
    gateway: str
    dns: str
    vcpu: int = 4
    memory_mb: int = 8192
    system_disk_gb: int = 100
    data_disk_gb: int = 200

@dataclass
class DeploymentConfig:
    project_name: str = "k3s-ha-deployment"
    kit: str = "authentik"
    proxmox_endpoint: str = "https://pve.example.invalid:8006/"
    proxmox_node: str = "pve1"
    storage: str = "local-lvm"
    bridge: str = "vmbr0"
    template_vm_id: int = 9000
    iso_path: str = ""
    os_family: str = "ubuntu"
    os_version: str = "24.04"
    install_method: str = "cloud-init-template"
    custom_profile: str = ""
    http_proxy: str = ""
    https_proxy: str = ""
    no_proxy: str = "localhost,127.0.0.1,::1"
    ca_certificate: str = ""
    ssh_user: str = "deployer"
    ssh_public_key: str = ""
    machines: list[Machine] | None = None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["machines"] = [asdict(m) for m in (self.machines or [])]
        return data


def validate_config(c: DeploymentConfig) -> list[str]:
    errors=[]
    if not re.fullmatch(r"[a-z][a-z0-9-]{1,38}", c.project_name): errors.append("Nom de projet invalide (minuscules, chiffres, tirets).")
    if c.kit not in {"authentik", "keycloak"}: errors.append("Kit cible invalide.")
    if not c.proxmox_endpoint.startswith("https://"): errors.append("L'API Proxmox doit utiliser HTTPS.")
    if not c.proxmox_node: errors.append("Nœud Proxmox obligatoire.")
    if not c.storage or not c.bridge: errors.append("Stockage et bridge Proxmox obligatoires.")
    if c.template_vm_id < 100: errors.append("template_vm_id doit être supérieur ou égal à 100.")
    if not c.machines: errors.append("Au moins une machine doit être définie.")
    if len(c.machines or []) > 20: errors.append("Maximum MVP : 20 machines.")
    names=set(); ips=set()
    for i,m in enumerate(c.machines or [],1):
        if not re.fullmatch(r"[a-zA-Z][a-zA-Z0-9-]{1,62}",m.name): errors.append(f"Machine {i}: hostname invalide.")
        if m.name.lower() in names: errors.append(f"Machine {i}: hostname dupliqué.")
        names.add(m.name.lower())
        try:
            iface=ipaddress.ip_interface(m.ipv4_cidr)
            if iface.version != 4: raise ValueError()
            if str(iface.ip) in ips: errors.append(f"Machine {i}: adresse IP dupliquée.")
            ips.add(str(iface.ip))
            gw=ipaddress.ip_address(m.gateway)
            if gw not in iface.network: errors.append(f"Machine {i}: passerelle hors du réseau {iface.network}.")
            if gw.version != 4: raise ValueError()
            for d in [x.strip() for x in m.dns.split(",") if x.strip()]:
                if ipaddress.ip_address(d).version != 4: raise ValueError()
        except ValueError:
            errors.append(f"Machine {i}: IPv4/CIDR, passerelle ou DNS invalide.")
        if m.vcpu < 1 or m.vcpu > 128: errors.append(f"Machine {i}: vCPU doit être compris entre 1 et 128.")
        if m.memory_mb < 1024 or m.memory_mb > 1048576: errors.append(f"Machine {i}: RAM doit être comprise entre 1024 et 1048576 Mo.")
        if m.system_disk_gb < 30: errors.append(f"Machine {i}: disque système minimum 30 Go.")
        if m.data_disk_gb < 0: errors.append(f"Machine {i}: disque données négatif.")
    if c.install_method == "custom" and (not c.iso_path or not Path(c.iso_path).is_file()): errors.append("ISO personnalisée introuvable.")
    if c.install_method == "custom" and not c.custom_profile: errors.append("Une ISO personnalisée exige un profil d'installation documenté.")
    if c.os_family == "custom" and c.install_method != "custom": errors.append("Pour un OS personnalisé, sélectionner le mode ISO personnalisée.")
    return errors
