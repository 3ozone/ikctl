"""Tests para endpoints de autenticación y usuarios."""
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


class TestAuth:
    """Tests para autenticación."""

    def test_register_user_success(self):
        """Test registro de usuario exitoso."""
        response = client.post(
            "/register",
            json={
                "name": "Juan Pérez",
                "email": "juan@example.com",
                "password": "secretpassword123"
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["name"] == "Juan Pérez"
        assert data["email"] == "juan@example.com"
        assert "password" not in data
        assert "created_at" in data

    def test_register_user_invalid_email(self):
        """Test registro con email inválido."""
        response = client.post(
            "/register",
            json={
                "name": "Juan Pérez",
                "email": "invalid-email",
                "password": "secretpassword123"
            }
        )
        assert response.status_code == 400

    def test_register_user_duplicate_email(self):
        """Test registro con email duplicado."""
        user_data = {
            "name": "Juan Pérez",
            "email": "duplicate@example.com",
            "password": "secretpassword123"
        }
        # Primer registro
        client.post("/register", json=user_data)
        # Segundo registro con mismo email
        response = client.post("/register", json=user_data)
        assert response.status_code == 409

    def test_login_success(self):
        """Test login exitoso."""
        # Primero registrar usuario
        client.post(
            "/register",
            json={
                "name": "Test User",
                "email": "test@example.com",
                "password": "testpass123"
            }
        )
        # Luego hacer login
        response = client.post(
            "/login",
            json={
                "email": "test@example.com",
                "password": "testpass123"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_login_invalid_credentials(self):
        """Test login con credenciales inválidas."""
        response = client.post(
            "/login",
            json={
                "email": "noexiste@example.com",
                "password": "wrongpass"
            }
        )
        assert response.status_code == 401


class TestUserProfile:
    """Tests para perfil de usuario."""

    def test_get_user_profile_success(self):
        """Test obtener perfil de usuario autenticado."""
        # Registrar y obtener token
        client.post(
            "/register",
            json={
                "name": "Profile User",
                "email": "profile@example.com",
                "password": "pass123"
            }
        )
        login_response = client.post(
            "/login",
            json={
                "email": "profile@example.com",
                "password": "pass123"
            }
        )
        token = login_response.json()["access_token"]

        # Obtener perfil
        response = client.get(
            "/users/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "profile@example.com"
        assert data["name"] == "Profile User"

    def test_get_user_profile_unauthorized(self):
        """Test obtener perfil sin token."""
        response = client.get("/users/me")
        assert response.status_code == 401

    def test_update_user_name_success(self):
        """Test actualizar nombre de usuario."""
        # Registrar y obtener token
        client.post(
            "/register",
            json={
                "name": "Old Name",
                "email": "update@example.com",
                "password": "pass123"
            }
        )
        login_response = client.post(
            "/login",
            json={
                "email": "update@example.com",
                "password": "pass123"
            }
        )
        token = login_response.json()["access_token"]

        # Actualizar nombre
        response = client.put(
            "/users/me",
            headers={"Authorization": f"Bearer {token}"},
            json={"name": "New Name"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "New Name"

    def test_update_user_name_unauthorized(self):
        """Test actualizar nombre sin autenticación."""
        response = client.put(
            "/users/me",
            json={"name": "New Name"}
        )
        assert response.status_code == 401

    def test_update_password_success(self):
        """Test cambiar contraseña."""
        # Registrar y obtener token
        client.post(
            "/register",
            json={
                "name": "Password User",
                "email": "password@example.com",
                "password": "oldpass123"
            }
        )
        login_response = client.post(
            "/login",
            json={
                "email": "password@example.com",
                "password": "oldpass123"
            }
        )
        token = login_response.json()["access_token"]

        # Cambiar contraseña
        response = client.put(
            "/users/me/password",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "current_password": "oldpass123",
                "new_password": "newpass456"
            }
        )
        assert response.status_code == 200

        # Verificar que la nueva contraseña funciona
        login_response = client.post(
            "/login",
            json={
                "email": "password@example.com",
                "password": "newpass456"
            }
        )
        assert login_response.status_code == 200

    def test_update_password_wrong_current(self):
        """Test cambiar contraseña con contraseña actual incorrecta."""
        # Registrar y obtener token
        client.post(
            "/register",
            json={
                "name": "Wrong Pass User",
                "email": "wrongpass@example.com",
                "password": "correctpass123"
            }
        )
        login_response = client.post(
            "/login",
            json={
                "email": "wrongpass@example.com",
                "password": "correctpass123"
            }
        )
        token = login_response.json()["access_token"]

        # Intentar cambiar con contraseña incorrecta
        response = client.put(
            "/users/me/password",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "current_password": "wrongpass",
                "new_password": "newpass456"
            }
        )
        assert response.status_code == 401

    def test_update_password_unauthorized(self):
        """Test cambiar contraseña sin autenticación."""
        response = client.put(
            "/users/me/password",
            json={
                "current_password": "oldpass",
                "new_password": "newpass"
            }
        )
        assert response.status_code == 401
