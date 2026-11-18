from pathlib import Path
import json, yaml, shutil
from .models import DeploymentConfig
from .kit_archive import validate_kit_archive


def generate_project(c: DeploymentConfig, out: Path, kit_archive: str = "") -> list[Path]:
    if not kit_archive:
        raise ValueError(f"Une archive ZIP du kit {c.kit.capitalize()} doit être sélectionnée.")
    kit_archive_path = validate_kit_archive(kit_archive, c.kit)
    out.mkdir(parents=True, exist_ok=True)
    (out/"terraform").mkdir(exist_ok=True)
    (out/"ansible"/"playbooks").mkdir(parents=True,exist_ok=True)
    (out/"config").mkdir(exist_ok=True)
    files=[]
    def write(path, content):
        p=out/path; p.parent.mkdir(parents=True,exist_ok=True); p.write_text(content,encoding="utf-8"); files.append(p); return p
    cfg=c.to_dict()
    write(Path("deployment.json"),json.dumps(cfg,indent=2,ensure_ascii=False))
    tfvars={"proxmox_endpoint":c.proxmox_endpoint,"proxmox_node":c.proxmox_node,"storage":c.storage,"bridge":c.bridge,"template_vm_id":c.template_vm_id,"ssh_user":c.ssh_user,"machines":[{"name":m.name,"ipv4_cidr":m.ipv4_cidr,"gateway":m.gateway,"dns":m.dns,"vcpu":m.vcpu,"memory_mb":m.memory_mb,"system_disk_gb":m.system_disk_gb,"data_disk_gb":m.data_disk_gb} for m in c.machines]}
    write(Path("terraform/terraform.tfvars.json"),json.dumps(tfvars,indent=2))
    write(Path("terraform/versions.tf"),'''terraform {\n  required_version = ">= 1.8.0"\n  required_providers {\n    proxmox = { source = "bpg/proxmox", version = "~> 0.80" }\n  }\n}\n''')
    write(Path("terraform/provider.tf"),'''variable "proxmox_endpoint" { type = string }\nvariable "proxmox_node" { type = string }\nvariable "storage" { type = string }\nvariable "bridge" { type = string }\nvariable "template_vm_id" { type = number }\nvariable "ssh_user" { type = string }\nvariable "proxmox_api_token" {\n  type      = string\n  sensitive = true\n}\nvariable "machines" { type = list(object({ name=string, ipv4_cidr=string, gateway=string, dns=string, vcpu=number, memory_mb=number, system_disk_gb=number, data_disk_gb=number })) }\n\nprovider "proxmox" {\n  endpoint = var.proxmox_endpoint\n  api_token = var.proxmox_api_token\n  insecure = false\n}\n''')
    write(Path("terraform/main.tf"),'''resource "proxmox_virtual_environment_vm" "node" {
  for_each  = { for machine in var.machines : machine.name => machine }
  name      = each.value.name
  node_name = var.proxmox_node

  clone {
    vm_id = var.template_vm_id
    full  = true
  }
  agent {
    enabled = true
  }
  cpu {
    cores = each.value.vcpu
    type  = "host"
  }
  memory {
    dedicated = each.value.memory_mb
  }
  disk {
    datastore_id = var.storage
    interface    = "scsi0"
    size         = each.value.system_disk_gb
    discard      = "on"
    iothread     = true
  }
  dynamic "disk" {
    for_each = each.value.data_disk_gb > 0 ? [1] : []
    content {
      datastore_id = var.storage
      interface    = "scsi1"
      size         = each.value.data_disk_gb
      discard      = "on"
      iothread     = true
    }
  }
  network_device {
    bridge = var.bridge
    model  = "virtio"
  }
  initialization {
    datastore_id = var.storage
    ip_config {
      ipv4 {
        address = each.value.ipv4_cidr
        gateway = each.value.gateway
      }
    }
    dns {
      servers = split(",", each.value.dns)
    }
    user_account {
      username = var.ssh_user
      keys     = [file("${path.module}/../config/ssh_public_key.pub")]
    }
  }
}

output "vm_names" {
  value = [for vm in proxmox_virtual_environment_vm.node : vm.name]
}
''')
    write(Path("terraform/README.md"),'''# Terraform Proxmox\n\nLe provider crée des clones complets d'un template cloud-init existant. Le template doit être préparé avec cloud-init et QEMU Guest Agent. Les paramètres réseau sont appliqués par le provider.\n\nLe token est fourni via `TF_VAR_proxmox_api_token`, jamais dans le fichier tfvars.\n''')
    inv={"all":{"children":{"k3s_nodes":{"hosts":{m.name:{"ansible_host":m.ipv4_cidr.split('/')[0],"ansible_user":c.ssh_user} for m in c.machines}}}}}
    write(Path("ansible/inventory/hosts.yml"),yaml.safe_dump(inv,sort_keys=False,allow_unicode=True))
    vars_={"http_proxy":c.http_proxy,"https_proxy":c.https_proxy,"no_proxy":c.no_proxy,"proxy_environment":[{"key":"HTTP_PROXY","value":c.http_proxy},{"key":"HTTPS_PROXY","value":c.https_proxy},{"key":"NO_PROXY","value":c.no_proxy},{"key":"http_proxy","value":c.http_proxy},{"key":"https_proxy","value":c.https_proxy},{"key":"no_proxy","value":c.no_proxy}],"ca_certificate_source":c.ca_certificate,"data_disk_device":"/dev/sdb","data_disk_mount":"/var/lib/longhorn","configure_longhorn_disk":any(m.data_disk_gb>0 for m in c.machines)}
    write(Path("ansible/group_vars.yml"),yaml.safe_dump(vars_,sort_keys=False,allow_unicode=True))
    write(Path("ansible/ansible.cfg"),'''[defaults]\ninventory = inventory/hosts.yml\nhost_key_checking = True\nretry_files_enabled = False\nstdout_callback = default\n\n[privilege_escalation]\nbecome = True\n''')
    write(Path("ansible/playbooks/prepare-os.yml"),'''- name: Prepare Linux hosts for K3s\n  hosts: k3s_nodes\n  become: true\n  vars_files: [../group_vars.yml]\n  tasks:\n    - name: Set hostname\n      ansible.builtin.hostname:\n        name: "{{ inventory_hostname }}"\n    - name: Configure proxy environment\n      ansible.builtin.copy:\n        dest: /etc/profile.d/proxy.sh\n        owner: root\n        group: root\n        mode: '0644'\n        content: |\n          export HTTP_PROXY={{ http_proxy | quote }}\n          export HTTPS_PROXY={{ https_proxy | quote }}\n          export NO_PROXY={{ no_proxy | quote }}\n          export http_proxy={{ http_proxy | quote }}\n          export https_proxy={{ https_proxy | quote }}\n          export no_proxy={{ no_proxy | quote }}\n      when: http_proxy | length > 0 or https_proxy | length > 0\n    - name: Preserve existing environment and set proxy variables\n      ansible.builtin.lineinfile:\n        path: /etc/environment\n        regexp: "^{{ item.key }}="\n        line: "{{ item.key }}={{ item.value | to_json }}"\n        create: true\n      loop: "{{ proxy_environment }}"\n      when: item.value | length > 0\n    - name: Configure APT proxy\n      ansible.builtin.copy:\n        dest: /etc/apt/apt.conf.d/90proxy\n        owner: root\n        group: root\n        mode: '0644'\n        content: |\n          Acquire::http::Proxy "{{ http_proxy }}";\n          Acquire::https::Proxy "{{ https_proxy }}";\n      when: ansible_os_family == 'Debian' and (http_proxy | length > 0 or https_proxy | length > 0)\n    - name: Ensure required packages are present (Debian family)\n      ansible.builtin.apt:\n        name: [curl, ca-certificates, jq, parted, lvm2, xfsprogs, e2fsprogs, open-iscsi, nfs-common] \n        state: present\n        update_cache: true\n      when: ansible_os_family == 'Debian'\n    - name: Ensure required packages are present (RedHat family)\n      ansible.builtin.dnf:\n        name: [curl, ca-certificates, jq, parted, lvm2, xfsprogs, e2fsprogs, iscsi-initiator-utils, nfs-utils]\n        state: present\n      when: ansible_os_family == 'RedHat'\n    - name: Configure DNF proxy\n      ansible.builtin.ini_file:\n        path: /etc/dnf/dnf.conf\n        section: main\n        option: proxy\n        value: "{{ https_proxy if https_proxy | length > 0 else http_proxy }}"\n        no_extra_spaces: true\n      when: ansible_os_family == 'RedHat' and (http_proxy | length > 0 or https_proxy | length > 0)\n    - name: Install enterprise CA on Debian family\n      ansible.builtin.copy:\n        src: "{{ playbook_dir }}/../../config/enterprise-ca.pem"\n        dest: /usr/local/share/ca-certificates/enterprise-ca.crt\n        owner: root\n        group: root\n        mode: '0644'\n      when: ansible_os_family == 'Debian' and ca_certificate_source | length > 0\n      notify: update debian ca trust\n    - name: Install enterprise CA on RedHat family\n      ansible.builtin.copy:\n        src: "{{ playbook_dir }}/../../config/enterprise-ca.pem"\n        dest: /etc/pki/ca-trust/source/anchors/enterprise-ca.pem\n        owner: root\n        group: root\n        mode: '0644'\n      when: ansible_os_family == 'RedHat' and ca_certificate_source | length > 0\n      notify: update redhat ca trust\n    - name: Detect root filesystem source\n      ansible.builtin.command: findmnt -n -o SOURCE /\n      register: root_source\n      changed_when: false\n    - name: Extend root logical volume to all free extents in its VG\n      ansible.builtin.command: lvextend -r -l +100%FREE "{{ root_source.stdout }}"\n      when: root_source.stdout is search('^/dev/mapper/') or root_source.stdout is search('^/dev/[^/]+/[^/]+$')\n      register: root_lv_extend\n      changed_when: root_lv_extend.rc == 0\n    - name: Display data disk candidate (never format automatically in MVP)\n      ansible.builtin.debug:\n        msg: "Disque de données attendu : {{ data_disk_device }}. Vérifier son identité avant toute préparation Longhorn."\n  handlers:\n    - name: update debian ca trust\n      ansible.builtin.command: update-ca-certificates\n    - name: update redhat ca trust\n      ansible.builtin.command: update-ca-trust\n''')
    write(Path("ansible/README.md"),'''# Ansible\n\nL'inventaire est généré depuis le nombre de machines choisi dans l'UI. `prepare-os.yml` prépare les paquets et le proxy. Le formatage des disques est volontairement séparé et non automatique : le chemin `/dev/sdb` est un candidat, pas une preuve d'identité du disque. Avant de préparer Longhorn, il faut identifier le disque par `/dev/disk/by-id/` et confirmer son numéro de série.\n''')
    archive_name=kit_archive_path.name
    handoff={"selected_kit":c.kit,"source_archive":archive_name,"imported_archive":f"imported-kit/{archive_name}","machines":[m.name for m in c.machines],"next_step":"Review imported kit config.env and map machine IPs, proxy, VIPs, storage paths before invoking kit deployment scripts.","automatic_kit_execution":False}
    write(Path("config/kit-handoff.json"),json.dumps(handoff,indent=2))
    if c.ssh_public_key.strip(): write(Path("config/ssh_public_key.pub"),c.ssh_public_key.strip()+"\n")
    if c.ca_certificate and Path(c.ca_certificate).is_file(): shutil.copy2(c.ca_certificate,out/"config"/"enterprise-ca.pem")
    dst=out/"imported-kit"; dst.mkdir(exist_ok=True)
    shutil.copy2(kit_archive_path,dst/archive_name)
    files.append(dst/archive_name)
    write(Path("DEPLOYMENT-NOTES.md"),f'''# Deployment handoff\n\nKit cible : {c.kit}\nNombre de VM : {len(c.machines)}\nOS demandé : {c.os_family} {c.os_version}\nMéthode : {c.install_method}\n\nLes fichiers générés ne déclenchent pas encore les scripts du kit applicatif. Vérifier le mapping réseau, les VIP, les tailles et les variables propres au kit avant son déploiement.\n''')
    return files
