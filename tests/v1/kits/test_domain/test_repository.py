"""Tests para la Entidad Repository."""
from datetime import datetime, timezone

from app.v1.kits.domain.entities.repository import Repository
from app.v1.kits.domain.value_objects.sync_status import SyncStatus


def make_repository(**overrides) -> Repository:
    """Factory de un Repository mínimo válido para tests."""
    defaults = {
        "id": "repo-1",
        "user_id": "user-1",
        "url": "https://github.com/org/kits",
        "ref": "main",
        "credential_id": None,
        "sync_status": SyncStatus("never_synced"),
        "last_synced_at": None,
        "last_commit_sha": None,
        "sync_error_message": None,
        "is_deleted": False,
        "created_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
        "updated_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
    }
    defaults.update(overrides)
    return Repository(**defaults)


class TestRepositoryCreation:
    """Tests de construcción y campos de la entidad Repository."""

    def test_repository_creates_with_valid_fields(self):
        """Una entidad Repository se crea correctamente con campos válidos."""
        repo = make_repository()
        assert repo.id == "repo-1"
        assert repo.user_id == "user-1"
        assert repo.url == "https://github.com/org/kits"
        assert repo.ref == "main"
        assert repo.sync_status == SyncStatus("never_synced")
        assert repo.is_deleted is False

    def test_repository_equality_by_id(self):
        """Dos Repository con el mismo id son iguales aunque difieran en otros campos."""
        repo_a = make_repository(
            id="repo-x", url="https://github.com/org/kits-a")
        repo_b = make_repository(
            id="repo-x", url="https://github.com/org/kits-b")
        assert repo_a == repo_b

    def test_repository_inequality_different_ids(self):
        """Dos Repository con distinto id no son iguales."""
        repo_a = make_repository(id="repo-1")
        repo_b = make_repository(id="repo-2")
        assert repo_a != repo_b


class TestRepositoryCommands:
    """Tests de los comandos de negocio de la entidad Repository."""

    def test_update_changes_url_and_resets_sync_status(self):
        """update() con nueva url resetea sync_status a never_synced."""
        repo = make_repository(sync_status=SyncStatus("synced"))
        repo.update(url="https://github.com/org/other",
                    ref="main", credential_id=None)
        assert repo.url == "https://github.com/org/other"
        assert repo.sync_status == SyncStatus("never_synced")

    def test_update_changes_ref_and_resets_sync_status(self):
        """update() con nueva ref resetea sync_status a never_synced."""
        repo = make_repository(sync_status=SyncStatus("synced"))
        repo.update(url="https://github.com/org/kits",
                    ref="develop", credential_id=None)
        assert repo.ref == "develop"
        assert repo.sync_status == SyncStatus("never_synced")

    def test_update_same_url_and_ref_does_not_reset_sync_status(self):
        """update() sin cambiar url ni ref no resetea sync_status."""
        repo = make_repository(sync_status=SyncStatus("synced"))
        repo.update(
            url="https://github.com/org/kits",
            ref="main",
            credential_id="cred-1",
        )
        assert repo.sync_status == SyncStatus("synced")
        assert repo.credential_id == "cred-1"

    def test_mark_synced_sets_status_and_commit_sha(self):
        """mark_synced() establece sync_status a synced y guarda commit_sha."""
        repo = make_repository()
        now = datetime(2026, 4, 12, tzinfo=timezone.utc)
        repo.mark_synced(commit_sha="abc123", synced_at=now)
        assert repo.sync_status == SyncStatus("synced")
        assert repo.last_commit_sha == "abc123"
        assert repo.last_synced_at == now
        assert repo.sync_error_message is None

    def test_mark_sync_error_sets_status_and_message(self):
        """mark_sync_error() establece sync_status a sync_error y guarda el mensaje."""
        repo = make_repository()
        repo.mark_sync_error(message="Connection refused")
        assert repo.sync_status == SyncStatus("sync_error")
        assert repo.sync_error_message == "Connection refused"

    def test_delete_sets_is_deleted(self):
        """delete() establece is_deleted = True."""
        repo = make_repository()
        repo.delete()
        assert repo.is_deleted is True


class TestRepositoryQueries:
    """Tests de las queries de estado de la entidad Repository."""

    def test_is_synced_returns_true_when_synced(self):
        """is_synced() devuelve True cuando sync_status es synced."""
        repo = make_repository(sync_status=SyncStatus("synced"))
        assert repo.is_synced() is True

    def test_is_synced_returns_false_when_never_synced(self):
        """is_synced() devuelve False cuando sync_status es never_synced."""
        repo = make_repository(sync_status=SyncStatus("never_synced"))
        assert repo.is_synced() is False
