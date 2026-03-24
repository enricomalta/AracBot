# utils/helpers.py
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
from typing import Optional
import sys
import io

def setup_logging(level=logging.INFO):
    """Configura logging para a aplicação com suporte a UTF-8"""
    # Configurar o stdout para UTF-8 no Windows
    if sys.platform == 'win32':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
    
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
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