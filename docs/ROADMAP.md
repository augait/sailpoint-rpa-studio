# Roadmap e critérios de conclusão

| Fase | Entrega | Critério verificável |
|---|---|---|
| 1 — esta versão | API, PostgreSQL, fila, worker, editor sequencial, recorder local, logs e demo | Cadastrar → salvar → enfileirar → navegador executa → resultado/evidência na UI |
| 2 | React/TypeScript/React Flow, IF/ELSE, loops, variáveis tipadas, vault, retry seletivo, cron, versões | Fluxo visual com branches validado; publicação imutável; execução histórica; scheduler sem duplicar |
| 3 | Adaptador ISC e operações IAM | Contratos testados contra tenant DEV; estados assíncronos corretos e idempotência no legado |
| 4 | Agregação, paginação, recorder avançado, pools, SLAs e observabilidade | Agregação completa repetível; concorrência por aplicação; retry sem duplicar dados |
| 5 | HA, SSO, secret managers, approvals, isolamento e DR | Testes de falha/recuperação, ACL, auditoria e testes de carga aprovados |

## Prioridades de engenharia na Fase 2

- Outbox transacional e reconciliador de execuções/worker perdido antes de uso crítico.
- Contrato de grafo, IDs estáveis, edges, validação de ciclos e limites de iteração.
- Modelo workflow_versions com Draft/Published/Archived e rollback auditável.
- Vault persistente e rotação; campos de entrada com schema, tipos e segredo explícito.
- Retry por tipo de ação; ações mutáveis não repetidas automaticamente após resultado incerto.
- Schedules com timezone explícito, cron validado, locking e política de misfire.
- Estado debug com pause/continue/step, transporte autenticado ao desktop e lifecycle definido.

## Não implementado nesta entrega

Canvas React Flow; IF/ELSE/TRY/CATCH; loops/paginação; subworkflow; upload/download; HTTP action/webhook;
JavaScript customizado; proxy configurável por aplicação; vault nomeado; cron/scheduler; publicação/rollback;
callbacks/notificações; integração tenant SailPoint; agregações; trace viewer/network viewer;
replay visual completo; breakpoints; worker pools; limites por aplicação; conta/permissão real em diretório corporativo.

A tela de execução permite consultar etapas e screenshots antigos, mas não é um player de trace.
Os módulos não implementados não aparecem como controles ativos nem como serviços fictícios no Compose.
