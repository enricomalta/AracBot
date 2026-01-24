# Sistema de Análise de Sentimento de Notícias

## Visão Geral

Sistema de análise de sentimento que coleta notícias sobre Bitcoin de múltiplas fontes e utiliza NLP para determinar o sentimento do mercado (bullish/bearish/neutral). O sentimento é integrado ao processo de decisão de trading para melhorar a taxa de acerto.

## Objetivo

Melhorar a winning rate de **55%** para **60-65%** (meta: 70%) filtrando trades baseados no sentimento do mercado:
- **Bloquear** trades contrários ao sentimento forte
- **Aumentar confiança** em trades alinhados com sentimento positivo
- **Reduzir confiança** em trades com sentimento moderadamente negativo

## Arquitetura

### Componentes

```
news/
├── __init__.py                 # Exporta classes principais
├── news_collector.py           # Coleta de notícias
├── news_sentiment_analyzer.py  # Análise NLP de sentimento
└── news_sentiment_manager.py   # Gerenciamento e decisões
```

### Fluxo de Dados

```
Fontes de Notícias → Collector → Analyzer → Manager → Trading Decision
     ↓                  ↓           ↓          ↓            ↓
Google News RSS    Filtra BTC   NLP Score   Agregação   Buy/Sell/Block
CoinDesk RSS       Deduplica    -1 a +1     Cache       Adjust Confidence
Cointelegraph      Top 50       Label       Database
CryptoPanic API    24-48h
```

## Fontes de Notícias

### 1. Google News RSS
- URL: `https://news.google.com/rss/search?q=bitcoin&hl=en&gl=US&ceid=US:en`
- Vantagem: Agregador de múltiplas fontes
- Limitação: Sem API, parsing de RSS

### 2. CoinDesk RSS
- URL: `https://www.coindesk.com/arc/outboundfeeds/rss/`
- Vantagem: Especializado em crypto, alta qualidade
- Limitação: Menos volume

### 3. Cointelegraph RSS
- URL: `https://cointelegraph.com/rss`
- Vantagem: Foco em crypto, análises técnicas
- Limitação: Viés técnico

### 4. CryptoPanic API (Opcional)
- URL: `https://cryptopanic.com/api/v1/posts/`
- Vantagem: Agregador especializado, sentiment scores
- Limitação: Rate limit, requer API key
- **Status**: Implementado mas opcional (funciona sem API key)

## Análise de Sentimento

### Abordagem Léxica

Usa dicionários de palavras-chave com pesos:

**Palavras Positivas** (50+ termos):
- Alta intensidade: surge, rally, soar, breakout, explosion
- Média intensidade: rise, gain, bullish, growth, adoption
- Baixa intensidade: increase, positive, support, recovery

**Palavras Negativas** (50+ termos):
- Alta intensidade: crash, plunge, collapse, panic, dump
- Média intensidade: drop, fall, bearish, decline, sell-off
- Baixa intensidade: decrease, negative, resistance, concern

**Intensificadores**:
- very: 1.5x
- extremely, massive: 2.0x
- slightly, somewhat: 0.5x

**Negações**:
- not, no, never → inverte sinal

### Fórmula de Score

```python
score = Σ(palavra_peso × intensificador × contexto) / total_palavras
score_normalizado = tanh(score)  # Limita entre -1 e +1
```

### Classificação

| Score Range | Label | Significado |
|-------------|-------|-------------|
| > 0.2 | positive | Mercado bullish |
| -0.2 a 0.2 | neutral | Sem direção clara |
| < -0.2 | negative | Mercado bearish |

## Regras de Decisão

### Sinais de COMPRA (Buy)

| Sentimento | Score | Ação | Ajuste Confiança |
|------------|-------|------|------------------|
| Very Bearish | < -0.4 | **BLOQUEAR** | 0% |
| Moderately Bearish | -0.4 a -0.2 | Permitir | -3% |
| Neutral | -0.2 a 0.2 | Permitir | 0% |
| Bullish | > 0.3 | Permitir | +5% |

### Sinais de VENDA (Sell)

| Sentimento | Score | Ação | Ajuste Confiança |
|------------|-------|------|------------------|
| Very Bullish | > 0.4 | **BLOQUEAR** | 0% |
| Moderately Bullish | 0.2 a 0.4 | Permitir | -3% |
| Neutral | -0.2 a 0.2 | Permitir | 0% |
| Bearish | < -0.3 | Permitir | +5% |

## Integração com Trading Bot

### main.py - Live Monitoring

```python
# Atualiza sentimento a cada 1 hora
if (current_time - last_sentiment_check).seconds >= 3600:
    current_market_sentiment = sentiment_manager.get_current_market_sentiment()

# Antes de executar trade
trade_decision = sentiment_manager.should_trade(
    signal_type='buy',  # ou 'sell'
    current_sentiment=current_market_sentiment
)

if trade_decision['should_trade']:
    adjusted_confidence = confidence + trade_decision['confidence_adjustment']
    execute_trade(signal, adjusted_confidence)
else:
    print(f"Trade blocked: {trade_decision['reason']}")
```

## Banco de Dados

### Tabela: news_sentiment

Armazena sentimento agregado por timestamp:

```sql
CREATE TABLE news_sentiment (
    id INTEGER PRIMARY KEY,
    timestamp DATETIME,
    score REAL,           -- -1 a 1
    label TEXT,           -- positive/negative/neutral
    confidence REAL,      -- 0 a 1
    news_count INTEGER,
    positive_count INTEGER,
    negative_count INTEGER,
    neutral_count INTEGER,
    created_at DATETIME
)
```

### Tabela: news_articles

Armazena notícias individuais (top 10):

```sql
CREATE TABLE news_articles (
    id INTEGER PRIMARY KEY,
    timestamp DATETIME,
    title TEXT,
    source TEXT,
    sentiment_score REAL,
    sentiment_label TEXT,
    url TEXT,
    created_at DATETIME
)
```

## Performance e Otimizações

### Cache
- **Duração**: 30 minutos
- **Objetivo**: Reduzir chamadas às APIs/RSS feeds
- **Invalidação**: Automática após timeout

### Rate Limiting
- Google News RSS: Sem limite oficial
- CoinDesk/Cointelegraph: ~1 req/min recomendado
- CryptoPanic: 100 req/dia (free tier)

### Recency Weighting
Notícias mais recentes têm mais peso:
```python
weight = e^(-idade_em_horas / 48)
```
- Notícia de 1h atrás: peso ~0.98
- Notícia de 24h atrás: peso ~0.61
- Notícia de 48h atrás: peso ~0.37

## Uso

### Teste do Sistema

```bash
python test_sentiment.py
```

Output esperado:
```
📰 Teste 1: Coletando notícias...
✅ Sentimento coletado com sucesso!
Score: 0.35
Label: POSITIVE
Confidence: 0.82
News Count: 42

📊 Teste 2: Testando decisões...
Compra com sentimento atual:
  Should Trade: ✅ SIM
  Confidence Adjustment: +0.041
  Reason: Market sentiment is bullish (score: 0.35)
```

### Integração no Bot

```bash
# Monitoramento ao vivo (24h)
python main.py --live-monitoring --duration 24

# Backtest com sentimento
python main.py --backtest --days 30
```

## Dependências

Adicionar ao `requirements.txt`:
```
feedparser>=6.0.10  # Para parsing de RSS feeds
```

Instalar:
```bash
pip install feedparser
```

## Métricas de Sucesso

### Objetivos

| Métrica | Baseline (Sem Sentimento) | Meta (Com Sentimento) |
|---------|---------------------------|----------------------|
| Winning Rate | 55.04% | 60-65% |
| Trades Bloqueados | 0 | ~15-25% |
| False Positives Evitados | N/A | >70% |
| Sharpe Ratio | 0.11 | >0.20 |

### Validação

1. **Backtest 30 dias**:
   - Executar COM sentimento
   - Executar SEM sentimento (baseline)
   - Comparar winning rates

2. **Análise Qualitativa**:
   - Verificar se trades bloqueados eram realmente ruins
   - Confirmar que sentimento está alinhado com movimento de preço

3. **Live Monitoring 24h**:
   - Validar em tempo real
   - Monitorar falsos positivos
   - Ajustar thresholds se necessário

## Limitações e Próximos Passos

### Limitações Atuais

1. **Análise Léxica**: Simples, não captura sarcasmo ou nuances
2. **Contexto Limitado**: Não considera quem escreveu ou fonte
3. **Lag Temporal**: Notícias podem ter 1-2h de atraso
4. **Sem ML**: Não aprende com acertos/erros

### Melhorias Futuras

1. **Sentiment Transformer** (Etapa 2):
   - Usar BERT/FinBERT para análise mais sofisticada
   - Fine-tune em dataset de notícias de crypto
   - Capturar contexto e sarcasmo

2. **Source Weighting**:
   - Dar mais peso para fontes confiáveis
   - Descontar rumores e FUD

3. **Entity Recognition**:
   - Extrair entidades (pessoas, empresas)
   - Filtrar notícias sobre pessoas vs tecnologia

4. **Sentiment Prediction**:
   - Prever sentimento futuro baseado em padrões históricos
   - Correlacionar sentimento com movimento de preço

5. **Multi-Asset**:
   - Estender para outras cryptos
   - Correlação entre sentimento de BTC e altcoins

## Configuração

### Kill Switch (Ativar/Desativar)

O sistema possui um **kill switch** que permite ativar ou desativar completamente a análise de sentimento via arquivo `.env`:

```bash
# .env
SENTIMENT_ENABLED=true   # Set to false to disable sentiment analysis
```

Quando desabilitado:
- ✅ Bot funciona normalmente (padrões técnicos + ML)
- ❌ Não coleta notícias
- ❌ Não analisa sentimento
- ❌ Não ajusta confiança baseado em notícias
- ❌ Não bloqueia trades por sentimento

**Quando usar `SENTIMENT_ENABLED=false`:**
- Você quer testar o bot sem influência de notícias
- Fontes de notícias estão indisponíveis
- Você quer comparar performance com/sem sentimento
- Problemas com rate limiting de APIs

### Variáveis de Ambiente (.env)

```bash
# Binance API
BINANCE_API_KEY=your_api_key_here
BINANCE_API_SECRET=your_api_secret_here
USE_BINANCE_DEMO=true

# Sentiment Analysis (KILL SWITCH)
SENTIMENT_ENABLED=true  # Set to false to disable sentiment analysis feature
CRYPTOPANIC_API_KEY=  # Optional: API key for CryptoPanic (leave empty to skip)
```

### settings.py

Configurações carregadas automaticamente:
```python
# Sentiment Analysis (KILL SWITCH)
SENTIMENT_ENABLED = os.getenv('SENTIMENT_ENABLED', 'true').lower() == 'true'
CRYPTOPANIC_API_KEY = os.getenv('CRYPTOPANIC_API_KEY', '')
```

## Suporte

Para dúvidas ou issues:
1. Verificar logs: `logs/trading_bot.log`
2. Executar `test_sentiment.py` para diagnóstico
3. Verificar conectividade com fontes de notícias

## Changelog

### v1.0 (Atual)
- ✅ Implementação inicial de coleta de notícias
- ✅ Análise de sentimento léxica
- ✅ Integração com main.py
- ✅ Database para histórico de sentimento
- ✅ Cache de 30 minutos
- ✅ Sistema de decisão de trading
- ✅ **Kill switch** para ativar/desativar via .env

### v1.1 (Planejado)
- ⏳ Sentiment Transformer com BERT
- ⏳ Source weighting
- ⏳ Backtesting comparativo
- ⏳ Dashboard de sentimento
