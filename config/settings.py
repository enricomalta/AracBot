# config/settings.py
import os
from datetime import timedelta
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Settings:
    # Database
    DB_PATH = "bitcoin_patterns.db"
    
    # API
    BINANCE_API_URL = "https://api.binance.com/api/v3/klines"
    BINANCE_TRADE_URL = "https://api.binance.com/api/v3"
    SYMBOL = "BTCUSDT"
    TIMEFRAMES = ['1m', '5m', '15m', '1h', '4h']
    
    # API Keys (configure via environment variables)
    API_KEY = os.getenv('BINANCE_API_KEY', '')
    API_SECRET = os.getenv('BINANCE_API_SECRET', '')
    USE_DEMO = os.getenv('USE_BINANCE_DEMO', 'true').lower() == 'true'  # Use demo account by default
    
    # Sentiment Analysis (KILL SWITCH)
    SENTIMENT_ENABLED = os.getenv('SENTIMENT_ENABLED', 'true').lower() == 'true'
    
    # Trading
    INITIAL_CAPITAL = 10000.0
    MAX_DRAWDOWN = 0.05
    DAILY_LOSS_LIMIT = 0.02
    
    # Pattern Detection
    MIN_CONFIDENCE = 0.72  # Balanceado para qualidade vs quantidade
    ML_CONFIDENCE_WEIGHT = 0.5  # Aumentado para 50% - ML tem mais peso
    
    # Risk Management
    MAX_POSITION_SIZE = 0.1  # 10% do capital
    MAX_PORTFOLIO_RISK = 0.3  # 30% do capital alocado
    
    # Monitoring
    CHECK_INTERVAL = 60  # segundos
    DEFAULT_DURATION_HOURS = 24
    
    # ML Settings
    ML_MODEL_PATH = "ml_models.pkl"
    ML_SCALER_PATH = "ml_scalers.pkl"
    
    # Backtesting
    BACKTEST_INITIAL_CAPITAL = 10000.0
    BACKTEST_START_DATE = "2023-01-01"

settings = Settings()