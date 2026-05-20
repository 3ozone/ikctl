"""Tests para el Value Object KitManifest."""
import pytest

from app.v1.kits.domain.value_objects.kit_manifest import KitManifest
from app.v1.kits.domain.exceptions.kit import InvalidManifestError


MINIMAL_MANIFEST = {
    "name": "Install HAProxy",
}

FULL_MANIFEST = {
    "name": "Install HAProxy",
    "description": "Installs and configures HAProxy load balancer",
    "version": "1.0.0",
    "tags": ["networking", "loadbalancer"],
    "values": {"frontend_port": 80, "backend_servers": []},
    "debug_level": "errors",
    "files": {
        "uploads": ["haproxy.cfg.j2", "install-haproxy.sh"],
        "pipeline": ["install-haproxy.sh"],
    },
    "backup": ["/etc/haproxy/haproxy.cfg"],
}


class TestKitManifest:
    """Tests para el Value Object KitManifest."""

    def test_kit_manifest_valid_minimal(self):
        """Un manifiesto con solo el campo name es válido."""
        manifest = KitManifest.from_dict(MINIMAL_MANIFEST)
        assert manifest.name == "Install HAProxy"

    def test_kit_manifest_valid_full(self):
        """Un manifiesto completo con todos los campos es válido."""
        manifest = KitManifest.from_dict(FULL_MANIFEST)
        assert manifest.name == "Install HAProxy"
        assert manifest.description == "Installs and configures HAProxy load balancer"
        assert manifest.version == "1.0.0"
        assert manifest.upload_files == (
            "haproxy.cfg.j2", "install-haproxy.sh")
        assert manifest.pipeline_files == ("install-haproxy.sh",)
        assert manifest.backup_files == ("/etc/haproxy/haproxy.cfg",)

    def test_kit_manifest_pipeline_file_not_in_uploads_raises_error(self):
        """Un archivo en pipeline que no está en uploads lanza InvalidManifestError (RN-21)."""
        data = {
            "name": "My Kit",
            "files": {
                "uploads": ["install.sh"],
                "pipeline": ["install.sh", "missing.sh"],
            },
        }
        with pytest.raises(InvalidManifestError):
            KitManifest.from_dict(data)

    def test_kit_manifest_missing_name_raises_error(self):
        """Un manifiesto sin campo name lanza InvalidManifestError."""
        with pytest.raises(InvalidManifestError):
            KitManifest.from_dict({"description": "No name here"})

    def test_kit_manifest_tags_defaults_to_empty_tuple(self):
        """Si no se incluyen tags, el valor por defecto es una tupla vacía."""
        manifest = KitManifest.from_dict(MINIMAL_MANIFEST)
        assert manifest.tags == ()

    def test_kit_manifest_values_defaults_to_empty_dict(self):
        """Si no se incluyen values, el valor por defecto es un dict vacío."""
        manifest = KitManifest.from_dict(MINIMAL_MANIFEST)
        assert manifest.values == {}

    def test_kit_manifest_debug_level_defaults_to_none(self):
        """Si no se incluye debug_level, el valor por defecto es 'none'."""
        manifest = KitManifest.from_dict(MINIMAL_MANIFEST)
        assert manifest.debug_level == "none"

    def test_kit_manifest_backup_files_defaults_to_empty_tuple(self):
        """Si no se incluye backup, el valor por defecto es una tupla vacía."""
        manifest = KitManifest.from_dict(MINIMAL_MANIFEST)
        assert manifest.backup_files == ()
