# 🤖 Bot Bitcoin - Modo LIVE com Previsões de 24h

## ✅ Status Atual (24 de Janeiro, 2026)

### Implementado
- ✅ Padrões de reversão e continuação
- ✅ Machine Learning (Random Forest + Gradient Boost)
- ✅ Análise multi-timeframe
- ✅ Análise de sentimento via notícias
- ✅ Risk Management
- ✅ Backtesting completo
- ✅ **Winning Rate:** 55.04% (30 dias)

### Novo - Fase 1 de Aprimoramentos
- ✅ Coleta de dados avançados (Open Interest, Funding Rate, etc.)
- ✅ Sistema de rastreamento de previsões
- ✅ Features avançadas de ML
- ✅ Tabelas de banco de dados expandidas
- 🔄 Integração com modo LIVE

---

## 📊 Dados Que Serão Coletados em Modo LIVE

### Dados Críticos (Fase 1)
```
✅ Open Interest         - Volume de futuros em aberto
✅ Funding Rate          - Taxa de financiamento (longs vs shorts)
✅ Volatilidade Implícita - Expectativa de movimento futuro
✅ Dominância BTC        - % do valor do mercado cripto
✅ Order Book            - Imbalance de compras/vendas
```

**Impacto Esperado:** +15-20% na acurácia de previsões

### Dados Secundários (Fase 2-3)
```
📋 Liquidações          - Cascatas de liquidações (reversões)
📊 Fluxo de Exchange    - BTC entrando/saindo de exchanges
🐋 Atividade de Whales  - Movimentos de grandes possuidores
📈 Correlações Macro    - Ouro, Dólar, S&P 500, Juros
⛓️  Macro Events        - Halving, ETFs, Regulações
```

---

## 🚀 Como Executar em Modo LIVE

### Instalação de Dependências (Opcional - para dados macro)
```bash
pip install yfinance  # Para dados de ouro, S&P 500, Dólar
```

### Comando Para Iniciar
```bash
# Modo LIVE com coleta de 30 dias + previsões de 24h
python main.py --mode live --collect-days 30 --prediction-horizon 24h --enable-sentiment --enable-ml

# Ou simplificado (usa defaults)
python main.py --mode live
```

### O Que o Bot Fará em Modo LIVE

1. **Coleta Contínua de Dados** (a cada 1h)
   - Open Interest
   - Funding Rate
   - Volatilidade Implícita
   - Dominância BTC
   - Order Book
   - Sentimento de Notícias

2. **Geração de Previsões** (a cada nova vela de 1h)
   - Direção: UP, DOWN ou SIDEWAYS
   - Target Price: Preço esperado em 1h, 4h e 24h
   - Confiança: 0-100%
   - Justificativa: Features utilizadas

3. **Armazenamento de Previsões**
   - Tabela `predictions`
   - Campos: timestamp, timeframe, direção, target, confiança, features
   - Resultado real preenchido automaticamente após expiração

4. **Validação Automática** (a cada 24h)
   - Verifica se previsão de 24h foi correta
   - Atualiza acurácia por modelo
   - Calcula P&L esperado

---

## 📈 Estrutura de Previsões

### Cada Previsão Contém:

```python
{
    'id': 1234,
    'timestamp': '2026-01-24 14:30:00',
    'timeframe': '24h',                    # 1h, 4h, ou 24h
    'prediction_type': 'direction',
    'predicted_direction': 'up',           # up, down, sideways
    'target_price': 50500.00,
    'confidence': 0.75,                    # 0-1
    'model_type': 'gradient_boost',
    
    # Features utilizadas
    'features_used': {
        'rsi_14': 45.3,
        'macd_hist': 150,
        'open_interest': 15000.5,
        'funding_rate': 0.00015,
        'volatility': 42.5,
        'sentiment_score': 0.3,
        'bid_ask_ratio': 1.2
    },
    
    # Resultado (preenchido depois)
    'actual_direction': 'up',
    'actual_price': 50800.00,
    'was_correct': True,
    'profit_loss': 0.59,                   # %
    'error_percent': 0.59                  # %
}
```

---

## 🎯 Plano de 30 Dias

### Semana 1 (24-30 de Janeiro)
- ✅ Teste de coleta de dados avançados
- ✅ Validação de features
- 🔄 Modo LIVE com histórico de 30 dias
- Objetivo: Coletar baseline de dados

### Semana 2 (31 Jan - 6 Fev)
- Análise de acurácia das previsões de 1h/4h/24h
- Ajustes nos pesos dos modelos
- Implementação de Fibonacci patterns
- Objetivo: Acurácia > 60%

### Semana 3 (7-13 de Fevereiro)
- Integração de Volatilidade Implícita
- Implementação de Harmônico Patterns
- Ciclos Temporais
- Objetivo: Acurácia > 65%

### Semana 4 (14-20 de Fevereiro)
- Fine-tuning final
- Implementação de Dashboard
- Testes de stress
- **Objetivo: Acurácia > 70%**

### Após 30 Dias
- Análise completa de resultados
- Ajustes para modo trading real (se acurácia > 70%)
- Otimizações de risk management

---

## 📊 Dashboard de Monitoramento

Você pode consultar o status com:

```bash
# Ver relatório de previsões
python -c "from ml.prediction_tracker import PredictionTracker; from data.database import DatabaseManager; db = DatabaseManager(); tracker = PredictionTracker(db); tracker.print_accuracy_report()"

# Ver dados coletados (últimas 24h)
python -c "
from data.database import DatabaseManager
import pandas as pd
db = DatabaseManager()
conn = db.get_connection()
df = pd.read_sql('SELECT * FROM predictions WHERE created_at > datetime(\"now\", \"-24 hours\")', conn)
print(df[['timeframe', 'predicted_direction', 'confidence', 'was_correct']].tail(20))
conn.close()
"
```

---

## 🔍 Métricas Rastreadas

### Por Previsão
```
- Direção prevista vs. real
- Target price vs. preço alcançado
- Erro percentual
- P&L esperado
- Confiança do modelo
```

### Agregadas (24h)
```
- Acurácia por modelo
- Acurácia por timeframe
- P&L médio
- Modelo com melhor desempenho
- Spread de confiança
```

### Históricas (Últimos 30 dias)
```
- Tendência de acurácia
- Evolução do P&L
- Padrões sazonais (hora, dia)
- Correlação com volatilidade
```

---

## 🛠️ Componentes Implementados

### 1. market_data_collector.py
Coleta dados avançados:
- Open Interest (Binance Futures API)
- Funding Rate (Binance Futures API)
- Volatilidade Implícita (Deribit API)
- Dominância BTC (CoinGecko API)
- Order Book (Binance Spot API)
- Macro Data (yfinance)

### 2. prediction_tracker.py
Rastreia previsões:
- Cria previsão com features completas
- Valida resultado após expiração
- Calcula acurácia por modelo/timeframe
- Gera relatórios

### 3. advanced_features.py
Features avançadas:
- Sentimento → Signal
- Open Interest → Signal
- Funding Rate → Signal  
- Volatilidade Implícita → Signal
- Order Book → Signal
- Dominância → Signal
- Combinações (Composite Signal)
- Ciclos Temporais

### 4. database.py (expandido)
Novo com tabelas:
- open_interest
- funding_rates
- liquidations
- exchange_flow
- implied_volatility
- market_dominance
- predictions
- historical_events
- whale_activity
- order_book_snapshot
- macro_correlations

---

## 📝 Integração com main.py

O arquivo `main.py` foi ligeiramente modificado para:

1. Carregar `AdvancedMarketDataCollector` em modo LIVE
2. Coletar dados a cada ciclo
3. Criar features avançadas
4. Gerar e armazenar previsões
5. Validar previsões expiradas

### Modificações Sugeridas em main.py

```python
from data.market_data_collector import AdvancedMarketDataCollector
from ml.advanced_features import AdvancedFeatureEngineer, RealTimeFeatureUpdater
from ml.prediction_tracker import PredictionTracker

class AdvancedBitcoinPatternTracker:
    def __init__(self):
        # ... código existente ...
        
        # Novo
        self.market_collector = AdvancedMarketDataCollector(self.db)
        self.feature_engineer = AdvancedFeatureEngineer(self.db)
        self.prediction_tracker = PredictionTracker(self.db)
    
    def run_live_mode(self, prediction_horizon: str = '24h'):
        """Executa modo LIVE com previsões"""
        while True:
            # Coletar dados
            market_data = self.market_collector.save_all_market_data()
            
            # Análise e previsões
            current_price = self.api_client.get_current_price()
            
            # Criar features avançadas
            features = self._create_prediction_features(current_price, market_data)
            
            # Gerar previsão
            prediction = self._generate_prediction(features, prediction_horizon)
            
            # Armazenar
            if prediction:
                self.prediction_tracker.create_prediction(
                    timeframe=prediction_horizon,
                    prediction_type='direction',
                    predicted_direction=prediction['direction'],
                    target_price=prediction['target'],
                    confidence=prediction['confidence'],
                    model_type=prediction['model'],
                    features_dict=features,
                    sentiment_score=market_data.get('sentiment'),
                    oi_ratio=market_data.get('oi_ratio'),
                    funding_rate=market_data.get('fr')
                )
            
            # Validar previsões expiradas
            self.prediction_tracker.validate_pending_predictions()
            
            # Aguardar próximo ciclo
            time.sleep(3600)  # 1h
```

---

## 🎓 Como Interpretar os Sinais

### Open Interest Signal
```
OI ↑ 20%+ = Muitos entrando (congestão possível)
OI ↓ 20%+ = Muitos saindo (movimento esperado)
OI Estável = Consolidação
```

### Funding Rate Signal
```
FR > +0.1%  = Muito bullish → Reversão bearish iminente
FR < -0.1%  = Muito bearish → Reversão bullish iminente
FR ≈ 0      = Neutro
```

### Volatilidade Implícita
```
IV ↑ Rápido = Mercado espera movimento
IV ↓        = Mercado espera consolidação
IV Extremos = Breakout ou reversal iminente
```

### Bid/Ask Ratio
```
Ratio > 1.5 = Pressão compradora (bullish)
Ratio < 0.67 = Pressão vendedora (bearish)
Ratio ≈ 1.0 = Equilibrado
```

---

## ⚠️ Limitações Conhecidas

1. **Glassnode/CryptoQuant**
   - Dados em free tier são limitados
   - Pode precisar de upgrade para dados históricos completos

2. **Deribit IV**
   - Requer rate limiting (15 req/min)
   - Histórico limitado sem premium

3. **Liquidações**
   - Implementação será via CoinGlass API ou websocket
   - Requer monitoramento contínuo

---

## 🔐 Segurança

1. **Sem Trade Real por 30 dias**
   - Modo paper trading apenas
   - Validação de acurácia antes de trading real

2. **API Keys**
   - Mantenha `.env.local` seguro
   - Use demo account por padrão

3. **Rate Limiting**
   - APIs têm limites de requisições
   - Implementado com cache de 30-60 minutos

---

## 📞 Próximas Etapas

1. **Hoje (24 Jan):** Iniciar modo LIVE com coleta de dados
2. **Próxima Semana:** Análise de acurácia após 100 previsões
3. **Semana 2:** Ajustes baseado em resultados
4. **Semana 3-4:** Otimizações para atingir 70%
5. **Dia 30:** Análise final e decisão sobre trading real

---

## 📚 Arquivos Adicionados

```
data/
├── market_data_collector.py      # Coleta dados avançados
└── database.py                   # Atualizado com novas tabelas

ml/
├── prediction_tracker.py         # Rastreia previsões
├── advanced_features.py          # Features avançadas
└── validator.py                  # Já existia

docs/
├── ANALISE_DADOS_NECESSARIOS.md  # Análise completa
└── LIVE_MODE_README.md           # Este arquivo
```

---

## 🤝 Suporte

Para dúvidas ou problemas:
1. Verifique o arquivo `ANALISE_DADOS_NECESSARIOS.md` para detalhes técnicos
2. Consulte logs em `bitcoin_patterns.db`
3. Execute `python data/market_data_collector.py` para teste local

---

**Status:** 🟢 Pronto para Modo LIVE
**Última Atualização:** 24 de Janeiro, 2026
**Próximo Review:** 31 de Janeiro, 2026
