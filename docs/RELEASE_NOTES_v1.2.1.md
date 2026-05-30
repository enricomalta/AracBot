# Release Notes - v1.2.1

Data: 2026-05-30

## Resumo

Esta versão corrige a coleta e o consumo de sinais para retrain, melhora a consistência do banco SQLite entre modos de execução e adiciona configuração de janela de treinamento.

## Principais mudanças

### 1. Banco de dados e tabela de sinais

- Garantia de criação da tabela collected_signals no setup inicial do banco.
- Proteção adicional para criação da tabela no fluxo de leitura de sinais.
- Criação de índice único para evitar duplicatas exatas:
  - chaves: timestamp, pattern, signal
- Inserção alterada para INSERT OR IGNORE em collected_signals.

Arquivos:
- data/database.py

### 2. Coleta de sinais no modo live com previsões

- O fluxo run_live_with_predictions passou a executar detecção de padrões por ciclo.
- Sinais detectados agora são persistidos em collected_signals para alimentar retrain.
- Logs adicionados para informar quando houve coleta de sinais no ciclo.

Arquivos:
- main.py

### 3. Coleta de sinais no backtest

- O Backtester passou a receber db_manager opcional.
- Sinais detectados no backtest agora são persistidos em collected_signals.
- main.run_backtest passou a injetar self.db no Backtester.

Arquivos:
- analysis/backtester.py
- main.py

### 4. Janela de treinamento configurável

- Novo argumento CLI para retrain:
  - --retrain-days
- Novo fallback por variável de ambiente:
  - RETRAIN_WINDOW_DAYS (default 30)
- Retrain aplica filtro temporal por timestamp antes do processamento.

Arquivos:
- main.py
- config/settings.py

### 5. Logs de retrain mais úteis

- Removido spam de log linha a linha para todos os sinais.
- Adicionado resumo com:
  - período mínimo e máximo dos sinais
  - contagem por pattern/signal
  - amostra dos últimos 5 sinais

Arquivos:
- main.py

### 6. Documentação atualizada

- README atualizado com:
  - DB_PATH e RETRAIN_WINDOW_DAYS no .env.local
  - exemplo de uso de --retrain-days
  - notas operacionais da versão v1.2.1

Arquivos:
- readme.md

## Compatibilidade

- Compatível com comandos existentes.
- Sem mudanças de API pública fora dos novos parâmetros opcionais.

## Comandos de validação executados

- python main.py --mode retrain
- python main.py --mode retrain --retrain-days 1
- python -c "from main import AdvancedBitcoinPatternTracker; t=AdvancedBitcoinPatternTracker(); t.run_backtest(days=10); import sqlite3; from config.settings import settings; c=sqlite3.connect(settings.DB_PATH); cur=c.cursor(); cur.execute('SELECT COUNT(*) FROM collected_signals'); print('collected_signals:', cur.fetchone()[0]); c.close()"

## Resultado da validação

- Erro de tabela ausente resolvido.
- Retrain passou a encontrar sinais coletados.
- Janela de 1 dia aplicada corretamente no retrain (redução de 62 para 24 sinais no teste).
- Coleta de sinais confirmada no backtest e habilitada no live com previsões.

## Sugestão de mensagem de commit

chore(release): v1.2.1 - fix signal collection and retrain window

- ensure collected_signals table exists in setup/read paths
- add unique index and insert-or-ignore for collected_signals
- collect pattern signals in live-with-predictions cycle
- persist detected signals during backtest
- add retrain-days CLI option and RETRAIN_WINDOW_DAYS env fallback
- improve retrain logs with period/pattern summary
- update README and add release notes
