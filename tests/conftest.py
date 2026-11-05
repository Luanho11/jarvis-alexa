import pytest


@pytest.fixture(autouse=True)
def sin_google(monkeypatch):
    # config.py carga el .env real: sin esto, las pruebas de la agenda llamarían al Apps Script del usuario.
    for variable in ("GOOGLE_SCRIPT_URL", "GOOGLE_SCRIPT_CLAVE", "GOOGLE_AGENDA"):
        monkeypatch.delenv(variable, raising=False)
