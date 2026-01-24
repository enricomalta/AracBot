# Instalar dependências
pip install -r requirements.txt

# ⚠️ AVISOS DE SEGURANÇA
- **Nunca use chaves de API reais sem entender os riscos**
- **Comece sempre com conta demo (USE_BINANCE_DEMO=true)**
- **Trading de criptomoedas envolve alto risco de perda financeira**
- **Este bot é experimental e pode ter bugs**
- **Configure stop losses adequados**
- **Monitore o bot constantemente**

# Funcionalidades Implementadas
- ✅ Detecção de padrões gráficos (Head & Shoulders, Double Top/Bottom, etc.)
- ✅ Validação com Machine Learning
- ✅ Risk management com position sizing
- ✅ Stop loss e take profit automáticos
- ✅ Execução de trades reais via Binance API
- ✅ Modo demo para testes seguros
- ✅ Análise de performance e relatórios
- ✅ Cache de dados para eficiência

# Configurar API Keys (para trading real)
# Crie um arquivo .env ou configure variáveis de ambiente:
# BINANCE_API_KEY=your_api_key_here
# BINANCE_API_SECRET=your_api_secret_here
# USE_BINANCE_DEMO=true  # Use true para conta demo, false para real

# Modo Live Trading (executa trades reais)
python main.py --mode live --duration 24

# Modo Live Monitoring (apenas monitora sinais, sem executar trades)
# Configure USE_BINANCE_DEMO=true ou remova as API keys
python main.py --mode live --duration 24

# Paper Trading (simulação realista com dados históricos)
python main.py --mode paper --duration 24

# Executar backtest
python main.py --mode backtest --backtest-days 30

# Gerar relatório
python main.py --mode report

# Retreinar ML com dados coletados
python main.py --mode retrain