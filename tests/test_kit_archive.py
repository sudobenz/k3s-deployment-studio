import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile

from app.core.kit_archive import KitArchiveError, validate_kit_archive


class KitArchiveTests(unittest.TestCase):
    def _make_archive(self, root: Path, name: str, entries: tuple[str, str]) -> Path:
        archive_path = root / name
        with ZipFile(archive_path, "w") as archive:
            for entry in entries:
                archive.writestr(f"sample-kit/{entry}", "# example script\n")
        return archive_path

    def test_accepts_authentik_archive_even_when_renamed(self):
        with tempfile.TemporaryDirectory() as temp:
            archive = self._make_archive(
                Path(temp),
                "mon-kit-renomme.zip",
                ("scripts/03-deploy-authentik.sh", "upgrade/15-upgrade-authentik.sh"),
            )
            self.assertEqual(validate_kit_archive(archive, "authentik"), archive.resolve())

    def test_accepts_keycloak_archive_even_when_renamed(self):
        with tempfile.TemporaryDirectory() as temp:
            archive = self._make_archive(
                Path(temp),
                "package.zip",
                ("scripts/08-deploy-keycloak.sh", "upgrade/16-upgrade-keycloak.sh"),
            )
            self.assertEqual(validate_kit_archive(archive, "keycloak"), archive.resolve())

    def test_rejects_wrong_kit_type(self):
        with tempfile.TemporaryDirectory() as temp:
            archive = self._make_archive(
                Path(temp),
                "keycloak.zip",
                ("scripts/08-deploy-keycloak.sh", "upgrade/16-upgrade-keycloak.sh"),
            )
            with self.assertRaisesRegex(KitArchiveError, "kit Keycloak"):
                validate_kit_archive(archive, "authentik")

    def test_rejects_unrecognized_zip(self):
        with tempfile.TemporaryDirectory() as temp:
            archive = self._make_archive(
                Path(temp), "other.zip", ("README.md", "scripts/install.sh")
            )
            with self.assertRaisesRegex(KitArchiveError, "ne correspond pas"):
                validate_kit_archive(archive, "authentik")

    def test_rejects_invalid_zip(self):
        with tempfile.TemporaryDirectory() as temp:
            archive = Path(temp) / "invalid.zip"
            archive.write_text("not a zip", encoding="utf-8")
            with self.assertRaises(KitArchiveError):
                validate_kit_archive(archive, "keycloak")


if __name__ == "__main__":
    unittest.main()
