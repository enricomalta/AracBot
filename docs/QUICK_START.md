# 🚀 Guia Rápido - Bot BTC em Modo LIVE

## Status Atual
✅ **Funcional e Pronto para Usar**

Seu bot foi integrado com sucesso com os seguintes recursos:
- Coleta de dados do mercado (Open Interest, Funding Rate, etc)
- Geração de previsões baseadas em ML
- Análise de sentimento de notícias
- Rastreamento de acurácia de previsões
- Relatórios diários automáticos

## Como Iniciar

### Opção 1: Linha de Comando (Simples)
```bash
cd d:\Dados\Coding\bot_btc
python main.py --mode live --collect-days 30
```

### Opção 2: Script PowerShell (Com Log)
```powershell
cd d:\Dados\Coding\bot_btc
.\start_live_bot.ps1 -Days 30 -Horizon "24h" -Interval 60
```

## Parâmetros

- `--collect-days`: Quantos dias de dados históricos carregar (padrão: 30)
- `--prediction-horizon`: Horizonte das previsões (ex: "24h", "1h", "4h")
- `--update-interval`: Intervalo entre ciclos em minutos (padrão: 60)

## O Que o Bot Faz

A cada ciclo (padrão 1 hora):

1. **Coleta Dados** (5-10 segundos)
   - Open Interest da Binance
   - Taxa de Financiamento
   - Volume e Order Book
   - Dominância de Mercado (BTC)

2. **Análise de Notícias** (5-10 segundos)
   - Google News RSS
   - CoinDesk RSS
   - Cointelegraph RSS
   - Calcula sentimento: Positivo/Neutro/Negativo

3. **Engenharia de Features** (<1 segundo)
   - RSI (14, 21 períodos)
   - MACD
   - Bandas de Bollinger
   - ATR e ADX
   - OBV (On Balance Volume)
   - Volatilidade
   - Retornos

4. **Geração de Previsão** (<1 segundo)
   - Ensemble de 4 sinais (RSI, MACD, Bollinger, Sentimento)
   - Direção: UP / DOWN / SIDEWAYS
   - Preço alvo
   - Confiança da previsão

5. **Armazenamento** 
   - Tudo salvo no banco de dados SQLite
   - Incluindo features, preço atual, dados coletados

6. **Validação (24h depois)**
   - Sistema automaticamente valida se previsão acertou
   - Calcula acurácia por tipo de padrão
   - Gera relatório diário

## Monitorando em Tempo Real

### Ver os últimos logs:
```powershell
Get-Content -Path ".\logs\live_bot_*.log" -Wait
```

### Ver status no banco de dados:
```bash
python main.py --mode report --report-type predictions
```

## Parando o Bot

### Via PowerShell:
```powershell
Get-Process python | Stop-Process -Force
```

### Via Linha de Comando:
```bash
taskkill /F /IM python.exe
```

## Recuperando Dados Históricos

Se o bot for parado e reiniciado:
- Os dados coletados são preservados no banco de dados
- Ao reiniciar com `--collect-days 30`, ele carrega do cache
- Nenhum dado é perdido

## Banco de Dados

Local: `bitcoin_patterns.db`

Principais tabelas:
- `predictions` - Todas as previsões geradas
- `predictions_validation` - Resultados das validações
- `open_interest` - Histórico de OI
- `funding_rates` - Taxa de financiamento histórica
- `order_book_snapshot` - Snapshots do order book
- `news_sentiment` - Sentimento por horário

## Troubleshooting

### Bot não inicia
1. Verifique se Python 3.8+ está instalado: `python --version`
2. Verifique as dependências: `pip list | findstr -E "pandas|talib|scikit"`
3. Verifique o arquivo de log para erros específicos

### Erro de Encoding
✅ Já foi corrigido! Se ainda aparecer, defina:
```powershell
$env:PYTHONIOENCODING="utf-8"
```

### Dados não estão sendo salvos
1. Verifique permissões na pasta do projeto
2. Verifique espaço em disco
3. Verifique se o banco de dados não está corrompido (delete bitcoin_patterns.db e reinicie)

## Próximos Passos

1. **Coletar por 30 dias** para ter histórico sólido
2. **Revisar relatório de acurácia** após os primeiros ciclos
3. **Ajustar parâmetros** baseado na acurácia observada
4. **Considerar modo PAPER** para backtesting antes de LIVE

## Modo Paper (Recomendado Primeiro)

```bash
python main.py --mode paper --backtest-days 30
```

Executa estratégia em dados históricos sem gastar capital real.

---

**Última atualização**: 2026-01-24
**Versão**: 2.0 (Com Previsões ML + Validação Automática)
