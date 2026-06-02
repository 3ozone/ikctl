"""Tests para la Entidad Kit."""
from datetime import datetime, timezone

from app.v1.kits.domain.entities.kit import Kit
from app.v1.kits.domain.value_objects.sync_status import SyncStatus
from app.v1.kits.domain.value_objects.kit_manifest import KitManifest


def make_kit(**overrides) -> Kit:
    """Factory de un Kit mínimo válido para tests."""
    defaults = {
        "id": "kit-1",
        "user_id": "user-1",
        "repository_id": "repo-1",
        "path_in_repo": "kits/haproxy",
        "name": "Install HAProxy",
        "description": "",
        "version": "1.0.0",
        "tags": [],
        "values": {},
        "debug_level": "errors",
        "upload_files": (),
        "pipeline_files": (),
        "backup_files": (),
        "sync_status": SyncStatus("never_synced"),
        "last_synced_at": None,
        "last_commit_sha": None,
        "sync_error_message": None,
        "is_deleted": False,
        "created_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
        "updated_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
    }
    defaults.update(overrides)
    return Kit(**defaults)


MANIFEST_DATA = {
    "name": "Install HAProxy",
    "description": "Installs HAProxy",
    "version": "2.0.0",
    "tags": ["networking"],
    "values": {"port": 80},
    "debug_level": "all",
    "files": {
        "uploads": ["haproxy.cfg.j2", "install.sh"],
        "pipeline": ["install.sh"],
    },
    "backup": ["/etc/haproxy/haproxy.cfg"],
}


class TestKitCreation:
    """Tests de construcción y campos de la entidad Kit."""

    def test_kit_creates_with_valid_fields(self):
        """Una entidad Kit se crea correctamente con campos válidos."""
        kit = make_kit()
        assert kit.id == "kit-1"
        assert kit.user_id == "user-1"
        assert kit.repository_id == "repo-1"
        assert kit.path_in_repo == "kits/haproxy"
        assert kit.sync_status == SyncStatus("never_synced")
        assert kit.is_deleted is False

    def test_kit_equality_by_id(self):
        """Dos Kit con el mismo id son iguales aunque difieran en otros campos."""
        kit_a = make_kit(id="kit-x", name="HAProxy")
        kit_b = make_kit(id="kit-x", name="Nginx")
        assert kit_a == kit_b

    def test_kit_inequality_different_ids(self):
        """Dos Kit con distinto id no son iguales."""
        kit_a = make_kit(id="kit-1")
        kit_b = make_kit(id="kit-2")
        assert kit_a != kit_b


class TestKitCommands:
    """Tests de los comandos de negocio de la entidad Kit."""

    def test_mark_synced_updates_fields_from_manifest(self):
        """mark_synced() actualiza los campos del manifest y establece sync_status."""
        kit = make_kit()
        manifest = KitManifest.from_dict(MANIFEST_DATA)
        now = datetime(2026, 4, 12, tzinfo=timezone.utc)
        kit.mark_synced(manifest=manifest, commit_sha="abc123", synced_at=now)
        assert kit.sync_status == SyncStatus("synced")
        assert kit.last_commit_sha == "abc123"
        assert kit.last_synced_at == now
        assert kit.name == "Install HAProxy"
        assert kit.version == "2.0.0"
        assert kit.tags == ["networking"]
        assert kit.sync_error_message is None

    def test_mark_sync_error_sets_status_and_message(self):
        """mark_sync_error() establece sync_status a sync_error y guarda el mensaje."""
        kit = make_kit()
        kit.mark_sync_error(message="Git clone failed")
        assert kit.sync_status == SyncStatus("sync_error")
        assert kit.sync_error_message == "Git clone failed"

    def test_soft_delete_sets_is_deleted(self):
        """soft_delete() establece is_deleted = True."""
        kit = make_kit()
        kit.soft_delete()
        assert kit.is_deleted is True


class TestKitQueries:
    """Tests de las queries de estado de la entidad Kit."""

    def test_is_usable_returns_true_when_synced_and_not_deleted(self):
        """is_usable() devuelve True cuando está sincronizado y no eliminado."""
        kit = make_kit(sync_status=SyncStatus("synced"), is_deleted=False)
        assert kit.is_usable() is True

    def test_is_usable_returns_false_when_not_synced(self):
        """is_usable() devuelve False cuando sync_status no es synced."""
        kit = make_kit(sync_status=SyncStatus("never_synced"))
        assert kit.is_usable() is False

    def test_is_usable_returns_false_when_deleted(self):
        """is_usable() devuelve False cuando is_deleted es True."""
        kit = make_kit(sync_status=SyncStatus("synced"), is_deleted=True)
        assert kit.is_usable() is False


class TestKitFileFields:
    """Tests de los campos de archivos del manifest persistidos en la entidad Kit."""

    def test_kit_has_upload_files_field_defaulting_to_empty_tuple(self):
        """Kit tiene el campo upload_files que por defecto es una tupla vacía."""
        kit = make_kit()
        assert kit.upload_files == ()

    def test_kit_has_pipeline_files_field_defaulting_to_empty_tuple(self):
        """Kit tiene el campo pipeline_files que por defecto es una tupla vacía."""
        kit = make_kit()
        assert kit.pipeline_files == ()

    def test_kit_has_backup_files_field_defaulting_to_empty_tuple(self):
        """Kit tiene el campo backup_files que por defecto es una tupla vacía."""
        kit = make_kit()
        assert kit.backup_files == ()

    def test_kit_stores_upload_files_as_tuple(self):
        """Kit almacena upload_files como tupla de strings."""
        kit = make_kit(upload_files=("haproxy.cfg.j2", "install.sh"))
        assert kit.upload_files == ("haproxy.cfg.j2", "install.sh")

    def test_kit_stores_pipeline_files_as_tuple(self):
        """Kit almacena pipeline_files como tupla de strings."""
        kit = make_kit(
            upload_files=("install.sh",),
            pipeline_files=("install.sh",),
        )
        assert kit.pipeline_files == ("install.sh",)

    def test_kit_stores_backup_files_as_tuple(self):
        """Kit almacena backup_files como tupla de strings."""
        kit = make_kit(backup_files=("/etc/haproxy/haproxy.cfg",))
        assert kit.backup_files == ("/etc/haproxy/haproxy.cfg",)

    def test_mark_synced_updates_upload_files_from_manifest(self):
        """mark_synced() actualiza upload_files desde el manifest."""
        kit = make_kit()
        manifest = KitManifest.from_dict(MANIFEST_DATA)
        now = datetime(2026, 4, 12, tzinfo=timezone.utc)
        kit.mark_synced(manifest=manifest, commit_sha="abc123", synced_at=now)
        assert kit.upload_files == ("haproxy.cfg.j2", "install.sh")

    def test_mark_synced_updates_pipeline_files_from_manifest(self):
        """mark_synced() actualiza pipeline_files desde el manifest."""
        kit = make_kit()
        manifest = KitManifest.from_dict(MANIFEST_DATA)
        now = datetime(2026, 4, 12, tzinfo=timezone.utc)
        kit.mark_synced(manifest=manifest, commit_sha="abc123", synced_at=now)
        assert kit.pipeline_files == ("install.sh",)

    def test_mark_synced_updates_backup_files_from_manifest(self):
        """mark_synced() actualiza backup_files desde el manifest."""
        kit = make_kit()
        manifest = KitManifest.from_dict(MANIFEST_DATA)
        now = datetime(2026, 4, 12, tzinfo=timezone.utc)
        kit.mark_synced(manifest=manifest, commit_sha="abc123", synced_at=now)
        assert kit.backup_files == ("/etc/haproxy/haproxy.cfg",)
