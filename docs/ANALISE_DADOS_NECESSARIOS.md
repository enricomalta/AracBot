# Análise de Dados e Informações Necessárias para Modo Live com Previsões 24h
**Data:** 24 de Janeiro de 2026  
**Objetivo:** Maximizar informações coletadas para previsões precisas de movimentação do BTC nos próximos 30 dias (iniciando com previsões de 24h)

---

## 1. DADOS JÁ DISPONÍVEIS ✅

### 1.1 Mercado
- ✅ Histórico de preços (BTCUSDT) em múltiplos timeframes (1m, 5m, 15m, 1h, 4h)
- ✅ Dados de volume (base e quote)
- ✅ Dados de trades (número de trades, taker buy volume)
- ✅ Análise técnica: RSI, MACD, Bollinger Bands, ATR, ADX, OBV, Stochastic, Trends
- ✅ Padrões de preço: Double Top/Bottom, Triângulos, Flags/Pennants
- ✅ Elliott Waves (implementado, mas desabilitado atualmente)

### 1.2 Machine Learning
- ✅ Modelos treinados: RandomForest, GradientBoosting, SVM
- ✅ 25+ features técnicas
- ✅ ML Accuracy: 84-86% em reversal/continuation
- ✅ Análise de importância de features

### 1.3 Notícias e Sentimento
- ✅ Coletor de notícias (Google News, CoinDesk, Cointelegraph)
- ✅ Análise de sentimento (Bullish, Bearish, Neutral)
- ✅ Score de sentimento (-1 a +1)
- ✅ Cache de 30 minutos

### 1.4 Armazenamento
- ✅ SQLite com tabelas para:
  - Padrões detectados (com performance histórica)
  - Histórico de preços
  - Métricas de performance
  - Sentimento de notícias

---

## 2. DADOS QUE AINDA FALTAM ❌

### 2.1 Dados de Mercado Avançados (CRÍTICO)

#### Interesse em Aberto (Open Interest)
- **O que é:** Volume de futuros/derivativos em aberto (não liquidados)
- **Por que:** Mostra posições não fechadas, indica força/fraqueza do movimento
- **Como obter:** Binance API (`/fapi/v1/openInterest`)
- **Impacto:** +15-20% na precisão de previsões
- **Armazenar:** Tabela `open_interest` com timestamp, símbolo, valor

#### Funding Rate (Taxas de Financiamento)
- **O que é:** Taxa paga entre traders long/short em contratos perpétuos
- **Por que:** Indica sentimento excessivo (short squeeze ou liquidações)
- **Como obter:** Binance API (`/fapi/v1/fundingRate`)
- **Impacto:** +10-15% na identificação de reversões
- **Armazenar:** Tabela `funding_rates` com histórico de mudanças

#### Liquidações em Tempo Real
- **O que é:** Valores liquidados (longs/shorts)
- **Por que:** Cascata de liquidações sinaliza reversões violentas
- **Como obter:** 
  - Binance Liquidation websocket OR
  - CoinGlass API (free tier) para histórico
- **Impacto:** +8-12% em previsões de curto prazo
- **Armazenar:** Tabela `liquidations` com direção, tamanho, timestamp

#### Dados Agregados de Exchange
- **O que é:** Fluxo de entrada/saída do BTC de exchanges
- **Por que:** Whales movimentando BTC indicam intenções (vender/comprar em massa)
- **Como obter:** 
  - Glassnode API (free tier básico)
  - CryptoQuant (free)
  - Santiment API
- **Impacto:** +12-18% em previsões de 24-72h
- **Armazenar:** Tabela `exchange_flow` com direção, quantidade, exchange, timestamp

#### Volatilidade Implícita (IV) e Opções
- **O que é:** Expectativa de volatilidade futura (mercado de opções)
- **Por que:** Antecede movimentos abruptos
- **Como obter:** 
  - Binance Options API
  - Deribit API (maior mercado de opções)
  - IV-rank histórica
- **Impacto:** +15-20% em detecção de breakouts iminentes
- **Armazenar:** Tabela `implied_volatility` com IV-rank, skew, termo

#### Taxa de Dominância do Bitcoin
- **O que é:** % do BTC do valor total do mercado cripto
- **Por que:** Mostra se mercado está em altcoins (risco ON) ou Bitcoin (risco OFF)
- **Como obter:** CoinGecko API (free)
- **Impacto:** +5-10% contextual para correções de mercado
- **Armazenar:** Tabela `dominance` com BTC%, altcoin%, timestamp

#### Correlações com Ativos Macro
- **O que é:** Correlação com ouro, dólar, S&P 500, taxa de juros
- **Por que:** Ambiente macro afeta comportamento do BTC
- **Como obter:** 
  - Yahoo Finance API (free)
  - Fred API (Federal Reserve, free)
  - Alpha Vantage (free tier)
- **Impacto:** +10-15% em previsões de 30 dias
- **Armazenar:** Tabela `macro_correlations` com índices relacionados

---

### 2.2 Análise de Notícias (APRIMORAMENTO)

#### Análise de Tópicos/Eventos
- **Atual:** Sentimento genérico (-1 a +1)
- **Necessário:** Categorização de notícias
  - Regulação (alto impacto)
  - Adoção institucional (médio impacto)
  - Segurança/hacks (alto impacto negativo)
  - Halvings, upgrades (médio/alto impacto)
  - Economia macro (alto impacto)
  - Concorrência/altcoins (baixo/médio impacto)
- **Impacto:** +8-15% em interpretação de sentimento
- **Implementação:** Adicionar categorias ao `news_sentiment` table

#### Análise de Influência/Fontes
- **O que é:** Diferenciar peso de fontes (CoinDesk vs. blog aleatório)
- **Atualmente:** Todas as notícias têm peso igual
- **Necessário:** Score de autoridade por fonte
- **Impacto:** +5-10% em filtragem de ruído
- **Implementação:** Campo `source_weight` em `news_sentiment`

#### Análise de Eventos Históricos
- **O que é:** Database de eventos passados (halving, ETFs, etc.)
- **Por que:** Padrões comportamentais após eventos similar
- **Impacto:** +10-15% em previsões pré-evento
- **Implementação:** Tabela `historical_events` com data, evento, resultado de preço

---

### 2.3 Features Comportamentais (APRIMORAMENTO)

#### Ciclos Temporais
- **O que é:** Análise de padrões por hora, dia da semana, mês
- **Por que:** BTC tem sazonalidades conhecidas
- **Impacto:** +3-8% em previsões de curto prazo
- **Análise necessária:**
  - Retorno médio por hora do dia (UTC)
  - Volatilidade por dia da semana
  - Efeitos de fim de mês/trimestre
- **Implementação:** Features de `hour`, `day_of_week`, `day_of_month` no ML

#### Análise de Ordens Limitadas
- **O que é:** Detecção de grandes ordens não preenchidas
- **Por que:** Suporte/resistência real (walls)
- **Como obter:** Binance WebSocket depth (`@depth`)
- **Impacto:** +8-12% em breakout/rejection prediction
- **Armazenar:** Tabela `order_book_snapshot` com bids/asks em níveis chave

#### Análise de Whales (Grandes Movimentos)
- **O que é:** Acompanhar endereços com >1000 BTC
- **Por que:** Whales movimentam o mercado
- **Como obter:** Glassnode, Santiment, CryptoQuant
- **Impacto:** +5-12% em detecção de reversões
- **Armazenar:** Tabela `whale_activity` com transações significativas

---

### 2.4 Features de Harmônica/Fractal (APRIMORAMENTO)

#### Fibonacci Retracements/Extensions
- **Atualmente:** Implementado manualmente
- **Necessário:** 
  - Auto-detecção de swings significativos
  - Cálculo automático de níveis
  - Validação de wick patterns nos níveis
- **Impacto:** +5-10% em identificação de reversal points
- **Implementação:** Módulo `fibonacci_analysis` em `patterns/`

#### Harmônico Patterns
- **O que é:** Gartley, Butterfly, Crab, Bat (além de Elliott)
- **Atualmente:** Não implementado
- **Impacto:** +8-15% em reversals
- **Implementação:** Novo módulo `harmonic_patterns.py`

#### Estrutura Fractal
- **O que é:** Mesmos padrões em múltiplos timeframes
- **Atualmente:** Análise multi-timeframe existe mas não é harmônico-orientada
- **Impacto:** +10-15% em confiabilidade
- **Implementação:** Validação cruzada entre timeframes para harmônicos

---

### 2.5 Análise de Correlações Avançadas

#### Análise de Spread
- **Spot vs. Futures:** Diferença de preço entre mercados
- **Diferentes exchanges:** Arbitrage opportunities
- **Impacto:** +3-8% em detecção de dislocações
- **Como obter:** Múltiplas APIs (Binance Spot, Binance Futures, Bybit, etc.)

#### Análise de Volatilidade Histórica (HV) vs. Implícita (IV)
- **O que é:** Comparar volatilidade realizada vs. esperada
- **Por que:** Indica se mercado está sobre/sub-precificando risco
- **Impacto:** +8-12% em decisões de entrada
- **Implementação:** Features `hv_20`, `hv_50`, `iv_rank` no ML

---

### 2.6 Infraestrutura de Armazenamento e Tempo Real

#### Armazenamento de Previsões
- **Necessário:** Tabela `predictions` estruturada para validação posterior
  - Timestamp de criação
  - Timeframe da previsão (1h, 4h, 24h)
  - Tipo de previsão (direction, range, volatility)
  - Confiança/probabilidade
  - Features utilizadas (snapshot)
  - Resultado real (preenchido depois)
  - Erro/Acerto da previsão
- **Uso:** Rastrear precisão de cada modelo/combinação

#### Webhooks/Alertas
- **Atualmente:** Logging apenas
- **Necessário:**
  - Discord/Telegram para alertas críticos (breakouts, reversals iminentes)
  - Email para resumo diário
  - Webhook para integração com otros sistemas

#### Dashboard em Tempo Real
- **Atualmente:** Não existe
- **Necessário:**
  - Visualização de preços + padrões detectados
  - Indicadores em tempo real
  - Histórico de previsões vs. resultados
  - Performance por tipo de padrão
  - Heatmap de sentimento
- **Tech:** Streamlit, Plotly, ou Grafana

---

## 3. PRIORIDADES PARA IMPLEMENTAÇÃO 🎯

### Fase 1 (CRÍTICO - Semana 1)
1. **Open Interest + Funding Rate** → +20-25% na precisão
   - Binance API (free)
   - Tabelas no DB
   - Features para ML
   
2. **Exchange Flow** (entrada/saída de BTC)
   - CryptoQuant/Glassnode (free tier)
   - Detecção de whale activity
   
3. **Tabela `predictions` estruturada**
   - Rastreamento de acertos/erros
   - Validação científica

### Fase 2 (ALTO IMPACTO - Semana 2)
4. **Volatilidade Implícita** (opções)
   - Deribit API
   - IV-rank e skew
   
5. **Harmônico Patterns**
   - Novo módulo de detecção
   - Validação em múltiplos timeframes
   
6. **Análise de Eventos Históricos**
   - Database de eventos passados
   - Pattern matching

### Fase 3 (APRIMORAMENTOS - Semana 3)
7. **Ciclos Temporais**
   - Features de sazonalidade
   - Análise de dia/hora
   
8. **Order Book Analysis**
   - Detecção de walls
   - Rejeições em níveis chave
   
9. **Correlações Macro**
   - Ouro, Dólar, S&P 500, Juros

### Fase 4 (OTIMIZAÇÃO - Semana 4)
10. **Dashboard em Tempo Real**
    - Streamlit app
    - Performance tracking
    
11. **Webhooks e Alertas**
    - Discord, Telegram, Email
    
12. **Re-treinamento automático**
    - Daily model updates
    - Validação de drift

---

## 4. ESTRUTURA DE TABELAS NECESSÁRIAS

```sql
-- Já existem:
-- patterns_detected
-- price_history
-- performance_metrics
-- news_sentiment

-- NOVAS NECESSÁRIAS:

-- Open Interest
CREATE TABLE open_interest (
    id INTEGER PRIMARY KEY,
    timestamp DATETIME,
    symbol TEXT,
    timeframe TEXT,
    oi_long REAL,
    oi_short REAL,
    oi_ratio REAL,
    change_percent REAL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Funding Rate
CREATE TABLE funding_rates (
    id INTEGER PRIMARY KEY,
    timestamp DATETIME,
    symbol TEXT,
    funding_rate REAL,
    mark_price REAL,
    index_price REAL,
    estimated_settle_time INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Liquidações
CREATE TABLE liquidations (
    id INTEGER PRIMARY KEY,
    timestamp DATETIME,
    symbol TEXT,
    side TEXT,  -- 'long' ou 'short'
    price REAL,
    quantity REAL,
    usd_value REAL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Fluxo de Exchange
CREATE TABLE exchange_flow (
    id INTEGER PRIMARY KEY,
    timestamp DATETIME,
    symbol TEXT,
    exchange TEXT,
    direction TEXT,  -- 'in' ou 'out'
    quantity REAL,
    usd_value REAL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Volatilidade Implícita
CREATE TABLE implied_volatility (
    id INTEGER PRIMARY KEY,
    timestamp DATETIME,
    symbol TEXT,
    iv_rank REAL,
    iv_percentile REAL,
    volatility REAL,
    source TEXT,  -- 'deribit', 'binance_options', etc
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Dominância
CREATE TABLE market_dominance (
    id INTEGER PRIMARY KEY,
    timestamp DATETIME,
    btc_dominance REAL,
    eth_dominance REAL,
    altcoin_dominance REAL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Previsões Estruturadas
CREATE TABLE predictions (
    id INTEGER PRIMARY KEY,
    timestamp DATETIME,
    timeframe TEXT,  -- '1h', '4h', '24h'
    prediction_type TEXT,  -- 'direction', 'range', 'volatility'
    predicted_direction TEXT,  -- 'up', 'down', 'sideways'
    target_price REAL,
    confidence REAL,
    model_type TEXT,  -- 'random_forest', 'gradient_boost', 'ensemble'
    features_used TEXT,  -- JSON das features utilizadas
    sentiment_score REAL,
    oi_ratio REAL,
    funding_rate REAL,
    
    -- Resultado (preenchido depois)
    actual_direction TEXT,
    actual_price REAL,
    was_correct BOOLEAN,
    profit_loss REAL,
    error_percent REAL,
    
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    resolved_at DATETIME
);

-- Eventos Históricos
CREATE TABLE historical_events (
    id INTEGER PRIMARY KEY,
    date DATETIME,
    event_name TEXT,
    category TEXT,  -- 'halving', 'etf', 'regulation', 'hack', 'upgrade'
    description TEXT,
    price_before REAL,
    price_1h_after REAL,
    price_24h_after REAL,
    price_7d_after REAL,
    volatility_change REAL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Atividade de Whales
CREATE TABLE whale_activity (
    id INTEGER PRIMARY KEY,
    timestamp DATETIME,
    address TEXT,
    transaction_hash TEXT,
    direction TEXT,  -- 'in' (compra) ou 'out' (venda)
    quantity REAL,
    usd_value REAL,
    from_exchange BOOLEAN,
    to_exchange BOOLEAN,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Order Book Snapshot
CREATE TABLE order_book_snapshot (
    id INTEGER PRIMARY KEY,
    timestamp DATETIME,
    symbol TEXT,
    bid_price REAL,
    bid_size REAL,
    ask_price REAL,
    ask_size REAL,
    bid_ask_ratio REAL,
    total_bid_volume REAL,
    total_ask_volume REAL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Correlações Macro
CREATE TABLE macro_correlations (
    id INTEGER PRIMARY KEY,
    timestamp DATETIME,
    btc_close REAL,
    gold_close REAL,
    sp500_close REAL,
    dxy_close REAL,  -- Dollar Index
    vix_close REAL,
    yield_10y REAL,
    yield_2y REAL,
    correlation_gold REAL,
    correlation_sp500 REAL,
    correlation_dxy REAL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

---

## 5. RECOMENDAÇÕES FINAIS 💡

### Para atingir **70% de acertos em 24h:**

1. **Implementar 3-4 primeiros dados críticos** (Fase 1)
   - Open Interest
   - Funding Rate
   - Exchange Flow
   - Esto deve aumentar acertos para ~60-62%

2. **Adicionar features harmônicas** (Fibonacci + Padrões)
   - Aumentar para ~65-67%

3. **Volatilidade Implícita + Ciclos Temporais**
   - Chegar a ~68-70%

4. **Feedback Loop:**
   - Armazenar todas as previsões em `predictions` table
   - Validar acertos 24h depois
   - Reajustar pesos dos modelos
   - Re-treinar ML diariamente

### Estimativa de Tempo:
- **Fase 1:** 3-4 dias
- **Fase 2:** 3-4 dias
- **Fase 3:** 2-3 dias
- **Validação:** 30 dias de coleta de dados

---

## 6. COMANDO PARA INICIAR O BOT

```bash
# Com histórico de 30 dias + Notícias + ML
python main.py --mode live --collect-days 30 --prediction-horizon 24h --enable-sentiment --enable-ml --storage-mode all

# Ou simplificado:
python main.py --mode live --backtest-days 30
```

**Próximo passo:** Implementar os dados da Fase 1 para começar a coletar informações em paralelo com o modo live.
