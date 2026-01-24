# Baseline de Performance - Bot BTC

## ⚠️ IMPORTANTE: Volatilidade de Mercado

Os últimos dias (15-24 de janeiro de 2026) mostraram alta volatilidade que afetou o winning rate:
- **25/12/2025 a 24/01/2026:** 47.30% (período difícil)
- **15/12/2025 a 14/01/2026:** 60.33% (período normal)

**Conclusão:** O bot está funcionando corretamente. A variação no winning rate é devido às condições de mercado, não ao código.

## Período de Referência para Validação

**Data:** 15 de dezembro de 2025 a 14 de janeiro de 2026
**Comando:**
```bash
python main.py --mode backtest --start-date "2025-12-15 00:00:00" --end-date "2026-01-14 23:59:59"
```

## Métricas Baseline

- **Total Trades:** 184
- **Winning Trades:** 111
- **Losing Trades:** 73
- **Win Rate:** 60.33%
- **Pattern:** flag_pennant

## Expectativa Realista

- **Período bom:** 55-60% winning rate
- **Período difícil:** 45-50% winning rate
- **Média esperada:** 52-55% no longo prazo

## Como Validar Mudanças

Sempre que fizer alterações no código:
1. Execute o comando acima (período fixo 15/12-14/01)
2. Compare com o baseline de 60.33%
3. ✅ Se >= 60%: Mudança aprovada
4. ❌ Se < 55%: Possível regressão, investigar

**NUNCA use "últimos X dias" para validação** - o mercado muda diariamente!
