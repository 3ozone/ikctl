"""Tests para endpoints de servidores."""
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def create_authenticated_user(email="server@example.com", password="pass123"):
    """Helper para crear usuario y obtener token."""
    client.post(
        "/register",
        json={
            "name": "Server User",
            "email": email,
            "password": password
        }
    )
    login_response = client.post(
        "/login",
        json={
            "email": email,
            "password": password
        }
    )
    return login_response.json()["access_token"]


class TestServers:
    """Tests para gestión de servidores."""

    def test_create_server_with_password_success(self):
        """Test crear servidor con autenticación por contraseña."""
        token = create_authenticated_user("srv1@example.com")

        response = client.post(
            "/servers",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "Servidor Producción",
                "host": "192.168.1.100",
                "port": 22,
                "username": "root",
                "auth_type": "password",
                "password": "serverpass123"
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["name"] == "Servidor Producción"
        assert data["host"] == "192.168.1.100"
        assert data["port"] == 22
        assert data["username"] == "root"
        assert data["auth_type"] == "password"
        assert "password" not in data  # No debe devolver la contraseña
        assert "created_at" in data

    def test_create_server_with_ssh_key_success(self):
        """Test crear servidor con autenticación por llave SSH."""
        token = create_authenticated_user("srv2@example.com")

        response = client.post(
            "/servers",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "Servidor Dev",
                "host": "dev.example.com",
                "port": 2222,
                "username": "admin",
                "auth_type": "ssh_key",
                "ssh_key": "-----BEGIN OPENSSH PRIVATE KEY-----\nfake_key\n-----END OPENSSH PRIVATE KEY-----"
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["auth_type"] == "ssh_key"
        assert "ssh_key" not in data  # No debe devolver la llave

    def test_create_server_unauthorized(self):
        """Test crear servidor sin autenticación."""
        response = client.post(
            "/servers",
            json={
                "name": "Servidor Test",
                "host": "192.168.1.100",
                "port": 22,
                "username": "root",
                "auth_type": "password",
                "password": "pass123"
            }
        )
        assert response.status_code == 401

    def test_create_server_invalid_data(self):
        """Test crear servidor con datos inválidos."""
        token = create_authenticated_user("srv3@example.com")

        response = client.post(
            "/servers",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "Servidor Test"
                # Faltan campos requeridos
            }
        )
        assert response.status_code == 400

    def test_list_servers_success(self):
        """Test listar servidores del usuario."""
        token = create_authenticated_user("srv4@example.com")

        # Crear algunos servidores
        client.post(
            "/servers",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "Servidor 1",
                "host": "192.168.1.100",
                "port": 22,
                "username": "root",
                "auth_type": "password",
                "password": "pass123"
            }
        )
        client.post(
            "/servers",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "Servidor 2",
                "host": "192.168.1.101",
                "port": 22,
                "username": "root",
                "auth_type": "password",
                "password": "pass123"
            }
        )

        # Listar servidores
        response = client.get(
            "/servers",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 2

    def test_list_servers_unauthorized(self):
        """Test listar servidores sin autenticación."""
        response = client.get("/servers")
        assert response.status_code == 401

    def test_get_server_success(self):
        """Test obtener detalles de servidor específico."""
        token = create_authenticated_user("srv5@example.com")

        # Crear servidor
        create_response = client.post(
            "/servers",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "Servidor Test",
                "host": "192.168.1.100",
                "port": 22,
                "username": "root",
                "auth_type": "password",
                "password": "pass123"
            }
        )
        server_id = create_response.json()["id"]

        # Obtener detalles
        response = client.get(
            f"/servers/{server_id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == server_id
        assert data["name"] == "Servidor Test"

    def test_get_server_not_found(self):
        """Test obtener servidor que no existe."""
        token = create_authenticated_user("srv6@example.com")

        response = client.get(
            "/servers/99999",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 404

    def test_get_server_unauthorized(self):
        """Test obtener servidor sin autenticación."""
        response = client.get("/servers/1")
        assert response.status_code == 401

    def test_update_server_success(self):
        """Test actualizar servidor."""
        token = create_authenticated_user("srv7@example.com")

        # Crear servidor
        create_response = client.post(
            "/servers",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "Servidor Old",
                "host": "192.168.1.100",
                "port": 22,
                "username": "root",
                "auth_type": "password",
                "password": "pass123"
            }
        )
        server_id = create_response.json()["id"]

        # Actualizar servidor
        response = client.put(
            f"/servers/{server_id}",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "Servidor Updated",
                "host": "192.168.1.200",
                "port": 2222,
                "username": "admin"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Servidor Updated"
        assert data["host"] == "192.168.1.200"
        assert data["port"] == 2222

    def test_update_server_not_found(self):
        """Test actualizar servidor que no existe."""
        token = create_authenticated_user("srv8@example.com")

        response = client.put(
            "/servers/99999",
            headers={"Authorization": f"Bearer {token}"},
            json={"name": "New Name"}
        )
        assert response.status_code == 404

    def test_update_server_unauthorized(self):
        """Test actualizar servidor sin autenticación."""
        response = client.put(
            "/servers/1",
            json={"name": "New Name"}
        )
        assert response.status_code == 401

    def test_delete_server_success(self):
        """Test eliminar servidor."""
        token = create_authenticated_user("srv9@example.com")

        # Crear servidor
        create_response = client.post(
            "/servers",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "Servidor Delete",
                "host": "192.168.1.100",
                "port": 22,
                "username": "root",
                "auth_type": "password",
                "password": "pass123"
            }
        )
        server_id = create_response.json()["id"]

        # Eliminar servidor
        response = client.delete(
            f"/servers/{server_id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 204

        # Verificar que no existe
        get_response = client.get(
            f"/servers/{server_id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert get_response.status_code == 404

    def test_delete_server_not_found(self):
        """Test eliminar servidor que no existe."""
        token = create_authenticated_user("srv10@example.com")

        response = client.delete(
            "/servers/99999",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 404

    def test_delete_server_unauthorized(self):
        """Test eliminar servidor sin autenticación."""
        response = client.delete("/servers/1")
        assert response.status_code == 401
