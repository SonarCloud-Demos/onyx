from types import SimpleNamespace
from typing import cast

import pytest

from onyx.db.enums import SSOProviderType
from onyx.db.models import SSOProvider
from onyx.error_handling.exceptions import OnyxError
from onyx.server.manage.sso.api import _reject_unsafe_saml_config
from onyx.server.manage.sso.models import SSOProviderResponse
from onyx.utils.sensitive import make_mock_sensitive_value


def _saml_config(**overrides: str) -> dict[str, str]:
    config = {
        "idp_entity_id": "https://saml.example.com/entityid",
        "idp_sso_url": "https://mocksaml.com/api/saml/sso",
        "idp_x509_cert": "Zm9v",
        "sp_entity_id": "onyx-mocksaml",
    }
    config.update(overrides)
    return config


def test_reject_unsafe_saml_config_accepts_mock_saml_shape() -> None:
    _reject_unsafe_saml_config(_saml_config())


def test_reject_unsafe_saml_config_rejects_bad_cert() -> None:
    with pytest.raises(OnyxError):
        _reject_unsafe_saml_config(_saml_config(idp_x509_cert="not a certificate"))


def test_reject_unsafe_saml_config_rejects_private_idp_url() -> None:
    with pytest.raises(OnyxError):
        _reject_unsafe_saml_config(
            _saml_config(idp_sso_url="http://169.254.169.254/sso")
        )


def test_sso_provider_response_includes_authorize_url() -> None:
    provider = cast(
        SSOProvider,
        SimpleNamespace(
            id=1,
            name="mocksaml",
            display_name="Mock SAML",
            provider_type=SSOProviderType.SAML,
            enabled=True,
            allowed_email_domains=[],
            config=make_mock_sensitive_value(_saml_config()),
        ),
    )

    response = SSOProviderResponse.from_model(provider, "https://onyx.example.com")

    assert response.redirect_uri == "https://onyx.example.com/auth/saml/callback"
    assert response.authorize_url == "/api/auth/saml/mocksaml/authorize"
