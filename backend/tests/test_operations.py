"""Tests para endpoints de operaciones."""
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def create_user_and_server(email="ops@example.com"):
    """Helper para crear usuario, autenticarse y crear servidor."""
    # Registrar usuario
    client.post(
        "/register",
        json={
            "name": "Ops User",
            "email": email,
            "password": "pass123"
        }
    )

    # Login
    login_response = client.post(
        "/login",
        json={
            "email": email,
            "password": "pass123"
        }
    )
    token = login_response.json()["access_token"]

    # Crear servidor
    server_response = client.post(
        "/servers",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": "Test Server",
            "host": "192.168.1.100",
            "port": 22,
            "username": "root",
            "auth_type": "password",
            "password": "serverpass123"
        }
    )
    server_id = server_response.json()["id"]

    return token, server_id


class TestConnectionTest:
    """Tests para test de conectividad SSH."""

    def test_connection_success(self):
        """Test de conexión SSH exitoso."""
        token, server_id = create_user_and_server("conn1@example.com")

        response = client.post(
            f"/servers/{server_id}/test-connection",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "success" in data
        assert "message" in data
        assert isinstance(data["success"], bool)

    def test_connection_server_not_found(self):
        """Test de conexión a servidor que no existe."""
        token, _ = create_user_and_server("conn2@example.com")

        response = client.post(
            "/servers/99999/test-connection",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 404

    def test_connection_unauthorized(self):
        """Test de conexión sin autenticación."""
        response = client.post("/servers/1/test-connection")
        assert response.status_code == 401


class TestInstallApplication:
    """Tests para instalación de aplicaciones."""

    def test_install_application_success(self):
        """Test instalación de aplicación exitosa."""
        token, server_id = create_user_and_server("inst1@example.com")

        response = client.post(
            f"/servers/{server_id}/install",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "application": "nginx",
                "version": "latest",
                "options": {
                    "port": 80,
                    "enable": True
                }
            }
        )
        assert response.status_code == 202
        data = response.json()
        assert "id" in data
        assert "server_id" in data
        assert data["server_id"] == server_id
        assert data["type"] == "install"
        assert data["status"] in ["pending", "running"]
        assert "created_at" in data

    def test_install_application_invalid_data(self):
        """Test instalación con datos inválidos."""
        token, server_id = create_user_and_server("inst2@example.com")

        response = client.post(
            f"/servers/{server_id}/install",
            headers={"Authorization": f"Bearer {token}"},
            json={
                # Falta campo requerido "application"
                "version": "latest"
            }
        )
        assert response.status_code == 400

    def test_install_application_server_not_found(self):
        """Test instalación en servidor que no existe."""
        token, _ = create_user_and_server("inst3@example.com")

        response = client.post(
            "/servers/99999/install",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "application": "nginx",
                "version": "latest"
            }
        )
        assert response.status_code == 404

    def test_install_application_unauthorized(self):
        """Test instalación sin autenticación."""
        response = client.post(
            "/servers/1/install",
            json={
                "application": "nginx",
                "version": "latest"
            }
        )
        assert response.status_code == 401


class TestTasks:
    """Tests para consulta de tareas."""

    def test_get_task_status_success(self):
        """Test obtener estado de tarea."""
        token, server_id = create_user_and_server("task1@example.com")

        # Crear tarea (instalación)
        install_response = client.post(
            f"/servers/{server_id}/install",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "application": "nginx",
                "version": "latest"
            }
        )
        task_id = install_response.json()["id"]

        # Consultar estado de tarea
        response = client.get(
            f"/tasks/{task_id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == task_id
        assert "status" in data
        assert data["status"] in ["pending", "running", "completed", "failed"]
        assert "created_at" in data

    def test_get_task_completed(self):
        """Test obtener tarea completada con resultado."""
        token, server_id = create_user_and_server("task2@example.com")

        # Crear y completar tarea
        install_response = client.post(
            f"/servers/{server_id}/install",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "application": "nginx",
                "version": "latest"
            }
        )
        task_id = install_response.json()["id"]

        # Consultar tarea (asumiendo que se completa)
        response = client.get(
            f"/tasks/{task_id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        data = response.json()
        # Puede estar completed o aún running/pending
        if data["status"] == "completed":
            assert "completed_at" in data
            assert data["completed_at"] is not None

    def test_get_task_not_found(self):
        """Test obtener tarea que no existe."""
        token, _ = create_user_and_server("task3@example.com")

        response = client.get(
            "/tasks/99999",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 404

    def test_get_task_unauthorized(self):
        """Test obtener tarea sin autenticación."""
        response = client.get("/tasks/1")
        assert response.status_code == 401

    def test_task_lifecycle(self):
        """Test completo del ciclo de vida de una tarea."""
        token, server_id = create_user_and_server("task4@example.com")

        # 1. Crear instalación (crea tarea)
        install_response = client.post(
            f"/servers/{server_id}/install",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "application": "docker",
                "version": "latest",
                "options": {
                    "compose": True
                }
            }
        )
        assert install_response.status_code == 202
        task_id = install_response.json()["id"]

        # 2. Verificar que tarea está pending o running
        task_response = client.get(
            f"/tasks/{task_id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert task_response.status_code == 200
        assert task_response.json()["status"] in [
            "pending", "running", "completed"]

        # 3. Verificar que tarea tiene server_id correcto
        assert task_response.json()["server_id"] == server_id
