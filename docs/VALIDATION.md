# Verificação da entrega

Data: 2026-09-21. Versão: 0.1.0.

**24 testes passaram**, incluindo Chromium real. Cinco avisos de depreciação das dependências,
sem falhas na suíte final. Nenhum ambiente corporativo ou tenant SailPoint foi acessado.

| Verificação | Resultado / alcance |
|---|---|
| API/RBAC/autenticação | Login, rate limit, permissões, validação e cabeçalhos passaram |
| Persistência | SQLite real para testes; snapshot, cifra, cancelamento, idempotência e conflito de revisão passaram |
| Fila | RQ com JSONSerializer + fakeredis; SimpleWorker executou jobs reais |
| Engine | Ordem, desabilitação, cancelamento, timeout, fallback e erro sem senha nos logs passaram |
| CREATE_ACCOUNT | Chromium real → servidor demo HTTP → 14 etapas → SUCCESS e accountId john.doe |
| Falha de seletor | Estado TIMEOUT; PNG criado; download sem auth negado e com auth permitido |
| Recorder DOM | Capturou fill/click e converteu senha em referência sem exportar valor digitado |
| Interface | Chromium: login → nova aplicação → workflow → adicionar etapa → salvar → executar → SUCCESS |
| JavaScript | Nenhum pageerror no teste de interface |
| Layout | Dashboard e designer capturados e inspecionados em 1440 px |
| Migração | Alembic upgrade/check/downgrade/upgrade passou em SQLite |
| Análise estática | Ruff sem erros nos módulos Python |
| Compose | YAML parseado; serviços e dependências inspecionados, sem execução Docker neste ambiente |

## Limites da validação

- Não havia Docker, servidor PostgreSQL ou Redis de sistema disponíveis para a topologia completa.
- Testes de persistência não substituem validação da migração em PostgreSQL.
- fakeredis não verifica latência, particionamento, durabilidade AOF, conexão ou failover Redis reais.
- O teste de UI usa o backend real através de transporte TestClient; a tarefa roda em thread separada
  no harness. O teste de provisionamento usa RQ SimpleWorker. O worker em produção é processo RQ distinto.
- Recorder foi validado no binding DOM com Chromium headless; o painel local/headed requer validação
  no desktop do usuário. A implementação abre Chromium headed quando iniciada pelo painel.
- Chrome/Edge/Firefox, desktop Windows, SSO/MFA, legado corporativo e load testing não foram exercitados.
- Captura de screenshot não pode ser garantida se não há página ou o browser já morreu.
- Sem teste de conector/tenant SailPoint; integração permanece especificação de Fase 3.
- Chromium/Playwright instalados para esta suíte são versões fixas do lock; consulte revisão de
  dependências e hardening antes de qualquer uso de produção.

## Reprodução

```bash
pip install -r requirements.lock
pip install --no-deps -e .
playwright install chromium
RUN_BROWSER_TESTS=1 pytest -q
ruff check backend worker recorder demo scripts tests migrations
```

Screenshots de inspeção em `docs/assets`. Esses arquivos mostram dados reais da execução de teste,
sem dados corporativos. `workers_online`/fila aparecem indisponíveis no screenshot de UI porque o
monitoramento da API não foi substituído pelo fake de teste; não foram preenchidos com números fictícios.
