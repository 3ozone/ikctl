"""Tests de integración para SQLAlchemyKitRepository (T-19)."""
from datetime import datetime

from app.v1.kits.domain.entities.kit import Kit
from app.v1.kits.domain.entities.repository import Repository
from app.v1.kits.domain.value_objects.sync_status import SyncStatus


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_repository(repo_id: str, user_id: str = "user-1") -> Repository:
    now = datetime(2024, 1, 1, 12, 0, 0)
    return Repository(
        id=repo_id,
        user_id=user_id,
        url="https://github.com/org/kits.git",
        ref="main",
        credential_id=None,
        sync_status=SyncStatus("never_synced"),
        last_synced_at=None,
        last_commit_sha=None,
        sync_error_message=None,
        is_deleted=False,
        created_at=now,
        updated_at=now,
    )


def _make_kit(
    kit_id: str,
    repository_id: str,
    user_id: str = "user-1",
    path_in_repo: str = "tools/my-kit",
    tags: list[str] | None = None,
    is_deleted: bool = False,
) -> Kit:
    now = datetime(2024, 1, 1, 12, 0, 0)
    return Kit(
        id=kit_id,
        user_id=user_id,
        repository_id=repository_id,
        path_in_repo=path_in_repo,
        name=f"kit-{kit_id}",
        description="A test kit",
        version="1.0.0",
        tags=tags or [],
        values={"port": 8080, "debug": False},
        debug_level="info",
        upload_files=("config.j2", "install.sh"),
        pipeline_files=("install.sh",),
        backup_files=("/etc/app/config",),
        sync_status=SyncStatus("synced"),
        last_synced_at=now,
        last_commit_sha="abc123",
        sync_error_message=None,
        is_deleted=is_deleted,
        created_at=now,
        updated_at=now,
    )


# ---------------------------------------------------------------------------
# T-19 — Test 1: save y find_by_id con roundtrip de tags/values JSON
# ---------------------------------------------------------------------------


async def test_save_and_find_by_id(kit_repository, repository_repository):
    """save persiste el kit y find_by_id lo recupera con todos sus campos correctos.

    Verifica el roundtrip JSON de tags (list[str]) y values (dict).
    """
    await repository_repository.save(_make_repository("repo-1"))

    kit = _make_kit("kit-1", "repo-1", tags=["python", "web"])
    await kit_repository.save(kit)

    found = await kit_repository.find_by_id("kit-1", "user-1")

    assert found is not None
    assert found.id == "kit-1"
    assert found.user_id == "user-1"
    assert found.repository_id == "repo-1"
    assert found.path_in_repo == "tools/my-kit"
    assert found.name == "kit-kit-1"
    assert found.description == "A test kit"
    assert found.version == "1.0.0"
    assert found.tags == ["python", "web"]          # roundtrip JSON list
    assert found.values == {"port": 8080, "debug": False}  # roundtrip JSON dict
    assert found.debug_level == "info"
    assert found.sync_status == SyncStatus("synced")
    assert found.last_commit_sha == "abc123"
    assert found.is_deleted is False

    # usuario incorrecto → None
    assert await kit_repository.find_by_id("kit-1", "other-user") is None


# ---------------------------------------------------------------------------
# T-19 — Test 2: find_by_id filtra deleted; find_by_id_internal no filtra
# ---------------------------------------------------------------------------


async def test_find_by_id_filters_deleted_and_find_by_id_internal(
    kit_repository, repository_repository
):
    """find_by_id devuelve None para kits deleted; find_by_id_internal los devuelve."""
    await repository_repository.save(_make_repository("repo-1"))

    deleted_kit = _make_kit("kit-deleted", "repo-1", is_deleted=True)
    await kit_repository.save(deleted_kit)

    # find_by_id: kit borrado → None aunque id y user_id sean correctos
    assert await kit_repository.find_by_id("kit-deleted", "user-1") is None

    # find_by_id: id inexistente → None
    assert await kit_repository.find_by_id("does-not-exist", "user-1") is None

    # find_by_id_internal: devuelve el kit aunque esté borrado
    internal = await kit_repository.find_by_id_internal("kit-deleted")
    assert internal is not None
    assert internal.id == "kit-deleted"
    assert internal.is_deleted is True

    # find_by_id_internal: id inexistente → None
    assert await kit_repository.find_by_id_internal("does-not-exist") is None


# ---------------------------------------------------------------------------
# T-19 — Test 3: find_by_repository_id incluye kits deleted (reconciliación sync)
# ---------------------------------------------------------------------------


async def test_find_by_repository_id_includes_deleted(
    kit_repository, repository_repository
):
    """find_by_repository_id devuelve todos los kits del repo, incluidos los deleted."""
    await repository_repository.save(_make_repository("repo-1"))
    await repository_repository.save(_make_repository("repo-2"))

    await kit_repository.save(_make_kit("kit-active", "repo-1", path_in_repo="tools/a"))
    await kit_repository.save(_make_kit("kit-deleted", "repo-1", path_in_repo="tools/b", is_deleted=True))
    await kit_repository.save(_make_kit("kit-other-repo", "repo-2", path_in_repo="tools/c"))

    kits = await kit_repository.find_by_repository_id("repo-1")

    assert len(kits) == 2
    ids = {k.id for k in kits}
    assert ids == {"kit-active", "kit-deleted"}

    # El kit de otro repositorio no aparece
    kits_repo2 = await kit_repository.find_by_repository_id("repo-2")
    assert len(kits_repo2) == 1
    assert kits_repo2[0].id == "kit-other-repo"

    # Repositorio sin kits → lista vacía
    assert await kit_repository.find_by_repository_id("repo-empty") == []


# ---------------------------------------------------------------------------
# T-19 — Test 4: find_all_by_user con filtros y update
# ---------------------------------------------------------------------------


async def test_find_all_by_user_with_filters_and_update(
    kit_repository, repository_repository
):
    """find_all_by_user respeta is_deleted, tags_filter AND, repository_id_filter y paginación.
    update persiste correctamente los cambios de la entidad.
    """
    await repository_repository.save(_make_repository("repo-1"))
    await repository_repository.save(_make_repository("repo-2"))

    # Kit A: tags python + web, repo-1
    await kit_repository.save(_make_kit("kit-a", "repo-1", path_in_repo="a", tags=["python", "web"]))
    # Kit B: tags python + database, repo-1
    await kit_repository.save(_make_kit("kit-b", "repo-1", path_in_repo="b", tags=["python", "database"]))
    # Kit C: tags web (solo), repo-2
    await kit_repository.save(_make_kit("kit-c", "repo-2", path_in_repo="c", tags=["web"]))
    # Kit D: deleted, repo-1
    await kit_repository.save(_make_kit("kit-d", "repo-1", path_in_repo="d", is_deleted=True))

    # Sin filtros: solo activos (A, B, C)
    all_kits = await kit_repository.find_all_by_user("user-1", page=1, per_page=10)
    assert len(all_kits) == 3
    assert {k.id for k in all_kits} == {"kit-a", "kit-b", "kit-c"}

    # tags_filter AND: ["python", "web"] → solo kit-a (tiene ambos tags)
    filtered = await kit_repository.find_all_by_user(
        "user-1", page=1, per_page=10, tags_filter=["python", "web"]
    )
    assert len(filtered) == 1
    assert filtered[0].id == "kit-a"

    # tags_filter: ["python"] → kit-a y kit-b
    filtered_python = await kit_repository.find_all_by_user(
        "user-1", page=1, per_page=10, tags_filter=["python"]
    )
    assert len(filtered_python) == 2
    assert {k.id for k in filtered_python} == {"kit-a", "kit-b"}

    # repository_id_filter: solo kits de repo-1 activos (A, B)
    filtered_repo = await kit_repository.find_all_by_user(
        "user-1", page=1, per_page=10, repository_id_filter="repo-1"
    )
    assert len(filtered_repo) == 2
    assert {k.id for k in filtered_repo} == {"kit-a", "kit-b"}

    # paginación: page=1 per_page=2 → 2 resultados; page=2 per_page=2 → 1 resultado
    page1 = await kit_repository.find_all_by_user("user-1", page=1, per_page=2)
    page2 = await kit_repository.find_all_by_user("user-1", page=2, per_page=2)
    assert len(page1) == 2
    assert len(page2) == 1
    assert {k.id for k in page1}.isdisjoint({k.id for k in page2})

    # --- update: modificar campos y verificar persistencia ---
    kit_a = await kit_repository.find_by_id("kit-a", "user-1")
    assert kit_a is not None
    kit_a.name = "updated-name"
    kit_a.tags = ["python", "web", "api"]
    kit_a.values = {"port": 9090}
    kit_a.version = "2.0.0"
    kit_a.updated_at = datetime(2024, 6, 1, 0, 0, 0)
    await kit_repository.update(kit_a)

    refreshed = await kit_repository.find_by_id("kit-a", "user-1")
    assert refreshed is not None
    assert refreshed.name == "updated-name"
    assert refreshed.tags == ["python", "web", "api"]
    assert refreshed.values == {"port": 9090}
    assert refreshed.version == "2.0.0"
    assert refreshed.updated_at == datetime(2024, 6, 1, 0, 0, 0)
