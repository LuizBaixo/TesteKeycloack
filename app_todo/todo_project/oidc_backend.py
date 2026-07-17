import logging

import requests
from django.conf import settings
from django.contrib.auth.models import Group
from mozilla_django_oidc.auth import OIDCAuthenticationBackend

logger = logging.getLogger(__name__)

KNOWN_ROLES = {"admin", "agenda_user", "todo_user"}
APP_ROLE = "todo_user"


class KeycloakBackend(OIDCAuthenticationBackend):
    def create_user(self, claims):
        user = super().create_user(claims)
        roles = set(claims.get("realm_access", {}).get("roles", []))
        # Usuário novo, chegou pelo Google e ainda não tem acesso ao To-Do:
        # concede a role no Keycloak (via Admin API) para que o pedido de
        # acesso feito através desta app já seja atendido neste próprio login.
        if claims.get("signup_via") == "google" and not roles & {"admin", APP_ROLE}:
            if self._grant_role_in_keycloak(claims.get("sub"), APP_ROLE):
                roles.add(APP_ROLE)
        return self._sync_user(user, claims, roles)

    def update_user(self, user, claims):
        roles = set(claims.get("realm_access", {}).get("roles", []))
        return self._sync_user(user, claims, roles)

    def _sync_user(self, user, claims, roles):
        user = super().update_user(user, claims)
        user.username = claims.get("preferred_username", user.username)
        groups = [Group.objects.get_or_create(name=role)[0] for role in roles & KNOWN_ROLES]
        user.groups.set(groups)
        user.is_staff = "admin" in roles
        user.save(update_fields=["username", "is_staff"])
        return user

    def _grant_role_in_keycloak(self, subject_id, role_name):
        if not subject_id:
            return False
        admin_base = settings.OIDC_OP_ADMIN_API_BASE
        try:
            token_response = requests.post(
                settings.OIDC_OP_TOKEN_ENDPOINT,
                data={
                    "grant_type": "client_credentials",
                    "client_id": settings.OIDC_RP_CLIENT_ID,
                    "client_secret": settings.OIDC_RP_CLIENT_SECRET,
                },
                timeout=5,
            )
            token_response.raise_for_status()
            headers = {"Authorization": f"Bearer {token_response.json()['access_token']}"}

            role_response = requests.get(f"{admin_base}/roles/{role_name}", headers=headers, timeout=5)
            role_response.raise_for_status()

            grant_response = requests.post(
                f"{admin_base}/users/{subject_id}/role-mappings/realm",
                headers=headers,
                json=[role_response.json()],
                timeout=5,
            )
            grant_response.raise_for_status()
            return True
        except requests.RequestException:
            logger.exception("Falha ao conceder a role %s ao usuário %s no Keycloak", role_name, subject_id)
            return False
