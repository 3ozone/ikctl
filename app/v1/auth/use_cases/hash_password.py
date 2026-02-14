"""Use Case para hashear contraseñas con bcrypt."""
import bcrypt


class HashPassword:
    """Use Case para hashear una contraseña en plaintext.

    Utiliza bcrypt con costo 12 (~70ms) para seguridad.
    """

    BCRYPT_COST = 12

    def execute(self, plaintext: str) -> str:
        """Hasheá una contraseña plaintext.

        Args:
            plaintext: Contraseña en texto plano

        Returns:
            Hash bcrypt de la contraseña
        """
        # bcrypt.hashpw retorna bytes, convertir a string
        hashed_bytes = bcrypt.hashpw(
            plaintext.encode('utf-8'),
            bcrypt.gensalt(rounds=self.BCRYPT_COST)
        )
        return hashed_bytes.decode('utf-8')
