from selma.memory.config import BackendConfig


def test_default_is_embedded():
    assert BackendConfig().kind == "embedded"