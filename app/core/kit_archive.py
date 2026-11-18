"""Validation des archives de kits K3s importées par l'application."""

from pathlib import Path, PurePosixPath
from zipfile import BadZipFile, ZipFile
import zlib


KIT_SIGNATURES: dict[str, tuple[str, str]] = {
    "authentik": (
        "03-deploy-authentik.sh",
        "15-upgrade-authentik.sh",
    ),
    "keycloak": (
        "08-deploy-keycloak.sh",
        "16-upgrade-keycloak.sh",
    ),
}


class KitArchiveError(ValueError):
    """Levée lorsqu'une archive ZIP n'est pas un kit valide du type demandé."""


def validate_kit_archive(archive_path: str | Path, expected_kit: str) -> Path:
    """Valide qu'une archive ZIP est bien du type Authentik ou Keycloak demandé.

    La détection s'appuie sur les scripts de déploiement et de mise à niveau du
    kit, et non sur le nom du fichier. Le ZIP peut donc être renommé librement.
    """
    kit = expected_kit.strip().lower()
    if kit not in KIT_SIGNATURES:
        raise KitArchiveError(f"Type de kit non pris en charge : {expected_kit!r}.")

    path = Path(archive_path).expanduser()
    if not path.is_file():
        raise KitArchiveError("Le fichier ZIP sélectionné est introuvable.")

    try:
        with ZipFile(path, "r") as archive:
            files = [
                PurePosixPath(info.filename.replace("\\", "/")).name.lower()
                for info in archive.infolist()
                if not info.is_dir()
            ]
            if not files:
                raise KitArchiveError("L'archive ZIP est vide.")

            corrupt_member = archive.testzip()
            if corrupt_member is not None:
                raise KitArchiveError(
                    f"L'archive ZIP est endommagée (fichier : {corrupt_member})."
                )
    except KitArchiveError:
        raise
    except (BadZipFile, OSError, RuntimeError, EOFError, NotImplementedError, zlib.error) as exc:
        raise KitArchiveError(
            "Le fichier sélectionné n'est pas une archive ZIP valide ou lisible."
        ) from exc

    required_markers = KIT_SIGNATURES[kit]
    missing = [marker for marker in required_markers if marker not in files]
    if missing:
        other_kit = "keycloak" if kit == "authentik" else "authentik"
        other_markers = KIT_SIGNATURES[other_kit]
        if all(marker in files for marker in other_markers):
            raise KitArchiveError(
                f"Cette archive contient un kit {other_kit.capitalize()}, "
                f"alors que {kit.capitalize()} est sélectionné."
            )
        raise KitArchiveError(
            f"Cette archive ne correspond pas à un kit {kit.capitalize()} reconnu. "
            "Vérifie que tu as sélectionné l'archive complète du kit."
        )

    return path.resolve()
