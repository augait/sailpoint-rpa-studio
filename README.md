# SailPoint RPA Studio

**v0.1.0 — primeira entrega executável / Fase 1**

Plataforma modular de RPA web voltada a IAM: cadastre aplicações, monte workflows por etapas,
enfileire execuções e acompanhe logs e evidências. Backend Python, FastAPI, PostgreSQL,
Redis/RQ e Playwright. Interface Jinja + JavaScript modular, sem build Node obrigatório.

Projeto independente, sem vínculo ou homologação da SailPoint. Esta versão é um MVP para
laboratório/DEV. As cinco fases solicitadas não são apresentadas como já implementadas.

## O que funciona

- Login JWT, Argon2id e papéis ADMIN, DEVELOPER, OPERATOR e VIEWER.
- Cadastro de aplicações e criação/edição de workflows com controle otimista de revisão.
- Editor de etapas com propriedades, seletores alternativos, reordenação, duplicação e desativação.
- Ações navigate, click, fill, wait, select, screenshot, extract_text, assert_text, check, press e hover.
- Variáveis por referência `{{username}}` e `{{application.url}}`; sem `eval`.
- Snapshot imutável por execução, fila RQ, contexto de navegador isolado, logs persistidos.
- Resultado, duração, correlação, cancelamento cooperativo e captura de erro na interface.
- Entrada cifrada com Fernet; eliminação após finalizar. Senhas referenciadas, nunca literais em campos marcados.
- Recorder local com captura DOM e exportação/importação de JSON.
- Portal legado fictício e template CREATE_ACCOUNT com 14 etapas.
- Dashboard com dados reais, workers registrados, auditoria, `/health`, `/metrics` e OpenAPI.
- Docker Compose, migração Alembic e testes automatizados.

Veja [arquitetura](docs/ARCHITECTURE.md), [API](docs/API.md), [segurança e limites](docs/SECURITY.md),
[roadmap](docs/ROADMAP.md) e [verificação da entrega](docs/VALIDATION.md).

## Pré-requisitos

- Docker Engine/Desktop e Docker Compose v2; Linux containers no Windows.
- Python 3.12+ para utilitários/gravador local.
- Acesso aos índices de pacotes, imagens Docker e distribuição de navegadores Playwright.
- Para recorder ou worker visível: computador com sessão gráfica.
- Recursos de memória variam com as páginas. Uma VPS de 2 GB é apertada para banco, fila e Chromium juntos;
  comece com um worker e meça a memória do processo real antes de aumentar concorrência.

## Instalação com Docker (recomendada)

Extraia o ZIP e abra o terminal na pasta `sailpoint-rpa-studio`.

```bash
python -m venv .venv
```

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Linux/macOS:

```bash
source .venv/bin/activate
```

Instale dependências e gere configuração local:

```bash
pip install -r requirements.lock
pip install --no-deps -e .
python scripts/configure.py
```

O utilitário cria `.env` com senha PostgreSQL, chave JWT e chave Fernet aleatórias.
Ele não sobrescreve `.env` existente. **Edite `.env` e defina `DEMO_PASSWORD` com uma senha fictícia**
para o portal de demonstração. Ela será fornecida como `admin_password` ao executar o template.
Não reutilize uma senha corporativa.

```bash
docker compose up --build -d
docker compose exec backend python scripts/bootstrap.py admin
```

O bootstrap solicita uma senha de pelo menos 12 caracteres sem exibi-la. Não há credencial padrão.

- Studio: http://localhost:8080
- API: http://localhost:8080/docs
- ReDoc: http://localhost:8080/redoc
- Portal fictício: http://localhost:8081

O Studio usa JWT em memória do navegador. Atualizar a página exige novo login.
PostgreSQL e Redis não expõem portas para o host no Compose padrão.

### Preparar a primeira demonstração

```bash
python scripts/demo_workflow.py --api http://localhost:8080 --legacy-url http://legacy:8081 --username admin
```

O script pede sua senha do Studio e cadastra a aplicação e o workflow por API. Execute uma vez
para evitar conflito com nome já existente. Depois use **Workflows → Abrir designer → Executar teste**.

Preencha:

| Variável | Valor de demonstração |
|---|---|
| admin_username | `demo-admin` |
| admin_password | O valor fictício escolhido em `DEMO_PASSWORD` |
| username | `john.doe` |
| firstname | `John` |
| lastname | `Doe` |
| email | `john.doe@test.local` |
| department | `IT` |

O worker abre Chromium headless, efetua login, cria a conta e valida a mensagem.
O resultado esperado é `SUCCESS` com `{"accountId":"john.doe"}`. Use outro username ao repetir.
A aplicação demo impede duplicação, mas o template espera uma criação nova; conta existente
faz a validação falhar. A política `ALREADY_EXISTS` e o desvio para UPDATE_ACCOUNT são Fase 2/3.

### Criar manualmente

1. Abra **Aplicações → Nova aplicação**. No Docker, URL do demo: `http://legacy:8081`.
2. Abra **Workflows → Novo workflow**, escolha a aplicação e nomeie o processo.
3. Adicione **Abrir URL**, URL `{{application.url}}`.
4. Adicione ações de preencher/clicar usando os seletores do sistema.
5. Em senhas, marque **Campo sensível** e use `{{password}}`.
6. Clique **Salvar workflow**; depois **Executar teste**.
7. Forneça as variáveis e acompanhe as etapas/logs.

Salvar incrementa uma revisão para controle de concorrência; isso **não** é publicação/rollback
com versões históricas. O MVP executa drafts. Cada execução preserva sua própria cópia.

## Recorder local

O servidor remoto não abre uma janela no seu Windows. Rode o agente no computador em que você
vai interagir com o legado. A mesma pasta extraída pode ser usada no desktop e no servidor.

```bash
pip install -r requirements.lock
pip install --no-deps -e .
playwright install chromium
python -m recorder.agent
```

O painel abre em http://127.0.0.1:8877. Caso não abra automaticamente, acesse esse endereço.

1. No Studio, botão **Abrir Recorder**, ou abra o endereço acima.
2. Informe a URL alcançável pelo **seu desktop**, por exemplo `http://localhost:8081`.
3. Clique **Iniciar gravação** e realize o processo na janela que abrir.
4. Clique **Parar gravação** no painel local e **Exportar JSON**.
5. No designer, use **Importar gravação**.
6. Revise variáveis e seletores; troque a URL inicial por `{{application.url}}`.
7. Salve e teste. O endereço visto pelo worker Docker pode diferir do endereço do desktop.

Preenchimentos viram variáveis pelo `name`/`id` do campo; a senha digitada não atravessa o binding.
O gravador junta preenchimentos consecutivos do mesmo campo, ignora cliques redundantes em inputs,
e prioriza testid, id, name, role, label, placeholder, text e CSS. Registra Enter/Tab/Escape;
hover está disponível no editor, mas não é gravado automaticamente para evitar ruído.
Não grava iframes, múltiplas abas, navegação digitada depois da URL inicial ou coordenadas.
Limite: 200 ações. Revisão e reordenação acontecem no designer após a importação.

## Operação local sem Docker

Tenha PostgreSQL e Redis instalados e configure `.env` com seus endereços. Para um laboratório
local, `DATABASE_URL=sqlite:///studio.db` é aceito; não use SQLite para produção distribuída.
Configure `ALLOWED_ORIGINS=["http://127.0.0.1:8081"]` e `ARTIFACT_DIR=artifacts`.

```bash
playwright install chromium firefox
alembic upgrade head
python scripts/bootstrap.py admin
uvicorn backend.app.main:app --host 127.0.0.1 --port 8080 --no-access-log
```

Em outros terminais com a mesma `.env`:

```bash
python -m worker.worker
uvicorn demo.app:app --host 127.0.0.1 --port 8081 --no-access-log
```

`DEMO_PASSWORD` deve estar exportada no ambiente para o servidor demo local. No Docker, o Compose
faz essa configuração. Worker RQ usa processos Unix: no Windows, use Docker/WSL2.
O Recorder, independentemente disso, pode rodar no Windows nativo.

Para ver o navegador em uma execução, cadastre a aplicação com headless desmarcado e use worker
em uma sessão gráfica Linux. Dentro do Docker padrão, mantenha headless ligado. Firefox é instalado
na imagem; Chrome/Edge exigem instalação do canal correspondente no host/imagem.

## Banco e migrações

```bash
alembic upgrade head
alembic current
```

A migração inicial é explícita e versionada. Não há `create_all` no startup da API.
No Compose o serviço `migrate` termina antes de backend e worker iniciarem.
Backup deve incluir PostgreSQL, volume de evidências e a chave Fernet armazenada separadamente.
Rotação de chave com recriptografia é uma evolução planejada.

## Workers e concorrência

```bash
docker compose up -d --scale worker=2
docker compose logs -f worker
```

Cada worker processa um job por vez. A concorrência global acompanha o número de workers.
Limite por aplicação e pools ainda não estão implementados. Se o legado aceita uma única sessão,
use **um worker** nesta fase. Não há reexecução automática de ações de criação após falha.
O cancelamento é cooperativo entre etapas; uma ação já iniciada pode completar antes de parar.

## Destinos permitidos

Edite `ALLOWED_ORIGINS` no `.env`, por exemplo:

```dotenv
ALLOWED_ORIGINS=["https://legacy.company.local","https://login.company.local","https://static.company.local"]
```

Inclua explicitamente as origens do legado, SSO e recursos necessários. A comparação inclui esquema,
host e porta. A lista vazia bloqueia a navegação. Reinicie API/worker após alterar.
Esse controle reduz destinos acidentais; ele não substitui firewall/proxy de saída.

## SailPoint

O MVP **não implementa** endpoints `/api/v1/rpa/accounts` nem callbacks para uma tenant.
O contrato de provisionamento e o mapeamento futuro estão em `docs/SAILPOINT.md`.
Hoje uma integração de laboratório pode autenticar na API do Studio, enviar uma execução com
`correlation_id`/`Idempotency-Key` e consultar seu resultado. Não a configure como provisionamento
SailPoint de produção sem implementar e validar o adaptador da Fase 3.

## Testes

```bash
pip install -e ".[test]"
pytest -q
```

Teste com Chromium real (requer binários instalados):

```bash
RUN_BROWSER_TESTS=1 pytest -q
```

PowerShell: `$env:RUN_BROWSER_TESTS="1"; pytest -q`.

A suíte usa SQLite e fakeredis; exercita serialização e execução RQ em `SimpleWorker`, não equivale
a testar um cluster Redis/PostgreSQL distribuído. Testes de navegador sobem o demo em `127.0.0.1:18081`.

## Troubleshooting

| Sintoma | Verificação |
|---|---|
| Não inicia / variável Compose vazia | Rode `configure.py` e preencha `DEMO_PASSWORD` |
| Login retorna 503 | Redis precisa estar acessível; rate limiting falha de forma fechada |
| Login retorna 429 | Aguarde 60 s; limite de 10 tentativas por IP observado pela API |
| Aplicação rejeitada | URL precisa estar em `ALLOWED_ORIGINS` |
| QUEUED não sai da fila | Verifique worker, Redis e `docker compose logs worker` |
| FAILED / Error antes de etapas | Verifique instalação de browser, sessão gráfica e memória |
| TIMEOUT em seletor | Use seletor único, visível e estável; revise as alternativas |
| Página sem estilos / SSO falha | Permita origens necessárias de recursos e autenticação |
| Save retorna 409 | Recarregue workflow: outra edição já alterou sua revisão |
| Recorder não abre | Inicie `python -m recorder.agent` no desktop |
| Demo mostra User already exists | Use username novo; template de demonstração espera criação nova |
| Screenshot indisponível | Browser pode ter falhado antes de existir página; veja EVIDENCE_UNAVAILABLE |
| Redis caiu entre commit/enqueue | Confira jobs e execuções antes de recriar; outbox/reconciliação é Fase 2 |

## Antes de produção

Leia `docs/SECURITY.md`. Esta entrega não inclui HA, outbox transacional, SSO, permissões por aplicação,
política de retenção, rotação de chaves, vault externo, observabilidade completa nem recuperação
automática de worker perdido. Valide Compose com PostgreSQL/Redis reais, atualize dependências
após revisão de segurança e faça teste de carga/recuperação no ambiente alvo.
