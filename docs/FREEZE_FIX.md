# CORREÇÃO: Bot Travado (Freeze Fix)

## Problema Identificado
O bot estava **travando indefinidamente** durante a coleta de dados. O bot estava esperando 1 hora para fazer a próxima predição, mas não acordava no horário esperado. Isso sugeria que uma requisição HTTP ficava **presa indefinidamente**, causando um deadlock.

### Causa Raiz
- Requisições HTTP com timeout de apenas 10 segundos, mas **sem retry automático**
- Se uma API ficasse lenta/desresponsiva, o bot ficava preso infinitamente
- Não havia proteção contra threads travadas
- Sem detecção de inatividade

## Solução Implementada

### 1. **Request Helper com Retry Automático** (`utils/request_helper.py`)
- Classe `RobustRequestSession` que:
  - ✅ Faz retry automático em caso de falha (up to 3 tentativas)
  - ✅ Exponential backoff entre tentativas (1.5s, 2.25s, 3.375s)
  - ✅ Executa requisições em thread separada com timeout de segurança
  - ✅ Trata timeouts, connection errors e rate limits
  - ✅ Timeout máximo de thread para evitar deadlock (15 segundos)

```python
# Exemplo de uso
session = RobustRequestSession(max_retries=3, timeout=10, thread_timeout=15)
response = session.get_with_timeout(url, params=params, timeout=10)
```

### 2. **Atualização do APIClient** (`data/api_client.py`)
- Usa `RobustRequestSession` em vez de `requests.Session()` simples
- Retry automático em todas as chamadas de klines
- Melhor tratamento de erros

### 3. **Atualização do Market Data Collector** (`data/market_data_collector.py`)
- Usa `RobustRequestSession` para:
  - `fetch_open_interest()` - com timeout de 8s
  - `fetch_funding_rate()` - com timeout de 8s
  - `fetch_order_book_snapshot()` - com timeout de 8s

### 4. **Watchdog para Detectar Travamentos** (`utils/watchdog.py`)
- Monitora inatividade do bot
- Detecta se o bot não termina um ciclo em tempo esperado
- Alerta logs se travamento for detectado

### 5. **Timeout Thread no Main** (`main.py`)
- Coleta de dados em thread separada com timeout de 20 segundos
- Se a coleta demorar mais, usa dados vazios e continua
- Previne travamento do loop principal

## Mudanças de Arquivos

### Arquivos Criados
- `utils/request_helper.py` - Helper para requisições robustas
- `utils/watchdog.py` - Monitoramento de travamentos

### Arquivos Modificados
- `data/api_client.py` - Usa RobustRequestSession
- `data/market_data_collector.py` - Usa RobustRequestSession
- `main.py` - Adiciona timeout thread e watchdog

## Resultados Esperados

✅ **Bot não mais trava em requisições lentas**
- Retry automático = "volta à vida" de APIs temporariamente indisponíveis
- Thread timeout = nunca fica preso esperando resposta

✅ **Detecção de problemas**
- Logs claros de quando coleta falha
- Alertas de possível travamento

✅ **Resiliência**
- Se Open Interest falhar, tenta 3x antes de desistir
- Se tudo falhar, continua com dados vazios

## Próximos Passos (Recomendado)

1. **Implement persistent logging** - Adicionar logs a arquivo (logs/ folder)
   ```python
   # Em utils/helpers.py
   file_handler = logging.FileHandler('logs/bot.log')
   ```

2. **Auto-restart on extended freeze** - Reiniciar bot se travado por >30 min
   ```python
   # Em utils/watchdog.py - já tem estrutura pronta
   ```

3. **Rate limiting entre requisições**
   ```python
   time.sleep(0.5)  # Entre diferentes APIs
   ```

## Teste a Solução

Para testar se o bot aguenta melhor:

```bash
# Rode o bot normalmente
python start_live_bot.ps1

# Observe os logs para:
# [Retry] - Significa que uma API falhou e está tentando novamente
# [Timeout] - Se coleta levar >20s
# Watchdog ticking - Confirmação que monitoramento está ativo
```

## Resumo das Melhorias

| Aspecto | Antes | Depois |
|--------|-------|--------|
| Travamento por API lenta | ❌ Sim, indefinido | ✅ Não (3 tentativas, depois fallback) |
| Retry automático | ❌ Não | ✅ Sim (exponential backoff) |
| Timeout de thread | ❌ Não | ✅ Sim (15s max por requisição) |
| Detecção de freeze | ❌ Não | ✅ Sim (Watchdog) |
| Logs de problemas | ⚠️ Mínimo | ✅ Detalhado |

---

**Data**: 27 de janeiro de 2026
**Versão**: 2.0 (com Anti-Freeze)
