from pathlib import Path
import json, os, subprocess, sys
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QMainWindow,QWidget,QVBoxLayout,QHBoxLayout,QFormLayout,QLineEdit,QComboBox,QSpinBox,QDoubleSpinBox,QTableWidget,QTableWidgetItem,QPushButton,QLabel,QFileDialog,QMessageBox,QPlainTextEdit,QTabWidget,QGroupBox,QCheckBox,QHeaderView,QInputDialog)
from app.core.models import DeploymentConfig, Machine, validate_config
from app.core.generator import generate_project
from app.core.kit_archive import KitArchiveError, validate_kit_archive

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__(); self.setWindowTitle("K3s Deployment Studio"); self.resize(1320,900); self.archive=""; self.kit_archives={"authentik":"","keycloak":""}; self.last_kit_directory=str(Path.home()); self.workspace=Path.cwd()/"workspace"
        root=QWidget(); self.setCentralWidget(root); layout=QVBoxLayout(root)
        header=QHBoxLayout(); title=QLabel("K3s Deployment Studio"); title.setStyleSheet("font-size:24px;font-weight:700")
        self.mode=QLabel("Application de bureau • Terraform + Ansible"); self.mode.setStyleSheet("color:#8b98a8")
        header.addWidget(title); header.addStretch(); header.addWidget(self.mode); layout.addLayout(header)
        self.tabs=QTabWidget(); layout.addWidget(self.tabs)
        self._build_general(); self._build_machines(); self._build_network(); self._build_execution()
        self.log=QPlainTextEdit(); self.log.setReadOnly(True); self.log.setMaximumBlockCount(3000); self.log.setPlaceholderText("Journal des opérations…"); layout.addWidget(self.log,1)
        self._style(); self.resize_rows(self.count.value()); self._update_kit_archive_ui()

    def _build_general(self):
        w=QWidget(); f=QFormLayout(w)
        self.project=QLineEdit("k3s-ha-deployment")
        self.kit=QComboBox(); self.kit.addItems(["authentik","keycloak"]); self.kit.currentTextChanged.connect(self.on_kit_changed)
        self.archive_label=QLabel("Aucune archive sélectionnée")
        self.archive_button=QPushButton("Choisir le ZIP Authentik…"); self.archive_button.clicked.connect(self.import_kit)
        row=QHBoxLayout(); row.addWidget(self.archive_button); row.addWidget(self.archive_label,1)
        self.endpoint=QLineEdit("https://pve.example.invalid:8006/"); self.node=QLineEdit("pve1"); self.storage=QLineEdit("local-lvm"); self.bridge=QLineEdit("vmbr0"); self.template=QSpinBox(); self.template.setRange(100,999999); self.template.setValue(9000)
        self.os=QComboBox(); self.os.addItems(["ubuntu","debian","rocky","almalinux","rhel","suse","custom"])
        self.osver=QLineEdit("24.04")
        self.method=QComboBox(); self.method.addItem("Template cloud-init (recommandé)","cloud-init-template"); self.method.addItem("ISO personnalisée + profil unattended","custom")
        self.iso=QLineEdit(); ib=QPushButton("Choisir ISO…"); ib.clicked.connect(self.pick_iso); ir=QHBoxLayout(); ir.addWidget(self.iso,1); ir.addWidget(ib)
        self.profile=QLineEdit(); self.profile.setPlaceholderText("ex. kickstart, autoinstall, preseed, autoyast ou chemin du profil")
        f.addRow("Nom du projet",self.project); f.addRow("Kit applicatif",self.kit); f.addRow("Archive du kit",row); f.addRow("API Proxmox HTTPS",self.endpoint); f.addRow("Nœud Proxmox cible",self.node); f.addRow("Stockage VM",self.storage); f.addRow("Bridge réseau",self.bridge); f.addRow("ID template cloud-init",self.template); f.addRow("Distribution",self.os); f.addRow("Version",self.osver); f.addRow("Méthode installation",self.method); f.addRow("ISO",ir); f.addRow("Profil unattended",self.profile)
        self.method.currentIndexChanged.connect(self._toggle_iso); self._toggle_iso()
        self.tabs.addTab(w,"1 · Projet & OS")

    def _toggle_iso(self):
        custom=self.method.currentData()=="custom"; self.iso.setEnabled(custom); self.profile.setEnabled(custom)

    def _build_machines(self):
        w=QWidget(); v=QVBoxLayout(w); bar=QHBoxLayout(); self.count=QSpinBox(); self.count.setRange(1,20); self.count.setValue(3); self.count.valueChanged.connect(self.resize_rows)
        add=QPushButton("+ Ajouter une machine"); add.clicked.connect(self.add_machine); rem=QPushButton("− Supprimer la dernière"); rem.clicked.connect(self.remove_machine)
        bar.addWidget(QLabel("Nombre de machines :")); bar.addWidget(self.count); bar.addStretch(); bar.addWidget(add); bar.addWidget(rem); v.addLayout(bar)
        info=QLabel("Le nombre de VM est libre (1 à 20). Chaque machine possède sa propre identité, IP, ressources et capacité disque."); info.setStyleSheet("color:#8b98a8") ; v.addWidget(info)
        self.table=QTableWidget(0,9); self.table.setHorizontalHeaderLabels(["Hostname","IPv4/CIDR","Passerelle","DNS","vCPU","RAM Mo","OS Go","Données Go",""]); self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch); self.table.verticalHeader().setVisible(False); v.addWidget(self.table)
        self.tabs.addTab(w,"2 · Machines")

    def _build_network(self):
        w=QWidget(); f=QFormLayout(w)
        self.http=QLineEdit(); self.https=QLineEdit(); self.noproxy=QLineEdit("localhost,127.0.0.1,::1"); self.ca=QLineEdit(); cb=QPushButton("Choisir CA…"); cb.clicked.connect(self.pick_ca); cr=QHBoxLayout(); cr.addWidget(self.ca,1); cr.addWidget(cb)
        self.sshuser=QLineEdit("deployer"); self.sshkey=QPlainTextEdit(); self.sshkey.setPlaceholderText("Coller la clé publique SSH (ssh-ed25519 …)"); self.sshkey.setMaximumHeight(90)
        f.addRow("HTTP_PROXY",self.http); f.addRow("HTTPS_PROXY",self.https); f.addRow("NO_PROXY",self.noproxy); f.addRow("CA entreprise",cr); f.addRow("Utilisateur SSH",self.sshuser); f.addRow("Clé publique SSH",self.sshkey)
        note=QLabel("Le proxy sera configuré sur l'OS et dans les services explicitement pris en charge. Les secrets de proxy ne doivent pas être saisis ici ; utiliser un compte proxy dédié et un mécanisme de secret externe."); note.setWordWrap(True); note.setStyleSheet("color:#c49a47"); f.addRow(note)
        self.tabs.addTab(w,"3 · Réseau & proxy")

    def _build_execution(self):
        w=QWidget(); v=QVBoxLayout(w)
        self.out=QLineEdit(str(self.workspace)); ob=QPushButton("Choisir dossier…"); ob.clicked.connect(self.pick_output); rr=QHBoxLayout(); rr.addWidget(self.out,1); rr.addWidget(ob)
        f=QFormLayout(); self.tokenid=QLineEdit(); self.tokenid.setPlaceholderText("user@realm!token-id"); self.tokensecret=QLineEdit(); self.tokensecret.setEchoMode(QLineEdit.EchoMode.Password); self.tokensecret.setPlaceholderText("Secret API token Proxmox")
        f.addRow("Token ID Proxmox",self.tokenid); f.addRow("Secret token",self.tokensecret); f.addRow("Workspace généré",rr); v.addLayout(f)
        buttons=QHBoxLayout(); self.generate_btn=QPushButton("Générer le projet"); self.generate_btn.clicked.connect(self.generate); self.validate=QPushButton("Terraform validate"); self.validate.clicked.connect(lambda:self.run_terraform("validate")); self.plan=QPushButton("Terraform plan"); self.plan.clicked.connect(lambda:self.run_terraform("plan")); self.apply=QPushButton("Terraform apply…"); self.apply.clicked.connect(self.apply_terraform); self.ansible=QPushButton("Ansible prepare OS"); self.ansible.clicked.connect(self.run_ansible)
        for b in [self.generate_btn,self.validate,self.plan,self.apply,self.ansible]: buttons.addWidget(b)
        v.addLayout(buttons)
        warning=QLabel("Terraform apply crée des VM réelles sur Proxmox. Vérifie le plan et les capacités avant de confirmer. Aucun destroy automatique n'est fourni."); warning.setWordWrap(True); warning.setStyleSheet("color:#d89b48;font-weight:600"); v.addWidget(warning); v.addStretch(); self.tabs.addTab(w,"4 · Génération & exécution")

    def _style(self):
        self.setStyleSheet("QMainWindow,QWidget{background:#151a22;color:#e6edf5;font-size:13px} QLineEdit,QComboBox,QSpinBox,QPlainTextEdit,QTableWidget{background:#202936;border:1px solid #354252;border-radius:5px;padding:6px;color:#f0f4f8} QPushButton{background:#315b89;border:0;border-radius:5px;padding:8px 12px;color:white;font-weight:600} QPushButton:hover{background:#4076ad} QTabWidget::pane{border:1px solid #354252;border-radius:6px} QTabBar::tab{background:#202936;padding:10px 16px;margin-right:3px} QTabBar::tab:selected{background:#315b89} QHeaderView::section{background:#263444;padding:7px;border:0} QGroupBox{border:1px solid #354252;border-radius:6px;margin-top:8px;padding:8px}")

    def add_machine(self):
        i=self.table.rowCount(); self.table.insertRow(i)
        defaults=[f"k3s-{i+1}",f"192.0.2.{51+i}/24","192.0.2.1","192.0.2.10,1.1.1.1","4","8192","100","200"]
        for col,val in enumerate(defaults): self.table.setItem(i,col,QTableWidgetItem(val))
        self.table.setItem(i,8,QTableWidgetItem("")); self.count.blockSignals(True); self.count.setValue(self.table.rowCount()); self.count.blockSignals(False)
    def remove_machine(self):
        if self.table.rowCount()>1: self.table.removeRow(self.table.rowCount()-1)
        self.count.blockSignals(True); self.count.setValue(self.table.rowCount()); self.count.blockSignals(False)
    def resize_rows(self,n):
        while self.table.rowCount()<n: self.add_machine()
        while self.table.rowCount()>n: self.table.removeRow(self.table.rowCount()-1)
        self.count.blockSignals(True); self.count.setValue(self.table.rowCount()); self.count.blockSignals(False)
    def pick_iso(self):
        p,_=QFileDialog.getOpenFileName(self,"Sélectionner une ISO","","Images ISO (*.iso)");
        if p: self.iso.setText(p); self.method.setCurrentIndex(1); self.os.setCurrentText("custom")
    def pick_ca(self):
        p,_=QFileDialog.getOpenFileName(self,"Certificat CA","","Certificats (*.pem *.crt *.cer)");
        if p:self.ca.setText(p)
    def pick_output(self):
        p=QFileDialog.getExistingDirectory(self,"Dossier de sortie",self.out.text());
        if p:self.out.setText(p)
    def _update_kit_archive_ui(self):
        kit=self.kit.currentText()
        display=kit.capitalize() if kit else "kit"
        self.archive_button.setText(f"Choisir le ZIP {display}…")
        if self.archive and Path(self.archive).is_file():
            self.archive_label.setText(f"{Path(self.archive).name}  ·  {display} sélectionné")
            self.archive_label.setToolTip(self.archive)
        else:
            self.archive=""
            self.archive_label.setText(f"Aucune archive {display} sélectionnée")
            self.archive_label.setToolTip("")

    def on_kit_changed(self, selected_kit):
        """Charge l'archive mémorisée pour ce type ou ouvre le sélecteur."""
        selected_kit=(selected_kit or self.kit.currentText()).lower()
        saved=self.kit_archives.get(selected_kit, "")
        if saved and Path(saved).is_file():
            try:
                self.archive=str(validate_kit_archive(saved, selected_kit))
            except KitArchiveError:
                self.archive=""
                self.kit_archives[selected_kit]=""
        else:
            self.archive=""
        self._update_kit_archive_ui()
        if not self.archive:
            self.import_kit()

    def import_kit(self):
        kit=self.kit.currentText().lower()
        display=kit.capitalize()
        p,_=QFileDialog.getOpenFileName(
            self,
            f"Sélectionner l'archive ZIP du kit {display}",
            self.last_kit_directory,
            "Archives de kits (*.zip);;Tous les fichiers (*)",
        )
        if not p:
            return
        try:
            selected=validate_kit_archive(p, kit)
        except KitArchiveError as exc:
            QMessageBox.warning(self,"Archive de kit invalide",str(exc))
            return
        self.archive=str(selected)
        self.kit_archives[kit]=self.archive
        self.last_kit_directory=str(selected.parent)
        self._update_kit_archive_ui()
        self.log.appendPlainText(f"Archive {display} sélectionnée : {selected}")
    def collect(self):
        machines=[]
        for r in range(self.table.rowCount()):
            vals=[self.table.item(r,c).text().strip() if self.table.item(r,c) else "" for c in range(8)]
            machines.append(Machine(vals[0],vals[1],vals[2],vals[3],int(vals[4]),int(vals[5]),int(vals[6]),int(vals[7])))
        method=self.method.currentData()
        return DeploymentConfig(project_name=self.project.text().strip(),kit=self.kit.currentText(),proxmox_endpoint=self.endpoint.text().strip(),proxmox_node=self.node.text().strip(),storage=self.storage.text().strip(),bridge=self.bridge.text().strip(),template_vm_id=self.template.value(),iso_path=self.iso.text().strip(),os_family=self.os.currentText(),os_version=self.osver.text().strip(),install_method=method,custom_profile=self.profile.text().strip(),http_proxy=self.http.text().strip(),https_proxy=self.https.text().strip(),no_proxy=self.noproxy.text().strip(),ca_certificate=self.ca.text().strip(),ssh_user=self.sshuser.text().strip(),ssh_public_key=self.sshkey.toPlainText().strip(),machines=machines)
    def generate(self):
        c=self.collect(); errors=validate_config(c)
        if not self.archive:
            errors.append(f"Sélectionne l'archive ZIP du kit {c.kit.capitalize()}.")
        else:
            try:
                self.archive=str(validate_kit_archive(self.archive, c.kit))
            except KitArchiveError as exc:
                errors.append(str(exc))
        if not c.ssh_public_key: errors.append("Clé publique SSH obligatoire pour le bootstrap cloud-init.")
        if errors: QMessageBox.warning(self,"Configuration invalide","\n• "+"\n• ".join(errors)); return
        out=Path(self.out.text()).expanduser().resolve()
        try:
            files=generate_project(c,out,self.archive); self.workspace=out; self.log.appendPlainText(f"Projet généré : {out}\n{len(files)} fichiers écrits.")
            QMessageBox.information(self,"Génération terminée",f"Projet généré dans :\n{out}\n\nVM configurées : {len(c.machines)}")
        except Exception as e: QMessageBox.critical(self,"Erreur génération",str(e))
    def _run(self,cmd,cwd,env=None):
        self.log.appendPlainText("\n$ "+" ".join(cmd)); self.log.repaint()
        try:
            p=subprocess.run(cmd,cwd=cwd,env=env or os.environ.copy(),text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
            self.log.appendPlainText(p.stdout); self.log.appendPlainText(f"Code retour : {p.returncode}"); return p.returncode==0
        except FileNotFoundError as e: self.log.appendPlainText(str(e)); QMessageBox.critical(self,"Binaire introuvable",str(e)); return False
    def _tf_env(self):
        env=os.environ.copy()
        if self.tokenid.text().strip() and self.tokensecret.text(): env["TF_VAR_proxmox_api_token"]=self.tokenid.text().strip()+"="+self.tokensecret.text()
        return env
    def run_terraform(self,action):
        d=Path(self.out.text())/"terraform"
        if not (d/"main.tf").exists(): QMessageBox.warning(self,"Projet absent","Génère d'abord le projet."); return
        env=self._tf_env()
        if action == "plan" and "TF_VAR_proxmox_api_token" not in env:
            QMessageBox.warning(self,"Identifiants manquants","Renseigne le Token ID et son secret avant de planifier."); return
        if not self._run(["terraform", "init"],d,env): return
        cmd=["terraform","validate"] if action=="validate" else ["terraform","plan","-out=tfplan"]
        self._run(cmd,d,env)
    def apply_terraform(self):
        d=Path(self.out.text())/"terraform"; env=self._tf_env()
        deployment_file=Path(self.out.text())/"deployment.json"
        if deployment_file.exists():
            try:
                if json.loads(deployment_file.read_text(encoding="utf-8")).get("install_method")=="custom":
                    QMessageBox.warning(self,"Workflow ISO custom non activé","Cette version enregistre l'ISO et son profil, mais ne sait pas encore créer automatiquement le média unattended et installer une ISO brute sur Proxmox. Terraform apply est bloqué pour éviter de cloner un template en prétendant installer cette ISO.")
                    return
            except Exception: pass
        if not (d/"main.tf").exists(): QMessageBox.warning(self,"Projet absent","Génère d'abord le projet."); return
        if not (d/"tfplan").exists(): QMessageBox.warning(self,"Plan absent","Exécute et vérifie d'abord Terraform plan."); return
        if "TF_VAR_proxmox_api_token" not in env:
            QMessageBox.warning(self,"Identifiants manquants","Renseigne le Token ID et son secret."); return
        ans=QMessageBox.question(self,"Confirmer Terraform apply","Cette opération applique le plan enregistré tfplan et crée les VM sur Proxmox. Confirmer ?",QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No)
        if ans!=QMessageBox.StandardButton.Yes:return
        self._run(["terraform","apply","-auto-approve","tfplan"],d,env)
    def run_ansible(self):
        d=Path(self.out.text())/"ansible"
        if not (d/"inventory/hosts.yml").exists(): QMessageBox.warning(self,"Projet absent","Génère d'abord le projet."); return
        QMessageBox.information(self,"Ansible","Vérifie que les VM sont installées, que SSH fonctionne et que les clés hôtes sont validées avant de lancer le playbook.")
        self._run(["ansible-playbook","-i","inventory/hosts.yml","playbooks/prepare-os.yml"],d)
