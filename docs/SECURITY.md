# Segurança, operação e limites

## Implementado

- Senhas de usuários: Argon2id; criação local pelo administrador, sem senha padrão.
- JWT HS256 com chave externa >=32 caracteres, expiração, issuer e audience validados.
- Papel e estado ativo consultados no banco em toda chamada; JWT não é fonte de papel.
- JWT somente em memória do cliente; não é salvo em localStorage nem cookie.
- Não há credencial ambiente autenticando requisições da UI; CSRF por cookie não se aplica à API.
- Recorder usa host/origem loopback fixa, sem CORS, e CSP bloqueia framing.
- Inputs de execução cifrados com Fernet; conteúdo não retornado pela API e apagado ao terminar.
- Logs não recebem valores digitados, corpo de requisição nem mensagem bruta de exceção Playwright.
- Campos de senha identificados por seletor/flag recusam literais. O runtime também verifica type=password.
- Evidências autenticadas, sem static mount do diretório; filename restrito a PNG.
- Screenshots mascaram controles de formulário e elementos com texto que contém valores de entrada.
- Não se salvam HTML bruto, trace, cookies ou network logs nesta fase.
- Ações limitadas a um catálogo; nenhum eval, Python ou JavaScript arbitrário fornecido pelo frontend.
- Novo browser context por execução; service workers bloqueados; allowlist em requisições roteadas.
- RQ com serialização JSON; Redis sem porta pública no Compose.
- Limite de payload, CSP, nosniff, no-referrer, frame denial, no-store e rate limit.
- Nginx limita requisições. Login limitado via Redis; indisponibilidade impede autenticação.

## Limites que precisam ser resolvidos antes de PRD

1. **Ambiente confiável:** RBAC é global, single-tenant. Um developer controla automações com o acesso
   do worker. Adicione autorização por aplicação, segregação de equipes, aprovação e SSO.
2. **Navegador e egress:** allowlist de origem não é sandbox de rede. DNS rebinding, redirects,
   WebSockets e protocolos internos exigem proxy/firewall e controles de rede do ambiente. Não
   dê ao worker acesso irrestrito a serviços internos, metadados de nuvem ou painel de controle.
3. **Segredos:** vault persistente, integração com CyberArk e rotação Fernet ainda não existem.
   A chave fica em `.env`/secret manager do deploy, nunca no repositório. TLS é obrigatório fora de localhost.
   Não inclua segredos em nomes, URLs, labels ou CSS; o validador não pode identificar todo segredo arbitrário.
4. **Evidências:** mascaramento de DOM é melhor esforço. Canvas, imagem, iframe ou conteúdo gerado
   podem conter dados sensíveis. Screenshots acessíveis a usuários da plataforma precisam de ACL por aplicação,
   retenção e eventual ciframento do storage; nesta fase o volume deve ter acesso restrito.
5. **Fila e banco:** não há outbox transacional entre commit SQL e enqueue Redis. Queda abrupta nesse
   intervalo pode deixar QUEUED sem job. Perda do host pode deixar RUNNING sem encerramento.
   Callback RQ cobre falhas observadas pelo worker, mas não equivale a reconciliação distribuída.
   Não reenvie operações mutáveis cegamente; confira o legado antes de reprocessar.
6. **Timeout/cancelamento:** cooperativo por etapa; stop não desfaz ação já enviada. Timeout global
   tenta fechar browser e salvar evidências; RQ tem margem extra de 90 s e pode matar o processo.
7. **Sessões:** não há compartilhamento, nem persistência de autenticação do browser. MFA e CAPTCHA
   não são contornados: trate-os por acesso de serviço suportado, aprovação humana ou redesign do fluxo.
8. **Dependências:** a entrega fixa versões reprodutíveis; revise CVEs, imagens e versão do Chromium
   antes de PRD. O pin Playwright usado nesta validação não é promessa de patch de segurança atual.
9. **Auditoria:** eventos append-only via API, mas administrador do banco pode alterá-los. Não é WORM,
   SIEM, evidência imutável regulatória nem trilha assinada.
10. **Disponibilidade:** sem HA, backups automáticos, retenção, quotas, DLQ operacional ou autoscaling.
    Não há limite de concorrência por aplicação; controle número de workers manualmente.
11. **Proxy/IP:** a API não confia indiscriminadamente em X-Forwarded-For. Atrás do Nginx do Compose,
    IP de auditoria/rate limit pode ser o proxy, compartilhando a cota de login. Configure cadeia de
    proxies confiáveis e política por usuário/IP no ambiente real; não aceite headers livres do cliente.
12. **Demo:** sistema fictício com SQLite e sessões locais, sem objetivo de segurança enterprise.
    É isolado para testes e deve ser removido do deploy PRD.

## Atualização de dependências

Atualize em branch controlada, regenere o lock, instale os browsers correspondentes e rode a suíte
com navegador, validação PostgreSQL/Redis reais, análise de vulnerabilidades e testes do legado.
Mudar Playwright exige instalar seus binários compatíveis. Nunca copie binários de browser de origem desconhecida.

## Operação de dados

Entrada cifrada permanece enquanto job está na fila; exclusão terminal é automática. Saídas, logs,
auditoria e evidências não têm expiração automática. Implemente política corporativa antes de dados reais.
A UI mostra até 500 eventos por execução no MVP; o endpoint permite paginação por ID para exportação.
