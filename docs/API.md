# API da Fase 1

Base `/api/v1`, JSON. OpenAPI gerado em `/openapi.json`, Swagger `/docs`, ReDoc `/redoc`.
Exceto login, página de entrada, assets e `/health`, as rotas exigem `Authorization: Bearer <JWT>`.

| Método / endpoint | Papel | Comportamento |
|---|---|---|
| POST /auth/login | público, limitado | username/password → JWT |
| GET /auth/me | todos | username e papel atual |
| GET /applications | todos | até 500 aplicações |
| POST /applications | ADMIN, DEVELOPER | cria aplicação e valida origem |
| GET /workflows | todos | até 500 workflows |
| GET /workflows/{id} | todos | workflow completo |
| POST /workflows | ADMIN, DEVELOPER | cria draft |
| PUT /workflows/{id} | ADMIN, DEVELOPER | exige revision corrente; conflito 409 |
| POST /workflows/{id}/execute | ADMIN, DEVELOPER, OPERATOR | snapshot + enqueue, retorna 202 |
| GET /executions?limit=50&offset=0 | todos | histórico, limite máximo 200 |
| GET /executions/{id} | todos | status/output/snapshot; omite entrada cifrada |
| GET /executions/{id}/logs?after=0 | todos | até 500 eventos, cursor pelo último ID |
| POST /executions/{id}/cancel | ADMIN, DEVELOPER, OPERATOR | pedido cooperativo; 409 se terminal |
| GET /executions/{id}/artifacts/{file.png} | todos | PNG autenticado |
| GET /dashboard | todos | estatísticas reais |
| GET /audit | ADMIN | últimos 200 eventos administrativos |
| GET /health | público, fora de /api/v1 | banco + Redis; 503 se degradado |
| GET /health/workers | todos, fora de /api/v1 | workers atuais no RQ |
| GET /metrics | ADMIN, fora de /api/v1 | contadores por estado em formato textual |

Não há deleção de aplicações/workflows na Fase 1, evitando apagar referências de execução.
Papéis são atribuídos pelo administrador através de `scripts/bootstrap.py`.

## Cadastro e execução

```json
{
  "name": "Legacy IAM Portal",
  "url": "http://legacy:8081",
  "environment": "DEV",
  "browser": "chromium",
  "headless": true,
  "timeout_ms": 30000
}
```

Workflow:

```json
{
  "name": "Abrir portal",
  "application_id": "UUID_DA_APLICACAO",
  "operation": "CUSTOM",
  "timeout_seconds": 600,
  "steps": [
    {"id":"open","type":"navigate","url":"{{application.url}}"},
    {"id":"username","type":"fill","selectors":[{"kind":"css","value":"#username"}],"value":"{{username}}"}
  ]
}
```

Execução: `POST /api/v1/workflows/{id}/execute`, header `Idempotency-Key: SP-938472`.

```json
{
  "correlation_id": "SP-938472",
  "input": {"username": "joao.silva"}
}
```

Resposta 202 inclui `id`, `status`, `correlation_id`, `snapshot`, `output`.
Consulte `/executions/{id}` até estado terminal. Não há garantia de completion síncrono.
Repetir a mesma chave, workflow e input com o mesmo usuário retorna a execução já criada.
Reutilizar chave com outro pedido ou usuário retorna 409. Idempotência da submissão não substitui
checagem de conta existente no legado; não oferece exactly-once em uma aplicação externa.

## Contrato de Step

Campos comuns: `id`, `type`, `name`, `enabled`, `selectors`, `value`, `url`, `output`,
`timeout_ms`, `wait_ms`, `secret`. Campos desconhecidos são recusados.

| Ação | Campos usados |
|---|---|
| navigate | url |
| click / hover | selectors |
| fill | selectors, value, secret |
| select | selectors, value (valor da option) |
| wait | wait_ms (espera fixa) |
| screenshot | id para nome do artefato |
| extract_text | selectors, output (nome da variável e campo de saída) |
| assert_text | selectors, value (conteúdo esperado) |
| check | selectors, value (`false`, `0`, `no` desmarcam) |
| press | selectors, value (`Enter`, `Tab`, atalhos Playwright) |

Exemplo de seletor role: `{"kind":"role","value":"button","name":"Save"}`.
Exemplo de alternativas: `[{"kind":"testid","value":"save"},{"kind":"css","value":"#save"}]`.
Fallback é seleção antes da ação; após uma ação começar, ela não é repetida automaticamente.

## Erros

401 autenticação, 403 papel, 404 inexistente, 409 conflito, 413 payload >1 MB,
422 validação sem eco do input sensível, 429 rate limit, 503 dependência indisponível.
Falhas Playwright aparecem como classe de exceção e contexto da etapa, sem mensagens brutas
que poderiam conter senha. Falha ao enfileirar retorna também execution_id para investigação.
