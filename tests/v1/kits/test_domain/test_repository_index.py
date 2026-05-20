"""Tests para el Value Object RepositoryIndex."""
import pytest

from app.v1.kits.domain.value_objects.repository_index import RepositoryIndex
from app.v1.kits.domain.exceptions.kit import MissingRootManifestError


class TestRepositoryIndex:
    """Tests para el Value Object RepositoryIndex."""

    def test_repository_index_valid_single_kit(self):
        """Un índice con un path de kit es válido y expone kit_paths."""
        data = {"kits": ["kits/my-kit"]}
        index = RepositoryIndex.from_dict(data)
        assert index.kit_paths == ("kits/my-kit",)

    def test_repository_index_valid_multiple_kits(self):
        """Un índice con varios paths de kits es válido."""
        data = {"kits": ["kits/haproxy", "kits/nginx", "tools/certbot"]}
        index = RepositoryIndex.from_dict(data)
        assert index.kit_paths == (
            "kits/haproxy", "kits/nginx", "tools/certbot")

    def test_repository_index_missing_kits_section_raises_error(self):
        """Un índice sin sección 'kits' lanza MissingRootManifestError."""
        data = {"name": "my-repo"}
        with pytest.raises(MissingRootManifestError):
            RepositoryIndex.from_dict(data)

    def test_repository_index_empty_kits_section_raises_error(self):
        """Un índice con sección 'kits' vacía lanza MissingRootManifestError."""
        data = {"kits": []}
        with pytest.raises(MissingRootManifestError):
            RepositoryIndex.from_dict(data)
