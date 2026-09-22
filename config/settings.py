# config/settings.py
import os
from datetime import timedelta
from dotenv import load_dotenv

# Load environment variables from .env.local file
load_dotenv()

class Settings:
    # Base do projeto (diretório pai de config/)
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # Database: Supabase Postgres. Local SQLite is intentionally not used by
    # the serverless runtime because its filesystem is ephemeral.
    DATABASE_URL = os.getenv('DATABASE_URL', '')
    SUPABASE_URL = os.getenv('SUPABASE_URL', '').rstrip('/')
    SUPABASE_ANON_KEY = os.getenv('SUPABASE_ANON_KEY', '')
    
    # API
    BINANCE_API_URL = "https://api.binance.com/api/v3/klines"
    BINANCE_TRADE_URL = "https://api.binance.com/api/v3"
    BINANCE_DEMO_TRADE_URL = "https://testnet.binance.vision/api/v3"
    SYMBOL = "BTCUSDT"
    TIMEFRAMES = ['1m', '5m', '15m', '1h', '4h']
    
    # API Keys (configure via environment variables)
    API_KEY = os.getenv('BINANCE_API_KEY', '')
    API_SECRET = os.getenv('BINANCE_API_SECRET', '')
    USE_DEMO = os.getenv('USE_BINANCE_DEMO', 'true').lower() == 'true'  # Use demo account by default
    ENABLE_LIVE_TRADING = os.getenv('ENABLE_LIVE_TRADING', 'false').lower() == 'true'

    # Serverless orchestration and security
    PUBLIC_BASE_URL = os.getenv('PUBLIC_BASE_URL', '').rstrip('/')
    CRON_TRIGGER_SECRET = os.getenv('CRON_TRIGGER_SECRET', '')
    QSTASH_TOKEN = os.getenv('QSTASH_TOKEN', '')
    QSTASH_URL = os.getenv('QSTASH_URL', 'https://qstash.upstash.io').rstrip('/')
    QSTASH_CURRENT_SIGNING_KEY = os.getenv('QSTASH_CURRENT_SIGNING_KEY', '')
    QSTASH_NEXT_SIGNING_KEY = os.getenv('QSTASH_NEXT_SIGNING_KEY', '')
    AUTH_COOKIE_NAME = os.getenv('AUTH_COOKIE_NAME', 'sb-access-token')
    CSRF_COOKIE_NAME = os.getenv('CSRF_COOKIE_NAME', 'csrf_token')
    ALERT_WEBHOOK_URL = os.getenv('ALERT_WEBHOOK_URL', '')
    SENTRY_DSN = os.getenv('SENTRY_DSN', '')
    
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
    RETRAIN_WINDOW_DAYS = int(os.getenv('RETRAIN_WINDOW_DAYS', '30'))
    
    # Backtesting
    BACKTEST_INITIAL_CAPITAL = 10000.0
    BACKTEST_START_DATE = "2023-01-01"

    # Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

settings = Settings()
