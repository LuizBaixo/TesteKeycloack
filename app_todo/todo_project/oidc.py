from urllib.parse import urlencode

from mozilla_django_oidc.views import OIDCAuthenticationRequestView


def logout_url(request):
    """Encerra também a sessão central do Keycloak."""
    endpoint = "http://localhost:8080/realms/sso-platform/protocol/openid-connect/logout"
    params = {"client_id": "todo", "post_logout_redirect_uri": request.build_absolute_uri("/")}
    return f"{endpoint}?{urlencode(params)}"


class GoogleOIDCAuthenticationRequestView(OIDCAuthenticationRequestView):
    """Pula a tela de escolha de credenciais do Keycloak e vai direto ao Google."""

    def get_extra_params(self, request):
        return {"kc_idp_hint": "google"}
