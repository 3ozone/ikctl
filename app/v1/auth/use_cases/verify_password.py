"""Use Case para verificar contraseñas contra su hash bcrypt."""
import bcrypt


class VerifyPassword:
    """Use Case para verificar si un plaintext coincide con un hash bcrypt.

    Compara de forma segura un plaintext contra un hash usando bcrypt.
    """

    def execute(self, plaintext: str, hashed: str) -> bool:
        """Verifica si el plaintext coincide con el hash.

        Args:
            plaintext: Contraseña en texto plano a verificar
            hashed: Hash bcrypt almacenado

        Returns:
            True si coinciden, False en caso contrario
        """
        # bcrypt.checkpw compara plaintext contra hash de forma segura
        return bcrypt.checkpw(
            plaintext.encode('utf-8'),
            hashed.encode('utf-8')
        )
