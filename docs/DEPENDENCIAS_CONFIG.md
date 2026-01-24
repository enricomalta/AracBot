# 📦 DEPENDÊNCIAS E CONFIGURAÇÃO FINAL

**Última Checklist Antes de Começar**

---

## ✅ Dependências Já Instaladas

Verifique que você tem tudo isto:

```bash
pip list | grep -E 'pandas|numpy|scikit-learn|requests|TA-Lib|feedparser'
```

### Obrigatórias (Já tem)
- ✅ pandas >= 1.5.0
- ✅ numpy >= 1.21.0
- ✅ scikit-learn >= 1.2.0
- ✅ requests >= 2.28.0
- ✅ TA-Lib >= 0.4.24
- ✅ feedparser >= 6.0.10
- ✅ joblib >= 1.2.0
- ✅ scipy >= 1.9.0
- ✅ python-dotenv >= 0.19.0

### Opcionais (Recomendado)
- 🟡 yfinance (para dados macro)

---

## 🔧 Instalação Opcional (yfinance)

Se quiser dados de macro (ouro, S&P 500, dólar):

```bash
pip install yfinance
```

Ou deixar de lado (o bot funciona sem isso).

---

## 🔌 Configuração de API

### Chaves Binance (Opcional - demo por padrão)

Se quiser usar conta real (NÃO RECOMENDADO para testes):

1. Gerar API keys em https://www.binance.com/api
2. Criar arquivo `.env` na pasta do bot:

```bash
cat > .env << EOF
BINANCE_API_KEY=sua_chave_aqui
BINANCE_API_SECRET=seu_secret_aqui
USE_BINANCE_DEMO=false
SENTIMENT_ENABLED=true
EOF
```

**RECOMENDADO:** Deixar `USE_BINANCE_DEMO=true` (padrão)

---

## 📝 Arquivos de Configuração

### config/settings.py
Já está configurado com:
- ✅ Demo account por padrão
- ✅ Symbol: BTCUSDT
- ✅ Timeframes: 1m, 5m, 15m, 1h, 4h
- ✅ Sentiment enabled
- ✅ ML enabled

**Não precisa mexer nada!**

---

## 🎯 Teste Rápido (5 minutos)

### 1. Verificar Imports
```bash
python -c "
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from data.database import DatabaseManager
from data.market_data_collector import AdvancedMarketDataCollector
from ml.prediction_tracker import PredictionTracker
from ml.advanced_features import AdvancedFeatureEngineer
print('✅ Todos os módulos importados com sucesso')
"
```

### 2. Testar Banco de Dados
```bash
python -c "
from data.database import DatabaseManager
db = DatabaseManager()
conn = db.get_connection()
c = conn.cursor()
c.execute('SELECT COUNT(*) FROM sqlite_master WHERE type=\"table\"')
count = c.fetchone()[0]
print(f'✅ Database OK: {count} tabelas')
conn.close()
"
```

### 3. Testar Coleta de Dados
```bash
# Vai coletar dados reais de 5 APIs
python data/market_data_collector.py
```

Se tudo OK → **Pronto para LIVE!**

---

## 🚀 Comando Final

```bash
cd d:\Dados\Coding\bot_btc

# Modo LIVE - deixar rodando 24/7
python main.py --mode live --collect-days 30 --prediction-horizon 24h
```

---

## 🔄 Deixar Rodando Continuamente

### Windows
```batch
# Opção 1: Terminal Keep-Open
start "" python main.py --mode live --collect-days 30

# Opção 2: Task Scheduler (melhor)
# 1. Abrir Task Scheduler
# 2. Create Basic Task
# 3. Trigger: At system startup
# 4. Action: Start program
# 5. Program: C:\Python39\python.exe
# 6. Arguments: main.py --mode live --collect-days 30
# 7. Start in: d:\Dados\Coding\bot_btc
```

### Linux/Mac
```bash
# Opção 1: screen
screen -S bot_live
python main.py --mode live --collect-days 30
# Desconectar: Ctrl+A depois D
# Reconectar: screen -r bot_live

# Opção 2: tmux
tmux new-session -d -s bot_live
tmux send-keys -t bot_live "python main.py --mode live --collect-days 30" Enter

# Opção 3: nohup
nohup python main.py --mode live --collect-days 30 > bot.log 2>&1 &
```

---

## 📊 Monitorar em Tempo Real

### Terminal 1: Bot Rodando
```bash
python main.py --mode live --collect-days 30
# Deixar aberto, vai imprimir logs
```

### Terminal 2: Verificar Status
```bash
# A cada 1 hora, mostrar relatório
watch -n 3600 "python -c \"
from ml.prediction_tracker import PredictionTracker
from data.database import DatabaseManager
db = DatabaseManager()
tracker = PredictionTracker(db)
tracker.print_accuracy_report()
\""
```

### Terminal 3: Ver Dados Brutos
```bash
# SQL interativo
sqlite3 bitcoin_patterns.db

# Dentro do sqlite:
sqlite> SELECT COUNT(*) FROM predictions;
sqlite> SELECT * FROM predictions WHERE created_at > datetime('now', '-24 hours') ORDER BY created_at DESC LIMIT 5;
sqlite> SELECT timeframe, COUNT(*) as total, SUM(CASE WHEN was_correct THEN 1 ELSE 0 END) as correct FROM predictions WHERE was_correct IS NOT NULL GROUP BY timeframe;
```

---

## 📈 Acompanhamento Diário

### Manhã (primeira coisa)
```bash
python -c "
from data.database import DatabaseManager
import sqlite3
db = DatabaseManager()
conn = db.get_connection()
c = conn.cursor()

# Previsões criadas ontem
c.execute('''SELECT COUNT(*) FROM predictions 
             WHERE created_at > datetime('now', '-1 days')''')
print(f'Previsões criadas ontem: {c.fetchone()[0]}')

# Acurácia atualizada
c.execute('''SELECT COUNT(*) as total, 
                    SUM(CASE WHEN was_correct THEN 1 ELSE 0 END) as correct
             FROM predictions WHERE was_correct IS NOT NULL''')
total, correct = c.fetchone()
if total > 0:
    print(f'Acurácia acumulada: {correct}/{total} = {correct/total*100:.1f}%')

conn.close()
"
```

### Relatório Semanal
```bash
python -c "
from ml.prediction_tracker import PredictionTracker
from data.database import DatabaseManager
db = DatabaseManager()
tracker = PredictionTracker(db)

# Relatório completo
print('=== SEMANA ===')
tracker.print_accuracy_report()

# Melhor modelo
best = tracker.get_best_models(1)
if best:
    print(f'\nMelhor modelo: {best[0][\"model_type\"]} com {best[0][\"accuracy\"]:.1f}%')
"
```

---

## 🛠️ Troubleshooting Rápido

### "ModuleNotFoundError: No module named 'yfinance'"
Solução: Ignorar (opcional)
```bash
# Remover linha macro_data do collector.py
# Ou instalar: pip install yfinance
```

### "ConnectionError: api.binance.com"
Solução: Normal, bot tenta novamente em 5min
```bash
# Verifique internet: ping google.com
# Verifique API: curl https://api.binance.com/api/v3/ping
```

### "database is locked"
Solução: Bot rodando em outro terminal
```bash
# Fechar outro bot_live
# Deletar .db-journal se existir
# Reiniciar
```

### "Tabela predictions não existe"
Solução: Deletar banco e deixar recriar
```bash
rm bitcoin_patterns.db
python main.py --mode live  # Vai recriar todas as tabelas
```

---

## 🔒 Segurança

### Proteção de Dados
```bash
# Fazer backup do banco todo dia
cp bitcoin_patterns.db bitcoin_patterns_backup_$(date +%Y%m%d).db

# Manter 30 dias de backup
find . -name "bitcoin_patterns_backup_*.db" -mtime +30 -delete
```

### Proteção de API Keys
```bash
# Nunca commit .env no git
echo ".env" >> .gitignore

# Se usar chaves reais, use demo account primeiro
USE_BINANCE_DEMO=true  # Padrão (seguro)
```

---

## 📊 Capacidade do Sistema

### Espaço em Disco
```
Estimado por mês: 50-100 MB
Por 30 dias: 50-100 MB
Python + dados: < 200 MB total

Mínimo recomendado: 1 GB livre
```

### Memória RAM
```
Uso típico: 200-500 MB
Durante coleta: < 1 GB
Sem problemas em máquinas modernas
```

### Processamento
```
CPU: Mínimo (< 1% durante coleta)
Rede: ~1-2 MB/dia (APIs)
Sem problemas mesmo em VPS cheap
```

---

## ✅ Checklist Final Pré-Execução

Antes de executar `python main.py --mode live`:

- [ ] Python 3.8+ instalado: `python --version`
- [ ] Dependências OK: `pip list | grep pandas`
- [ ] Banco criável: `ls bitcoin_patterns.db` (ok se não existe)
- [ ] Imports OK: `python -c "from data.market_data_collector import..."`
- [ ] Internet OK: `ping api.binance.com`
- [ ] Espaço em disco: `df -h` (> 1 GB)
- [ ] Terminal disponível: 24/7 pode rodar?
- [ ] Documentação lida: INICIO_RAPIDO.md?
- [ ] Testes passaram: `python data/market_data_collector.py`?

**Tudo OK?** ✅ Começar agora!

---

## 🎯 Primeiro Dia - Passo a Passo

```
14:45 - Bot iniciado
└─ Carregando 30 dias de histórico...
└─ Treinando modelos ML...
└─ Pronto!

15:00 - Primeiro ciclo
├─ Coleta dados de 6 fontes
├─ Cria features (30+)
├─ Executa modelos ML
└─ Previsão #1: UP a $50.500 (75% conf) ✅

15:00-15:10 - Deixar rodando
└─ Bot aguardando próxima hora

16:00 - Segundo ciclo
├─ Mesma coisa
└─ Previsão #2: DOWN a $49.800 (60% conf) ✅

... (continua a cada hora)

18:00 - Primeiras Validações
├─ Previsão #1 (1h): Expirou, validar
├─ Previsto: UP, Real: UP ✅ ACERTO
└─ Acurácia 1h: 100% (1/1)

No final do dia:
└─ ~10-20 previsões criadas
└─ ~5-10 previsões validadas
└─ Acurácia: ~50-60% (variável)
└─ Tudo armazenado no DB ✅
```

---

## 🎉 Pronto?

Se passou no checklist acima:

```bash
python main.py --mode live --collect-days 30
```

**E deixar rodando! 🚀**

Monitor no mês seguinte qual a acurácia real.

---

**Versão:** 1.0  
**Data:** 24 de Janeiro, 2026  
**Status:** ✅ Pronto para Execução
