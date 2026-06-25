import pytest
from fastapi import HTTPException
from app.api.dependencies import require_roles

def test_require_roles_auth0_action():
    checker = require_roles(["hr_admin"])
    mock_user = {
        "sub": "auth0|123",
        "https://successcore.com/app_metadata": {
            "roles": ["hr_admin"]
        }
    }
    res = checker(current_user=mock_user)
    assert res == mock_user

def test_require_roles_auth0_native():
    checker = require_roles(["employee"])
    mock_user = {
        "sub": "auth0|123",
        "https://successcore.com/roles": ["employee"]
    }
    res = checker(current_user=mock_user)
    assert res == mock_user

def test_require_roles_direct_payload():
    checker = require_roles(["sys_admin"])
    mock_user = {
        "sub": "auth0|123",
        "roles": ["sys_admin"]
    }
    res = checker(current_user=mock_user)
    assert res == mock_user

def test_require_roles_super_admin_bypass():
    checker = require_roles(["hr_admin"])
    mock_user = {
        "sub": "auth0|123",
        "roles": ["super_admin"]
    }
    res = checker(current_user=mock_user)
    assert res == mock_user

def test_require_roles_denied():
    checker = require_roles(["hr_admin"])
    mock_user = {
        "sub": "auth0|123",
        "roles": ["employee"]
    }
    with pytest.raises(HTTPException) as exc:
        checker(current_user=mock_user)
    assert exc.value.status_code == 403
    assert "No tienes los permisos necesarios" in exc.value.detail

def test_require_roles_missing_roles():
    checker = require_roles(["hr_admin"])
    mock_user = {
        "sub": "auth0|123"
    }
    with pytest.raises(HTTPException) as exc:
        checker(current_user=mock_user)
    assert exc.value.status_code == 403
    assert "Token inválido" in exc.value.detail
