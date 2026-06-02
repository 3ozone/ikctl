"""Tests de integración para SQLAlchemyRepositoryRepository (T-18)."""
from datetime import datetime

from app.v1.kits.domain.entities.repository import Repository
from app.v1.kits.domain.value_objects.sync_status import SyncStatus


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _make_repository(
    repo_id: str,
    user_id: str = "user-1",
    url: str = "https://github.com/org/kits.git",
    ref: str = "main",
    credential_id: str | None = None,
    is_deleted: bool = False,
) -> Repository:
    now = datetime(2024, 1, 1, 12, 0, 0)
    return Repository(
        id=repo_id,
        user_id=user_id,
        url=url,
        ref=ref,
        credential_id=credential_id,
        sync_status=SyncStatus("never_synced"),
        last_synced_at=None,
        last_commit_sha=None,
        sync_error_message=None,
        is_deleted=is_deleted,
        created_at=now,
        updated_at=now,
    )


# ---------------------------------------------------------------------------
# T-18 — Test 1: save y find_by_id happy path
# ---------------------------------------------------------------------------


async def test_save_and_find_by_id(repository_repository):
    """Guarda un repositorio y lo recupera por id + user_id verificando todos los campos."""
    repo = _make_repository("repo-1", credential_id="cred-abc")
    await repository_repository.save(repo)

    found = await repository_repository.find_by_id("repo-1", "user-1")

    assert found is not None
    assert found.id == "repo-1"
    assert found.user_id == "user-1"
    assert found.url == "https://github.com/org/kits.git"
    assert found.ref == "main"
    assert found.credential_id == "cred-abc"
    assert found.sync_status == SyncStatus("never_synced")
    assert found.last_synced_at is None
    assert found.last_commit_sha is None
    assert found.sync_error_message is None
    assert found.is_deleted is False
    assert found.created_at == datetime(2024, 1, 1, 12, 0, 0)

    # usuario incorrecto → None
    assert await repository_repository.find_by_id("repo-1", "other-user") is None


# ---------------------------------------------------------------------------
# T-18 — Test 2: find_by_id no devuelve repos borrados ni inexistentes
# ---------------------------------------------------------------------------


async def test_find_by_id_returns_none_for_deleted_and_missing(repository_repository):
    """find_by_id devuelve None si el repositorio tiene is_deleted=True o no existe."""
    deleted_repo = _make_repository("repo-deleted", is_deleted=True)
    await repository_repository.save(deleted_repo)

    # repo borrado → None aunque el id y user_id sean correctos
    result = await repository_repository.find_by_id("repo-deleted", "user-1")
    assert result is None

    # id inexistente → None
    result = await repository_repository.find_by_id("does-not-exist", "user-1")
    assert result is None


# ---------------------------------------------------------------------------
# T-18 — Test 3: find_all_by_user filtra borrados y pagina correctamente
# ---------------------------------------------------------------------------


async def test_find_all_by_user_pagination_and_deleted_filter(repository_repository):
    """find_all_by_user excluye is_deleted=True y respeta page/per_page."""
    now = datetime(2024, 1, 1, 12, 0, 0)

    # 3 repos del user-1: 2 activos + 1 borrado; 1 repo de user-2
    repos = [
        _make_repository("repo-a", user_id="user-1"),
        _make_repository("repo-b", user_id="user-1"),
        _make_repository("repo-c", user_id="user-1", is_deleted=True),
        _make_repository("repo-d", user_id="user-2"),
    ]
    for r in repos:
        await repository_repository.save(r)

    # user-1: solo 2 activos
    all_user1 = await repository_repository.find_all_by_user("user-1", page=1, per_page=10)
    assert len(all_user1) == 2
    ids = {r.id for r in all_user1}
    assert ids == {"repo-a", "repo-b"}

    # paginación: page=1 per_page=1 → 1 resultado
    page1 = await repository_repository.find_all_by_user("user-1", page=1, per_page=1)
    assert len(page1) == 1

    # paginación: page=2 per_page=1 → 1 resultado
    page2 = await repository_repository.find_all_by_user("user-1", page=2, per_page=1)
    assert len(page2) == 1
    assert page1[0].id != page2[0].id

    # paginación: page=3 per_page=1 → vacío
    page3 = await repository_repository.find_all_by_user("user-1", page=3, per_page=1)
    assert len(page3) == 0

    # user-2: solo 1
    all_user2 = await repository_repository.find_all_by_user("user-2", page=1, per_page=10)
    assert len(all_user2) == 1
    assert all_user2[0].id == "repo-d"


# ---------------------------------------------------------------------------
# T-18 — Test 4: update, delete físico y has_kits_with_references
# ---------------------------------------------------------------------------


async def test_update_delete_and_has_kits_with_references(repository_repository, db_session):
    """Actualiza campos, borra físicamente y verifica has_kits_with_references."""
    from app.v1.kits.infrastructure.persistence.models import KitModel

    repo = _make_repository("repo-1")
    await repository_repository.save(repo)

    # --- update: cambiar url y ref resetea sync_status a never_synced ---
    repo.update("https://github.com/new-org/repo.git", "develop", "cred-xyz")
    repo.updated_at = datetime(2024, 2, 1, 12, 0, 0)
    await repository_repository.update(repo)

    updated = await repository_repository.find_by_id("repo-1", "user-1")
    assert updated is not None
    assert updated.url == "https://github.com/new-org/repo.git"
    assert updated.ref == "develop"
    assert updated.credential_id == "cred-xyz"
    assert updated.sync_status == SyncStatus("never_synced")
    assert updated.updated_at == datetime(2024, 2, 1, 12, 0, 0)

    # --- has_kits_with_references: False cuando no hay kits ---
    assert await repository_repository.has_kits_with_references("repo-1") is False

    # --- insertar un kit activo directamente en la sesión ---
    # _JsonText serializa automáticamente: pasar list/dict, no json.dumps
    kit_model = KitModel(
        id="kit-1",
        user_id="user-1",
        repository_id="repo-1",
        path_in_repo="tools/my-kit",
        name="my-kit",
        description="",
        version="1.0.0",
        tags=[],
        values={},
        debug_level="info",
        sync_status="synced",
        last_synced_at=None,
        last_commit_sha=None,
        sync_error_message=None,
        is_deleted=False,
        created_at=datetime(2024, 1, 1, 12, 0, 0),
        updated_at=datetime(2024, 1, 1, 12, 0, 0),
    )
    db_session.add(kit_model)
    await db_session.flush()

    # --- has_kits_with_references: True cuando hay kits activos ---
    assert await repository_repository.has_kits_with_references("repo-1") is True

    # --- delete físico: el registro desaparece de la BD ---
    await repository_repository.delete("repo-1")
    assert await repository_repository.find_by_id("repo-1", "user-1") is None
