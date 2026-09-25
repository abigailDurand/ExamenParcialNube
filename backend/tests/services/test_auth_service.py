"""test-specs.md › BACKEND › Pruebas de servicios — Login y JWT (unitarias, sin BD)."""
import logging
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi import HTTPException

from config import get_settings
from repository import users_repository
from services import auth_service
from services.security import create_access_token, decode_access_token, hash_password

PASSWORD = "Clave-Correcta-123"
HASH = hash_password(PASSWORD)
USUARIO = {"id": 7, "email": "admin@correo.com", "password_hash": HASH}


@pytest.fixture
def repo_falso(monkeypatch):
    llamadas = []

    async def get_user_by_email(email):
        llamadas.append(email)
        return USUARIO if email == USUARIO["email"] else None

    async def get_user_by_id(user_id):
        return {"id": USUARIO["id"], "email": USUARIO["email"]} if user_id == USUARIO["id"] else None

    monkeypatch.setattr(users_repository, "get_user_by_email", get_user_by_email)
    monkeypatch.setattr(users_repository, "get_user_by_id", get_user_by_id)
    return llamadas


async def test_login_correcto_devuelve_jwt_valido_con_expiracion(repo_falso):
    """Spec: 'Login: con correo y contraseña correctos devuelve un JWT válido y con expiración'."""
    resultado = await auth_service.login("admin@correo.com", PASSWORD)
    settings = get_settings()
    payload = jwt.decode(resultado["access_token"], settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    assert resultado["token_type"] == "bearer"
    assert payload["sub"] == "7"
    assert "exp" in payload
    assert resultado["expires_in"] == settings.jwt_expiration_minutes * 60


@pytest.mark.parametrize(
    "email, password",
    [("admin@correo.com", "incorrecta"), ("nadie@correo.com", PASSWORD)],
    ids=["contraseña-incorrecta", "usuario-inexistente"],
)
async def test_login_invalido_levanta_401_con_mensaje_generico(repo_falso, email, password):
    """Spec: 'contraseña incorrecta o usuario inexistente levanta 401 (mensaje genérico)'."""
    with pytest.raises(HTTPException) as exc:
        await auth_service.login(email, password)
    assert exc.value.status_code == 401
    assert exc.value.detail == "Correo o contraseña incorrectos"


async def test_login_normaliza_correo_a_minusculas(repo_falso):
    """Spec: 'el correo se normaliza a minúsculas antes de buscar el usuario'."""
    await auth_service.login("  ADMIN@Correo.COM ", PASSWORD)
    assert repo_falso == ["admin@correo.com"]


async def test_login_no_expone_password_ni_hash_en_respuesta_ni_logs(repo_falso, caplog):
    """Spec: 'la respuesta y los logs nunca incluyen la contraseña ni el hash'."""
    caplog.set_level(logging.DEBUG)
    resultado = await auth_service.login("admin@correo.com", PASSWORD)
    with pytest.raises(HTTPException):
        await auth_service.login("admin@correo.com", "otra-clave-mala")
    texto_respuesta = str(resultado)
    assert PASSWORD not in texto_respuesta and HASH not in texto_respuesta
    assert "password" not in resultado
    assert PASSWORD not in caplog.text and HASH not in caplog.text and "otra-clave-mala" not in caplog.text


def test_jwt_emitido_se_valida_firma_y_expiracion():
    """Spec: 'El JWT emitido se valida correctamente (firma y expiración)'."""
    token, _ = create_access_token(7)
    assert decode_access_token(token) == 7

    settings = get_settings()
    firmado_con_otro_secreto = jwt.encode({"sub": "7", "exp": datetime.now(timezone.utc) + timedelta(minutes=5)},
                                          "otro-secreto-distinto-de-32-bytes-o-mas", algorithm="HS256")
    vencido = jwt.encode({"sub": "7", "exp": datetime.now(timezone.utc) - timedelta(seconds=1)},
                         settings.jwt_secret, algorithm=settings.jwt_algorithm)
    assert decode_access_token(firmado_con_otro_secreto) is None
    assert decode_access_token(vencido) is None


@pytest.mark.parametrize("token", [None, "", "no-es-un-jwt"], ids=["ausente", "vacio", "invalido"])
async def test_token_invalido_o_ausente_levanta_401(repo_falso, token):
    """Spec: 'Rechaza la consulta si el JWT es inválido o expiró (levanta 401)'."""
    with pytest.raises(HTTPException) as exc:
        await auth_service.get_current_user(token)
    assert exc.value.status_code == 401


async def test_token_vencido_levanta_401(repo_falso):
    """Spec: 'Rechaza la consulta si el JWT es inválido o expiró (levanta 401)'."""
    settings = get_settings()
    vencido = jwt.encode({"sub": "7", "exp": datetime.now(timezone.utc) - timedelta(seconds=1)},
                         settings.jwt_secret, algorithm=settings.jwt_algorithm)
    with pytest.raises(HTTPException) as exc:
        await auth_service.get_current_user(vencido)
    assert exc.value.status_code == 401


async def test_token_valido_devuelve_usuario(repo_falso):
    token, _ = create_access_token(7)
    assert await auth_service.get_current_user(token) == {"id": 7, "email": "admin@correo.com"}
