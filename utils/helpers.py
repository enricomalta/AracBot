# utils/helpers.py
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
from typing import Optional
import sys
import io
import warnings
import os

def setup_logging(level=logging.INFO):
    """Configura logging para a aplicação com suporte a UTF-8"""
    # Configurar o stdout para UTF-8 no Windows
    if sys.platform == 'win32':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
    
    # INFO+ usa formato limpo; DEBUG usa formato detalhado para troubleshooting.
    if level <= logging.DEBUG:
        log_format = '%(asctime)s,%(msecs)03d - %(name)s - %(levelname)s - %(message)s'
        date_format = '%Y-%m-%d %H:%M:%S'
    else:
        log_format = '%(asctime)s - %(levelname)s - %(message)s'
        date_format = '%Y-%m-%d %H:%M:%S'

    sklearn_parallel_warning = (
        r"`sklearn\.utils\.parallel\.delayed` should be used with "
        r"`sklearn\.utils\.parallel\.Parallel`"
    )

    # Importante: joblib pode criar subprocessos; PYTHONWARNINGS garante herança do filtro.
    existing_pythonwarnings = os.environ.get('PYTHONWARNINGS', '').strip()
    entries = [e for e in existing_pythonwarnings.split(',') if e.strip()] if existing_pythonwarnings else []
    entries = [e for e in entries if 'UserWarning:sklearn.utils.parallel' not in e]

    if level > logging.DEBUG:
        rule = 'ignore::UserWarning:sklearn.utils.parallel'
    else:
        rule = 'default::UserWarning:sklearn.utils.parallel'

    os.environ['PYTHONWARNINGS'] = ','.join([rule] + entries)

    # Filtro local (processo principal)
    warnings.filterwarnings(
        action='default',
        category=UserWarning,
        module=r'sklearn\.utils\.parallel',
        append=False
    )

    # Em INFO (ou acima), ocultar UserWarning do módulo de paralelismo do sklearn.
    if level > logging.DEBUG:
        warnings.filterwarnings(
            action='ignore',
            category=UserWarning,
            module=r'sklearn\.utils\.parallel',
            append=False
        )
    else:
        # Em DEBUG, manter visível apenas este warning específico do delayed/Parallel.
        warnings.filterwarnings(
            action='default',
            message=sklearn_parallel_warning,
            category=UserWarning,
            module=r'sklearn\.utils\.parallel',
            append=False
        )

    logging.basicConfig(
        level=level,
        format=log_format,
        datefmt=date_format,
        handlers=[
            logging.FileHandler('bot_execution.log', mode='a', encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ],
        force=True  # Força reconfiguração
    )

def calculate_volatility(df: pd.DataFrame, window: int = 20) -> float:
    """Calcula volatilidade anualizada"""
    returns = df['close'].pct_change().dropna()
    if len(returns) < 2:
        return 0.0
    return returns.std() * np.sqrt(252)

def normalize_confidence(confidence: float, min_val: float = 0.0, max_val: float = 1.0) -> float:
    """Normaliza valor de confiança para o range [0, 1]"""
    return max(min_val, min(confidence, max_val))

def calculate_holding_period(start_time: datetime, end_time: datetime = None) -> float:
    """Calcula período de hold em minutos"""
    if end_time is None:
        end_time = datetime.now()
    return (end_time - start_time).total_seconds() / 60

def generate_trade_id() -> str:
    """Gera ID único para trade"""
    return f"TRADE_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"

def format_percentage(value: float) -> str:
    """Formata valor como porcentagem"""
    return f"{value:.2f}%"

def format_currency(value: float) -> str:
    """Formata valor como moeda"""
    return f"${value:,.2f}"

def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """Divisão segura evitando divisão por zero"""
    if denominator == 0:
        return default
    return numerator / denominator