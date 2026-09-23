# Contrato planejado para Identity Security Cloud — Fase 3

Este arquivo é uma especificação de integração, não uma confirmação de suporte já implementado.
O adaptador concreto depende das capacidades e limites do conector ISC escolhido e precisa ser
validado na documentação vigente e em tenant DEV. Nenhuma chamada a uma tenant foi feita nesta entrega.

## Entrada normalizada

```json
{
  "operation": "CREATE_ACCOUNT",
  "application": "LegacyHR",
  "correlationId": "SP-938472",
  "identity": {
    "firstname": "Joao",
    "lastname": "Silva",
    "email": "joao.silva@company.com",
    "department": "IT"
  }
}
```

O adaptador resolve aplicação e versão publicada por operação, converte atributos, valida dados
obrigatórios e envia uma execução. Segredos de administrador vêm do vault, não da identidade recebida.

| Endpoint planejado | Operação |
|---|---|
| POST /api/v1/rpa/accounts | CREATE_ACCOUNT |
| PUT /api/v1/rpa/accounts/{id} | UPDATE_ACCOUNT |
| DELETE /api/v1/rpa/accounts/{id} | DELETE_ACCOUNT |
| POST /api/v1/rpa/accounts/{id}/enable | ENABLE_ACCOUNT |
| POST /api/v1/rpa/accounts/{id}/disable | DISABLE_ACCOUNT |
| POST /api/v1/rpa/accounts/{id}/lock | LOCK_ACCOUNT |
| POST /api/v1/rpa/accounts/{id}/unlock | UNLOCK_ACCOUNT |
| POST /api/v1/rpa/accounts/{id}/password | CHANGE_PASSWORD |
| POST /api/v1/rpa/accounts/{id}/entitlements | ADD_ENTITLEMENT |
| DELETE /api/v1/rpa/accounts/{id}/entitlements/{entitlement} | REMOVE_ENTITLEMENT |
| GET /api/v1/rpa/accounts/{id} | READ_ACCOUNT |
| GET /api/v1/rpa/accounts | ACCOUNT_AGGREGATION (snapshot paginado) |
| GET /api/v1/rpa/entitlements | ENTITLEMENT_AGGREGATION (snapshot paginado) |

Não retornar `success:true` quando apenas houve aceite da fila. Estratégia pode ser polling,
callback autenticado ou espera limitada com resultado durável, conforme o conector suportar.
É incorreto assumir que qualquer operação Web Services ISC acompanha automaticamente um 202.

## Resultado final normalizado planejado

```json
{
  "success": true,
  "accountId": "joao.silva",
  "executionId": "UUID_REAL_DA_EXECUCAO",
  "correlationId": "SP-938472"
}
```

## Idempotência e criação

- Chave do pedido evita jobs duplicados no Studio.
- Workflow precisa consultar conta antes de criar; corridas ainda exigem unicidade no legado.
- Conta existente: política explícita `ALREADY_EXISTS` ou UPDATE_ACCOUNT.
- Falha após clicar Save: verifique estado real antes de retry.
- Aggregation deve publicar snapshot consistente; não iniciar scraping novo a cada página do conector.
- Tokens ISC: client credentials no futuro Credential Manager; sem valores reais em `.env.example`.

As variáveis SAILPOINT_* são somente reservas de configuração nesta versão e não são consumidas.
