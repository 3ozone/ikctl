"""Tests para la entity Group."""
from datetime import datetime

from app.v1.servers.domain.entities.group import Group


CREATED_AT = datetime(2026, 1, 1, 12, 0, 0)
UPDATED_AT = datetime(2026, 1, 1, 12, 0, 0)


class TestGroupCreation:
    """Tests para la creación de la entity Group."""

    def test_group_valid(self):
        """Un grupo con name y server_ids es válido."""
        group = Group(
            id="grp-1",
            user_id="user-1",
            name="Producción",
            description="Servidores de producción",
            server_ids=["srv-1", "srv-2"],
            created_at=CREATED_AT,
            updated_at=UPDATED_AT,
        )
        assert group.name == "Producción"
        assert len(group.server_ids) == 2

    def test_group_without_description_valid(self):
        """Un grupo sin description es válido."""
        group = Group(
            id="grp-2",
            user_id="user-1",
            name="Staging",
            description=None,
            server_ids=[],
            created_at=CREATED_AT,
            updated_at=UPDATED_AT,
        )
        assert group.description is None


class TestGroupCommands:
    """Tests para los comandos de negocio de la entity Group."""

    def _make_group(self) -> Group:
        return Group(
            id="grp-3",
            user_id="user-1",
            name="Mi Grupo",
            description=None,
            server_ids=["srv-1"],
            created_at=CREATED_AT,
            updated_at=UPDATED_AT,
        )

    def test_add_server_appends_server_id(self):
        """add_server() añade el server_id a la lista."""
        group = self._make_group()
        group.add_server("srv-2")
        assert "srv-2" in group.server_ids

    def test_remove_server_removes_server_id(self):
        """remove_server() elimina el server_id de la lista."""
        group = self._make_group()
        group.remove_server("srv-1")
        assert "srv-1" not in group.server_ids

    def test_update_modifies_mutable_fields(self):
        """update() cambia name, description y server_ids."""
        group = self._make_group()
        new_updated_at = datetime(2026, 6, 1, 0, 0, 0)
        group.update(
            name="Nuevo Nombre",
            description="Nueva descripción",
            server_ids=["srv-3", "srv-4"],
            updated_at=new_updated_at,
        )
        assert group.name == "Nuevo Nombre"
        assert group.description == "Nueva descripción"
        assert group.server_ids == ["srv-3", "srv-4"]
        assert group.updated_at == new_updated_at


class TestGroupEquality:
    """Tests para la igualdad por identidad de la entity Group."""

    def test_eq_by_id(self):
        """Dos Group con el mismo id son iguales aunque difieran en campos."""
        group_a = Group(
            id="grp-4",
            user_id="user-1",
            name="A",
            description=None,
            server_ids=["srv-1"],
            created_at=CREATED_AT,
            updated_at=UPDATED_AT,
        )
        group_b = Group(
            id="grp-4",
            user_id="user-2",
            name="B",
            description="Diferente",
            server_ids=["srv-2", "srv-3"],
            created_at=CREATED_AT,
            updated_at=UPDATED_AT,
        )
        assert group_a == group_b
