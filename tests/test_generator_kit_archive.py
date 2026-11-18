import json
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile

from app.core.generator import generate_project
from app.core.models import DeploymentConfig, Machine


class GeneratorKitArchiveTests(unittest.TestCase):
    def test_selected_archive_is_copied_and_manifest_does_not_store_local_path(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "authentik-distribution-renamed.zip"
            with ZipFile(source, "w") as archive:
                archive.writestr("kit/scripts/03-deploy-authentik.sh", "#!/bin/sh\n")
                archive.writestr("kit/upgrade/15-upgrade-authentik.sh", "#!/bin/sh\n")

            output = root / "workspace"
            config = DeploymentConfig(
                kit="authentik",
                machines=[
                    Machine(
                        name="k3s-node-1",
                        ipv4_cidr="192.0.2.51/24",
                        gateway="192.0.2.1",
                        dns="192.0.2.10",
                    )
                ],
            )
            generate_project(config, output, str(source))

            copied = output / "imported-kit" / source.name
            self.assertTrue(copied.is_file())
            self.assertEqual(copied.read_bytes(), source.read_bytes())
            manifest = json.loads((output / "config" / "kit-handoff.json").read_text())
            self.assertEqual(manifest["selected_kit"], "authentik")
            self.assertEqual(manifest["source_archive"], source.name)
            self.assertNotIn(str(root), json.dumps(manifest))

    def test_generation_requires_a_selected_archive(self):
        with tempfile.TemporaryDirectory() as temp:
            config = DeploymentConfig(
                kit="keycloak",
                machines=[
                    Machine(
                        name="k3s-node-1",
                        ipv4_cidr="192.0.2.51/24",
                        gateway="192.0.2.1",
                        dns="192.0.2.10",
                    )
                ],
            )
            with self.assertRaisesRegex(ValueError, "archive ZIP"):
                generate_project(config, Path(temp) / "workspace")


if __name__ == "__main__":
    unittest.main()
