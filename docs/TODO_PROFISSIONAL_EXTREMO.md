# TODO Mestre - Evolucao para Nivel Profissional Extremo

Data: 2026-05-30
Versao alvo: v2.x
Escopo: transformar o sistema em plataforma quantitativa de nivel institucional, com foco em robustez, generalizacao, governanca e performance ajustada ao risco.

## 0. Principio norte

Objetivo realista: maximizar retorno ajustado ao risco com consistencia fora da amostra.
Observacao: em mercado financeiro nao existe perfeicao estatistica. O alvo tecnico correto e robustez + estabilidade + controle de risco em multiplos regimes.

## 1. KPIs de nivel profissional (metas)

### Performance
- Sharpe anualizado > 2.0 (paper/live controlado)
- Sortino > 2.8
- Profit Factor > 1.8
- Max Drawdown < 8%
- Calmar > 2.0
- Expectancy por trade > 0.15R

### Qualidade preditiva
- Brier Score melhor que baseline em pelo menos 20%
- Log Loss melhor que baseline em pelo menos 15%
- Calibration Error (ECE) < 0.03
- Hit rate direcional por regime > 58%

### Operacao
- Uptime > 99.5%
- Latencia p95 de ciclo < 5s
- Falhas de coleta por ciclo < 1%
- Divergencia de dados entre fontes < 0.5%

## 2. Backlog estrategico por fases

## Fase A - Fundacao Quant e MLOps (prioridade maxima)

### A1. Dados e qualidade
- [ ] Implementar Data Quality Layer com regras automatizadas:
  - missing, spikes, stale candles, timezone drift, duplicatas, schema drift
- [ ] Criar Data Contracts por fonte (Binance, noticias, funding, OI)
- [ ] Versionar datasets de treino (snapshot imutavel)
- [ ] Criar feature store offline (parquet particionado por simbolo/timeframe/data)
- [ ] Implementar label generation robusta (futuro real, sem leakage)

### A2. Evitar leakage e vieses
- [ ] Revisar todas as features com auditoria de leakage temporal
- [ ] Criar testes automatizados de leakage
- [ ] Garantir split temporal estrito (nunca shuffle em serie temporal)
- [ ] Implementar embargo/purging para eventos proximos

### A3. Pipeline de treino reproduzivel
- [ ] Pipeline unico: ingestao -> features -> labels -> treino -> validacao -> registro
- [ ] Seed fixo + tracking de experimento
- [ ] Registro de modelos (Model Registry com versao, metricas, artefatos)
- [ ] Assinatura de modelo promovido para producao

## Fase B - Modelagem avancada e ensemble institucional

### B1. Modelos base
- [ ] Baselines formais:
  - naive drift
  - momentum simples
  - media movel crossover
- [ ] Modelos tabulares avancados:
  - LightGBM
  - XGBoost
  - CatBoost
- [ ] Modelos de serie temporal:
  - TCN
  - LSTM com regularizacao forte
  - Transformer temporal leve

### B2. Ensemble e meta-model
- [ ] Stacking com meta-learner calibrado
- [ ] Weighting dinamico por regime de mercado
- [ ] Mixture-of-experts com gate por volatilidade/tendencia/liquidez

### B3. Calibracao de probabilidade
- [ ] Platt/Isotonic por regime
- [ ] Monitorar curva de confianca vs acerto
- [ ] Sinal de trade usar probabilidade calibrada, nao score bruto

## Fase C - Validacao profissional

### C1. Walk-forward robusto
- [ ] Walk-forward com janela deslizante (train/valid/test)
- [ ] Nested CV temporal para tuning
- [ ] Relatorio por dobra + media + desvio

### C2. Backtest realista
- [ ] Remover simulacao simplificada de retorno aleatorio
- [ ] Executar replay candle-by-candle com:
  - slippage dinamico
  - comissao real
  - latencia e partial fills
  - spread e book impact
- [ ] Simular regras de risco e capacidade de execucao

### C3. Testes de estresse
- [ ] Stress por eventos extremos (crashes, spikes)
- [ ] Monte Carlo de sequencias de trades
- [ ] Analise de sensibilidade a custos
- [ ] Robustez por subperiodo (bull, bear, lateral)

## Fase D - Risk engine de nivel institucional

### D1. Position sizing inteligente
- [ ] Sizing por volatilidade alvo (target vol)
- [ ] Kelly fracionado com teto dinamico
- [ ] Limites por correlacao e concentracao

### D2. Portfolio/risk overlays
- [ ] Kill switch por drawdown intraday/rolling
- [ ] Limitador de perda por regime
- [ ] Circuit breaker de sinais quando drift detectado
- [ ] Monitor de exposicao agregada e risco de gap

### D3. Execucao
- [ ] Smart order routing (quando aplicavel)
- [ ] Politica maker/taker dinamica
- [ ] Regras de cancel/replace e time-in-force

## Fase E - Deteccao de regime e adaptacao online

- [ ] Classificador de regime (trend, mean-reversion, high vol, low vol)
- [ ] Troca dinamica de estrategia/modelo por regime
- [ ] Reweight online com janela curta + regularizacao
- [ ] Aprendizado incremental controlado (sem contaminar modelo base)

## Fase F - Observabilidade, confiabilidade e governanca

### F1. Observabilidade
- [ ] Dashboard unico (Prometheus/Grafana ou equivalente)
- [ ] SLOs: latencia, erro, acuracia, drift, fill rate
- [ ] Alertas acionaveis com runbook

### F2. Drift e saude do modelo
- [ ] Monitor de drift de features (PSI, KS)
- [ ] Monitor de drift de labels/performance
- [ ] Alerta de recalibracao obrigatoria

### F3. Governanca
- [ ] Checklist de promocao para producao
- [ ] Aprovao por gates (metricas minimas)
- [ ] Registro de decisoes (ADR tecnico)
- [ ] Auditoria completa de previsao e execucao

## 3. TODO tecnico detalhado (curto prazo)

## Sprint 1 (1-2 semanas)
- [ ] Trocar backtest de retorno aleatorio por replay real com candles futuros
- [ ] Implementar validacao walk-forward basica
- [ ] Criar modulo de metrics completo (Sharpe, Sortino, Calmar, turnover, hit-rate por regime)
- [ ] Salvar snapshots de dataset de treino com hash
- [ ] Adicionar testes de leakage temporal

## Sprint 2 (2-3 semanas)
- [ ] Integrar LightGBM + calibracao isotonic
- [ ] Implementar model registry simples em SQLite/arquivo
- [ ] Criar pipeline de treino/retrain end-to-end com configuracao YAML
- [ ] Adicionar monitor de drift de features
- [ ] Definir gates de deploy (promove/rejeita modelo)

## Sprint 3 (2-3 semanas)
- [ ] Stacking ensemble com pesos por regime
- [ ] Risk overlay com kill switch dinamico
- [ ] Simulacao de custos realistas (slippage e spread)
- [ ] Dashboard operacional em tempo real
- [ ] Relatorio institucional diario automatico

## 4. Critrios de aceite por modulo

### Modulo de previsao
- [ ] Superar baseline em 3 janelas walk-forward consecutivas
- [ ] ECE < 0.03 em validacao out-of-sample
- [ ] Sem leakage detectado nos testes automatizados

### Modulo de execucao
- [ ] Divergencia entre preco esperado e executado dentro do limite p95
- [ ] Sem ordens fantasma/duplicadas por 30 dias de paper
- [ ] Reconciliacao 100% entre ordens e banco

### Modulo de risco
- [ ] Drawdown dentro de limites em stress tests
- [ ] Kill switch testado em cenarios simulados
- [ ] Politicas de exposicao aplicadas em 100% dos casos

## 5. Arquitetura alvo (resumo)

- Ingestao em camadas com validacao de qualidade
- Feature store + label store versionados
- Training service com experiment tracking e model registry
- Serving com modelo aprovado + calibracao
- Risk engine independente da camada de sinal
- Execution engine com politicas maker/taker
- Observabilidade central + alertas + auditoria

## 6. Lista de "nao negociar" para nivel extremo

- [ ] Nunca treinar/validar com leakage temporal
- [ ] Nunca promover modelo sem superar baseline out-of-sample
- [ ] Nunca operar sem limites de risco hard
- [ ] Nunca confiar em uma unica metrica de sucesso
- [ ] Nunca mudar logica de producao sem experimento controlado

## 7. Plano de entrega para v1.3.0 (proposto)

- [ ] Backtest realista candle-by-candle (sem retorno sintetico)
- [ ] Walk-forward baseline com relatorio automatizado
- [ ] Retrain real com labels e split temporal
- [ ] Dashboard minimo de performance/risco
- [ ] Gates de deploy de modelo

## 8. Comandos operacionais recomendados (padrao de trabalho)

- [ ] Rodar backtest por janela:
  - python main.py --mode backtest --backtest-days 30
- [ ] Rodar retrain com janela controlada:
  - python main.py --mode retrain --retrain-days 7
- [ ] Rodar live com coleta historica inicial:
  - python main.py --mode live --collect-days 30

## 9. Prioridade objetiva agora

Top 5 para impacto maximo imediato:
- [ ] Backtest realista sem simulacao aleatoria
- [ ] Walk-forward e validacao temporal formal
- [ ] Retrain real com labels e modelo versionado
- [ ] Calibracao de probabilidade
- [ ] Risk overlay com kill switch por drawdown

---

Se este plano for executado com disciplina, seu sistema sai do nivel de prototipo avancado para nivel de engenharia quantitativa profissional, com foco no que realmente importa: performance robusta, risco controlado e repetibilidade em producao.
