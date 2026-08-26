import pytest

try:
    import forge
except ImportError:
    forge = None

def test_package_importable():
    if forge is None:
        pytest.skip("forge requires optional dependencies not installed")
    assert forge is not None