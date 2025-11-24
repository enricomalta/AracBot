# Instalar dependências
pip install -r requirements.txt

# Executar em modo live
python main.py --mode live --duration 24

# Executar backtest
python main.py --mode backtest --backtest-days 30

# Gerar relatório
python main.py --mode report