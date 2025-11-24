# data/api_client.py
import requests
import pandas as pd
import time
import logging
from datetime import datetime, timedelta
from config.settings import settings

logger = logging.getLogger(__name__)

class APIClient:
    def __init__(self):
        self.base_url = settings.BINANCE_API_URL
        self.session = requests.Session()
        
    def fetch_klines(self, symbol: str, interval: str, limit: int = 500, 
                    start_time: str = None, end_time: str = None) -> pd.DataFrame:
        """
        Busca dados de klines da Binance API
        """
        try:
            params = {
                'symbol': symbol,
                'interval': interval,
                'limit': limit
            }
            
            if start_time:
                params['startTime'] = self._parse_timestamp(start_time)
            if end_time:
                params['endTime'] = self._parse_timestamp(end_time)
            
            response = self.session.get(self.base_url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            df = self._parse_klines_data(data)
            return df
            
        except Exception as e:
            logger.error(f"Error fetching klines for {symbol}: {e}")
            return None
    
    def _parse_klines_data(self, data: list) -> pd.DataFrame:
        """Parse dos dados de klines para DataFrame"""
        columns = [
            'timestamp', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_asset_volume', 'number_of_trades',
            'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
        ]
        
        df = pd.DataFrame(data, columns=columns)
        
        # Converter tipos
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = df[col].astype(float)
        
        return df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
    
    def _parse_timestamp(self, timestamp_str: str) -> int:
        """Converte string de timestamp para milissegundos"""
        if isinstance(timestamp_str, (int, float)):
            return int(timestamp_str)
        
        dt = pd.to_datetime(timestamp_str)
        return int(dt.timestamp() * 1000)
    
    def fetch_multiple_timeframes(self, symbol: str, timeframes: list = None) -> dict:
        """Busca dados para múltiplos timeframes"""
        if timeframes is None:
            timeframes = settings.TIMEFRAMES
        
        timeframe_data = {}
        for tf in timeframes:
            try:
                data = self.fetch_klines(symbol, tf, limit=100)
                if data is not None:
                    timeframe_data[tf] = data
                time.sleep(0.1)  # Rate limiting
            except Exception as e:
                logger.error(f"Error fetching {tf} data: {e}")
        
        return timeframe_data