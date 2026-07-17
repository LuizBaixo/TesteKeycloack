# Arquitetura de Microserviços e Single Sign-On (SSO) com Keycloak e Django

Este repositório contém uma implementação funcional de **Single Sign-On (SSO)** para duas aplicações independentes em Python/Django — **App Agenda** e **App To-Do List** — usando o **Keycloak** como provedor de identidade (Identity Provider - IdP) via **OpenID Connect (OIDC)**.

## Execução local

Pré-requisito: Docker com Docker Compose. Não é necessário instalar Python na máquina host.

1. Copie `.env.example` para `.env` e substitua as credenciais antes de usar fora de desenvolvimento. Os `client secrets` do `.env` (`AGENDA_OIDC_CLIENT_SECRET`, `TODO_OIDC_CLIENT_SECRET`) devem permanecer iguais aos definidos em `keycloak/realm-export.json`, pois a importação do Realm é estática.
2. Execute `docker compose up --build`.
3. Acesse a Agenda em `http://localhost:8001`, o To-Do List em `http://localhost:8002` e o painel do Keycloak em `http://localhost:8080`.

O Realm `sso-platform` importa três usuários de demonstração com senha temporária `senha123`; o Keycloak exigirá sua troca no primeiro login. Nunca use essas contas ou os valores de `.env.example` em produção.

Para reiniciar a importação do Realm durante o desenvolvimento, execute `docker compose down -v` antes de subir os serviços novamente. Esse comando remove os bancos locais.

---

## 1. Visão Geral da Arquitetura

A arquitetura adota uma abordagem descentralizada para os serviços de negócio (Agenda e Tarefas) e centralizada para a governança de identidade e credenciais.

```
                               +---------------------------------------+
                               |               KEYCLOAK                |
                               |          (Identity Provider)          |
                               +-------------------+-------------------+
                                                   |
                             Fluxo de Autenticação | (Authorization Code)
                                                   |
                 +---------------------------------+---------------------------------+
                 |                                                                   |
                 v                                                                   v
+---------------------------------+                                 +---------------------------------+
|           APP AGENDA            |                                 |          APP TO-DO LIST         |
|      (Django Client / RP)       |                                 |      (Django Client / RP)       |
+---------------------------------+                                 +---------------------------------+
| - Gerenciamento de Compromissos |                                 | - Gerenciamento de Tarefas      |
| - Banco de Dados Isolado        |                                 | - Banco de Dados Isolado        |
+---------------------------------+                                 +---------------------------------+
```

### Componentes Core:
1.  **Identity Provider (Keycloak):** Centralizador das contas de usuários, senhas e concessão de tokens de acesso (JWT).
2.  **Relying Parties (RP / Clients):** As duas aplicações Django agem como clientes OIDC que confiam no Keycloak para validar quem é o usuário autenticado.
3.  **Isolamento de Dados:** Cada aplicação possui seu próprio banco de dados Postgres (`agenda-db`, `todo-db`), sem compartilhamento de tabelas entre os dois sistemas.

---

## 2. Fluxo de Autenticação e Autorização (OIDC)

O processo de autenticação segue o fluxo padronizado pelo OIDC (**Authorization Code Flow**):

```
[ Usuário ]            [ Django App ]          [ Browser ]            [ Keycloak ]
     |                       |                      |                      |
     |--- 1. Acessa App ---->|                      |                      |
     |                       |--- 2. Redireciona -->|                      |
     |                       |      (Se sem sessão) |--- 3. Req Login ---->|
     |                       |                      |                      | (Solicita credenciais)
     |                       |                      |<-- 4. Exibe Tela ----|
     |<-- 5. Digita Senha ---|                      |                      |
     |                       |                      |--- 6. Envia Cred ----> (Valida e gera Code)
     |                       |                      |<-- 7. Redireciona ---| com o ?code=XYZ
     |                       |<-- 8. Envia Code ----|                      |
     |                       |                                             |
     |                       |--------- 9. Troca Code por Token ---------->| (Backchannel seguro)
     |                       |<-------- 10. Retorna ID, Access & Refresh --|
     |                       |
     |                       |-- 11. Valida Roles do Token e cria sessão --|
     |<-- 12. Acesso Ok -----|
```

1.  **Desafio de Autenticação:** O usuário tenta acessar a Agenda ou o To-Do List. Caso não possua sessão local ativa, o Middleware OIDC intercepta e o redireciona para a URL de login do Keycloak (`LOGIN_URL = "oidc_authentication_init"`).
2.  **SSO (Single Sign-On):** Se o usuário já tiver efetuado login no Keycloak através de outra aplicação do ecossistema, o Keycloak identifica o cookie de sessão ativa e concede o acesso imediatamente, sem requerer nova digitação de senha.
3.  **Backchannel Token Exchange:** A aplicação Django recebe um `Authorization Code` temporário e realiza uma requisição direta de servidor para servidor (backchannel) para trocá-lo pelos tokens JWT (`Access Token`, `ID Token` e `Refresh Token`).
4.  **Consumo de Roles:** O Django valida a assinatura do `ID Token` (RS256) através das chaves públicas expostas pelo Keycloak (`OIDC_OP_JWKS_ENDPOINT`) e mapeia `realm_access.roles` para grupos Django dentro de `KeycloakBackend` (ver seção 5).

---

## 3. Matriz de Controle de Acesso (RBAC)

A governança sobre o que cada usuário pode ou não fazer é definida usando **Role-Based Access Control (RBAC)** no nível do Realm do Keycloak. Cada view protegida usa o decorator `role_required(*roles)`, que checa `request.user.groups` e devolve `403` (via `handler403`) quando a role não bate.

### Definição de Roles (Papéis)
*   `admin`: Papel global que concede acesso completo em ambos os sistemas, além de `is_staff=True` (painel `/admin` do Django).
*   `agenda_user`: Autoriza a visualização, criação e exclusão de compromissos na aplicação Agenda.
*   `todo_user`: Autoriza a criação, conclusão e exclusão de tarefas na aplicação To-Do List.

### Cenários Práticos de Usuários Exemplo

| Usuário | Credencial | Roles Associadas | Escopo de Acesso |
| :--- | :--- | :--- | :--- |
| **`ana_admin`** | `senha123` | `admin`, `agenda_user`, `todo_user` | Acesso irrestrito a ambos os sistemas e ao `/admin` do Django. |
| **`lucas_agenda`** | `senha123` | `agenda_user` | Acesso exclusivo ao ecossistema da **Agenda**. Bloqueado (403) no To-Do List. |
| **`julia_todo`** | `senha123` | `todo_user` | Acesso exclusivo ao ecossistema do **To-Do List**. Bloqueado (403) na Agenda. |

---

## 3.1 Login social com Google

O Realm `sso-platform` tem um Identity Provider Google (`alias: google`) habilitado. Como o IdP é compartilhado pelos dois clients (`agenda` e `todo`), o botão "Google" aparece automaticamente na tela de login do Keycloak para as duas aplicações, e cada Django app também expõe um botão **"Continuar com Google"** na sua própria tela inicial (quando não há sessão ativa) que pula direto para o Google via `kc_idp_hint=google` (`GoogleOIDCAuthenticationRequestView`), sem passar pela tela de escolha do Keycloak.

**Provisionamento automático de acesso:** um usuário que nunca logou em nenhuma das apps e chega pelo Google não possui nenhuma role do Realm. Para que o acesso "já venha liberado" para a aplicação que ele usou para entrar (conforme a Matriz de RBAC da seção 3), o fluxo funciona assim:

1. O IdP `google` tem um mapper `hardcoded-attribute-idp-mapper` que grava o atributo `signup_via=google` no usuário do Keycloak no primeiro login social.
2. Cada client (`agenda`, `todo`) expõe esse atributo como claim `signup_via` no token.
3. No primeiro login em cada app (`KeycloakBackend.create_user`, em `agenda_project/oidc_backend.py` e `todo_project/oidc_backend.py`), se `signup_via == "google"` e o usuário ainda não tem a role da app (`agenda_user`/`todo_user`) nem `admin`, a app concede essa role diretamente no Keycloak via Admin REST API (usando o service account do próprio client, com as roles `manage-users` e `view-realm` do client `realm-management`) — e já reflete isso na sessão atual, sem precisar de novo login.

Isso só dispara para usuários **novos** sem role nenhuma (na prática, contas Google inéditas); contas locais de demonstração já vêm com suas roles pré-definidas no `realm-export.json` e não são afetadas — o isolamento de acesso entre Agenda e To-Do (ex.: `lucas_agenda` bloqueado no To-Do) continua valendo.

**Configuração das credenciais Google:** `keycloak/realm-export.json` (`identityProviders[0].config`) traz `clientId`/`clientSecret` como placeholders (`CHANGE_ME_GOOGLE_OAUTH_CLIENT_ID` / `CHANGE_ME_GOOGLE_OAUTH_CLIENT_SECRET`) — não há credencial real versionada. Para habilitar o login com Google localmente:

1. Crie um OAuth Client ID no [Google Cloud Console](https://console.cloud.google.com/apis/credentials) com o Redirect URI:
   ```
   http://localhost:8080/realms/sso-platform/broker/google/endpoint
   ```
2. Preencha `clientId`/`clientSecret` reais em `keycloak/realm-export.json` **antes** do primeiro `docker compose up` (a importação do Realm é estática), ou configure-os manualmente depois pelo Admin Console (**Identity providers → Google**).
3. Nunca faça commit de credenciais reais nesses campos — mantenha o arquivo com placeholders no controle de versão.

---

## 4. Estrutura de Diretórios do Projeto

```text
Keycloack/
│
├── docker-compose.yml         # Orquestração do Keycloak, Bancos de Dados e Apps
├── .env.example                # Template de variáveis de ambiente (copiar para .env)
│
├── keycloak/
│   └── realm-export.json      # Configurações pré-definidas (Realm, Clients, Roles, IdP Google e Usuários)
│
├── app_agenda/                # Microserviço 1 - Django
│   ├── manage.py
│   ├── agenda_project/
│   │   ├── settings.py        # Config. mozilla-django-oidc & Middleware
│   │   ├── oidc.py            # Logout central + entrada direta pelo Google
│   │   ├── oidc_backend.py    # KeycloakBackend: roles -> grupos Django
│   │   └── urls.py
│   └── core/                  # Views, Models (Appointment) e Templates da Agenda
│
└── app_todo/                  # Microserviço 2 - Django
    ├── manage.py
    ├── todo_project/
    │   ├── settings.py        # Config. mozilla-django-oidc & Middleware
    │   ├── oidc.py             # Logout central + entrada direta pelo Google
    │   ├── oidc_backend.py    # KeycloakBackend: roles -> grupos Django
    │   └── urls.py
    └── tasks/                  # Views, Models (Task) e Templates do To-Do
```

---

## 5. Implementação Django (estado atual)

1.  **Biblioteca OIDC:** `mozilla-django-oidc` (ver `requirements.txt` de cada app), configurada via `OIDC_RP_*` / `OIDC_OP_*` em `settings.py`. `OIDC_RP_SIGN_ALGO = "RS256"` é explícito porque a biblioteca assume HS256 por padrão, e o Keycloak assina os ID Tokens com RSA.
2.  **Login/Logout:** `LOGIN_URL = "oidc_authentication_init"` (rota da própria biblioteca, montada em `path("oidc/", include("mozilla_django_oidc.urls"))`). O logout usa `OIDC_OP_LOGOUT_URL_METHOD = "<app>.oidc.logout_url"`, que redireciona também para o endpoint de logout do Keycloak, encerrando a sessão central.
3.  **Mapeamento de Roles → Grupos Django:** `KeycloakBackend` (em `oidc_backend.py`, subclasse de `OIDCAuthenticationBackend`) lê `realm_access.roles` do token em `create_user`/`update_user`, sincroniza `user.groups` com as roles conhecidas (`admin`, `agenda_user`, `todo_user`) e define `is_staff = "admin" in roles`. É essa mesma classe que faz o auto-provisionamento de acesso via Google descrito na seção 3.1.
4.  **Proteção de Views:** o decorator `role_required(*roles)` (definido em cada `views.py`) combina `@login_required` com uma checagem de `request.user.groups`, levantando `PermissionDenied` (HTTP `403`) quando a role não corresponde. `handler403` em `urls.py` renderiza um template `403.html` próprio de cada app.

### Funcionalidades implementadas

*   **Agenda (`app_agenda/core`):** calendário mensal navegável (`?month=YYYY-MM`), criação e exclusão de compromissos (`Appointment`: título, data/hora, observações, cor), escopados ao usuário autenticado (`owner`).
*   **To-Do List (`app_todo/tasks`):** listagem de tarefas (`Task`: título, prazo opcional, concluída), criação, alternância de status concluído/pendente e exclusão, escopadas ao usuário autenticado (`owner`).
