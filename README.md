# Arquitetura de Microserviços e Single Sign-On (SSO) com Keycloak e Django

Este repositório contém o desenho arquitetural e a especificação de infraestrutura para a unificação de identidade e controle de acesso de duas aplicações independentes desenvolvidas em Python/Django: **App Agenda** e **App To-Do List**. 

O objetivo central desta arquitetura é implementar uma solução robusta de **Single Sign-On (SSO)** utilizando o **Keycloak** como provedor de identidade (Identity Provider - IdP) baseado no protocolo **OpenID Connect (OIDC)**.

## Execução local

Pré-requisito: Docker com Docker Compose. Não é necessário instalar Python na máquina host.

1. Copie `.env.example` para `.env` e substitua todas as credenciais antes de usar fora de desenvolvimento. Os `client secrets` do `.env` devem permanecer iguais aos definidos em `keycloak/realm-export.json` (a importação do Realm é estática).
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
1.  **Identity Provider (Keycloak):** Centralizador das contas de usuários, senhas, fluxos de MFA, e concessão de tokens de acesso (JWT).
2.  **Relying Parties (RP / Clients):** As duas aplicações Django agem como clientes OIDC que confiam no Keycloak para validar quem é o usuário autenticado.
3.  **Isolamento de Dados:** Cada aplicação possui seu próprio ciclo de deploy e persistência de dados (Banco de Dados individual), mitigando acoplamentos arquiteturais.

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

1.  **Desafio de Autenticação:** O usuário tenta acessar a Agenda ou o To-Do List. Caso não possua sessão local ativa, o Middleware OIDC intercepta e o redireciona para a URL de login do Keycloak.
2.  **SSO (Single Sign-On):** Se o usuário já tiver efetuado login no Keycloak através de outra aplicação do ecossistema, o Keycloak identifica o cookie de sessão ativa e concede o acesso imediatamente, sem requerer nova digitação de senha.
3.  **Backchannel Token Exchange:** A aplicação Django recebe um `Authorization Code` temporário e realiza uma requisição direta de servidor para servidor (backchannel) para trocá-lo pelos tokens JWT (`Access Token`, `ID Token` e `Refresh Token`).
4.  **Consumo de Roles:** O Django descriptografa o `Access Token` recebido, valida a assinatura criptográfica através das chaves públicas expostas pelo Keycloak (`jwks_url`) e mapeia os perfis de acesso direto no objeto `request.user`.

---

## 3. Matriz de Controle de Acesso (RBAC)

A governança sobre o que cada usuário pode ou não fazer é definida usando **Role-Based Access Control (RBAC)** no nível do Realm do Keycloak. As regras de negócio avaliam essas claims em tempo de execução.

### Definição de Roles (Papéis)
*   `admin`: Papel global que concede prerrogativas completas de escrita, leitura e deleção em todos os ecossistemas, além de acesso aos painéis de administração do Django (`/admin`).
*   `agenda_user`: Autoriza a visualização, criação e deleção de cronogramas na aplicação Agenda.
*   `todo_user`: Autoriza a criação, atualização e encerramento de atividades na aplicação To-Do List.

### Cenários Práticos de Usuários Exemplo

| Usuário | Credencial | Roles Associadas | Escopo de Acesso |
| :--- | :--- | :--- | :--- |
| **`ana_admin`** | `senha123` | `admin`, `agenda_user`, `todo_user` | Acesso irrestrito a ambos os sistemas e privilégios de superusuário. |
| **`lucas_agenda`** | `senha123` | `agenda_user` | Acesso exclusivo ao ecossistema da **Agenda**. Bloqueado no To-Do List. |
| **`julia_todo`** | `senha123` | `todo_user` | Acesso exclusivo ao ecossistema do **To-Do List**. Bloqueado na Agenda. |

---

## 3.1 Login social com Google

O Realm `sso-platform` tem um Identity Provider Google (`alias: google`) habilitado. Como o IdP é compartilhado pelos dois clients (`agenda` e `todo`), o botão "Google" aparece automaticamente na tela de login do Keycloak para as duas aplicações, e cada Django app também expõe um botão **"Continuar com Google"** na sua própria tela inicial (quando não há sessão ativa) que pula direto para o Google via `kc_idp_hint=google`, sem passar pela tela de escolha do Keycloak.

**Provisionamento automático de acesso:** um usuário que nunca logou em nenhuma das apps e chega pelo Google não possui nenhuma role do Realm. Para que o acesso "já venha liberado" para a aplicação que ele usou para entrar (conforme a Matriz de RBAC da seção 3), o fluxo funciona assim:

1. O IdP `google` tem um mapper `hardcoded-attribute-idp-mapper` que grava o atributo `signup_via=google` no usuário do Keycloak no primeiro login social.
2. Cada client (`agenda`, `todo`) expõe esse atributo como claim `signup_via` no token.
3. No primeiro login em cada app (`KeycloakBackend.create_user`, em `agenda_project/oidc_backend.py` e `todo_project/oidc_backend.py`), se `signup_via == "google"` e o usuário ainda não tem a role da app (`agenda_user`/`todo_user`) nem `admin`, a app concede essa role diretamente no Keycloak via Admin REST API (usando o service account do próprio client, com as roles `manage-users` e `view-realm` do client `realm-management`) — e já reflete isso na sessão atual, sem precisar de novo login.

Isso só dispara para usuários **novos** sem role nenhuma (na prática, contas Google inéditas); contas locais de demonstração já vêm com suas roles pré-definidas no `realm-export.json` e não são afetadas — o isolamento de acesso entre Agenda e To-Do (ex.: `lucas_agenda` bloqueado no To-Do) continua valendo.

⚠️ **Atenção:** o `client secret` real do Google OAuth está gravado em `keycloak/realm-export.json` (`identityProviders[0].config.clientSecret`) para sobreviver a um `docker compose down -v`. Diferente dos secrets de exemplo dos clients `agenda`/`todo`, este é um credencial real do Google Cloud Console — **não publique este repositório publicamente sem antes rotacionar/remover esse secret** ou movê-lo para um mecanismo de segredo adequado.

Se o Identity Provider Google precisar ser recriado manualmente (Admin Console: **Identity providers → Google**), o Redirect URI esperado pelo Google Cloud Console é:
```
http://localhost:8080/realms/sso-platform/broker/google/endpoint
```

---

## 4. Estrutura de Diretórios do Projeto

```text
meu-sistema-sso/
│
├── docker-compose.yml         # Orquestração do Keycloak, Bancos de Dados e Apps
│
├── keycloak/
│   └── realm-export.json      # Configurações pré-definidas (Realm, Clients, Roles e Usuários)
│
├── app_agenda/                # Microserviço 1 - Django
│   ├── manage.py
│   ├── agenda_project/
│   │   ├── settings.py        # Configurações de Middleware OIDC & URLs de Autenticação
│   │   └── urls.py
│   └── core/                  # Lógica de negócio da Agenda (Views, Models, Templates)
│
└── app_todo/                  # Microserviço 2 - Django
    ├── manage.py
    ├── todo_project/
    │   ├── settings.py        # Configurações de Middleware OIDC & URLs de Autenticação
    │   └── urls.py
    └── tasks/                 # Lógica de negócio do To-Do (Views, Models, Templates)
```

---

## 5. Estratégia de Integração no Django

Para que os códigos Django operem de acordo com esta arquitetura, as seguintes diretrizes de engenharia devem ser observadas durante o desenvolvimento:

1.  **Bibliotecas Recomendadas:** Utilizar `mozilla-django-oidc` ou `django-allauth` com suporte a OpenID Connect.
2.  **Configuração de Rotas:** Substituir a rota de login padrão do Django (`LOGIN_URL`) para direcionar para o endpoint de autenticação do backend OIDC da aplicação.
3.  **Validação de Roles via Decodificação do JWT:**
    *   O Keycloak envia as roles atribuídas dentro do payload do JWT na chave `realm_access.roles`.
    *   Deve ser implementado um `OIDCBackend` customizado estendendo a classe padrão da biblioteca escolhida para interceptar o login, mapear as roles do Keycloak para grupos do Django ou injetar dinamicamente permissões/flags (`is_staff`, `is_superuser`).
4.  **Proteção de Views:** Utilizar os decoradores padrão do Django como `@login_required` combinado com mixins ou decorators customizados que inspecionem as roles do usuário para barrar requisições não autorizadas com um HTTP `403 Forbidden`.
