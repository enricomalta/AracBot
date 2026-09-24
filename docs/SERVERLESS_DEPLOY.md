# Deploy serverless: Vercel + Supabase

O bot não mantém mais um processo em espera. O `cron-job.org` chama `POST /api/cron` uma vez por hora com `Authorization: Bearer <CRON_TRIGGER_SECRET>`. A rota responde `202` depois de registrar a mensagem na QStash; a QStash entrega o trabalho à rota `/api/worker`, com retentativas e assinatura verificável.

Isso é intencionalmente diferente de criar uma thread após devolver HTTP: a Vercel pode congelar a função após a resposta, portanto esse padrão perderia análises. A QStash também evita que um retry do cron duplique um mesmo ciclo horário.

## Provisionamento

1. Crie um projeto Supabase e aplique [0001_serverless_bot.sql](../supabase/migrations/0001_serverless_bot.sql) e [0002_model_training_runs.sql](../supabase/migrations/0002_model_training_runs.sql), por `supabase db push` ou pelo SQL Editor.
2. Copie a URL **Transaction pooler** (porta 6543) em `DATABASE_URL`, incluindo `sslmode=require`. Use a mesma variável no ambiente local e na Vercel: treinos locais e monitoramento serverless usam o mesmo banco Supabase. Não use a URL direta `db.<project-ref>.supabase.co`: ela requer IPv6 e pode resultar em `getaddrinfo failed` em redes IPv4.
3. Opcionalmente migre o histórico antes de remover o arquivo local:

   ```powershell
   $env:DATABASE_URL = 'postgresql://...'
   py -3 scripts/migrate_sqlite_to_supabase.py .\bitcoin_patterns.db
   ```

4. Crie uma fila QStash, copie o token e as duas signing keys. Configure `QSTASH_TOKEN`, `QSTASH_CURRENT_SIGNING_KEY`, `QSTASH_NEXT_SIGNING_KEY` e `PUBLIC_BASE_URL` no ambiente Vercel.
5. Configure `CRON_TRIGGER_SECRET` com valor aleatório longo. No cron-job.org use `POST https://SEU_DOMINIO/api/cron`, periodicidade de 1 hora, e o cabeçalho `Authorization: Bearer <segredo>`.
6. Adicione `SENTRY_DSN` e, se desejado, `ALERT_WEBHOOK_URL`. O webhook recebe `purchase_suggestion` e `sale`, além de um `content` compatível com Discord/Slack simples.
7. Faça deploy com `vercel --prod`. O worker tem duração máxima de 300 segundos; escolha um plano Vercel compatível se a coleta ultrapassar o seu limite de execução.

## Compra com aprovação humana

A análise nunca compra. Ela grava uma linha `pending` em `trade_suggestions` e envia o alerta. A interface futura deve obter a sessão do Supabase, colocar o access token em um cookie `HttpOnly; Secure; SameSite=Strict` chamado `sb-access-token` (ou o nome de `AUTH_COOKIE_NAME`) e usar um cookie `csrf_token` separado.

Ao aprovar, a interface deve chamar:

```js
fetch('/api/approve-purchase', {
  method: 'POST',
  credentials: 'include',
  headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrfToken },
  body: JSON.stringify({ suggestion_id: suggestionId })
})
```

A API valida a sessão diretamente no Supabase, compara cookie/header CSRF em tempo constante e reserva a sugestão atomicamente antes de enviar a ordem. `ENABLE_LIVE_TRADING` começa como `false`; só altere para `true` depois de testar as credenciais e regras de mercado da Binance. Com `USE_BINANCE_DEMO=true`, as ordens usam o endpoint Spot Testnet; use credenciais criadas especificamente nele. As posições aprovadas ficam em `positions`; a cada análise horária o algoritmo executa venda automática quando preço atingir stop-loss ou take-profit e envia o webhook com preço e P&L. Antes da venda a posição é reservada como `closing`, impedindo ordens duplicadas por retry; se a Vercel cair depois de a exchange aceitar a ordem, revise essa posição no painel da exchange antes de liberá-la manualmente.

## Treino local e monitoramento serverless

O comando local `python main.py --mode live` executa **um** ciclo de monitoramento, exatamente como o worker da Vercel, e não treina modelos. Para o treino diário, execute:

```powershell
python scripts/training_console.py
```

O console oferece treino por janela de dias, histórico dos últimos treinos no Supabase e deploy opcional. O treino usa candles `BTCUSDT 1h` armazenados/buscados pelo Supabase, grava métricas, período, hashes e data em `model_training_runs`, e só substitui os arquivos ativos depois de validar os dois artefatos. Mantém localmente três versões anteriores em `models/versions/`; essa pasta não entra em Git nem no bundle Vercel.

Os arquivos ativos `ml_models.pkl` e `ml_scalers.pkl` continuam na raiz e são os únicos modelos enviados no deploy. Ao confirmar deploy no console, ele executa `npx vercel --prod --yes`; é preciso que o CLI esteja autenticado e o projeto Vercel esteja vinculado. Vercel também mantém o histórico de deployments para rollback.

## Segurança de dados

As tabelas recebem RLS sem políticas públicas. A futura interface não deve usar o `DATABASE_URL` ou chave de serviço no navegador. Crie views/RPCs com permissões mínimas para os gráficos, ou uma API de leitura que valide a mesma sessão antes de expor somente os campos necessários.
