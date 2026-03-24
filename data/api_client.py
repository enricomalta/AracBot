# data/api_client.py
import requests
import pandas as pd
import time
import logging
import hmac
import hashlib
from datetime import datetime, timedelta
from urllib.parse import urlencode
from config.settings import settings
from data.database import DatabaseManager
from utils.request_helper import RobustRequestSession

logger = logging.getLogger(__name__)

class APIClient:
    def __init__(self, db_manager):
        self.base_url = settings.BINANCE_API_URL
        self.db = db_manager
        # Usar session robusta com retry automático
        self.session = RobustRequestSession(max_retries=3, timeout=10, thread_timeout=15)
        
    def fetch_klines(self, symbol: str, interval: str, limit: int = 500, 
                    start_time: str = None, end_time: str = None) -> pd.DataFrame:
        """
        Busca dados de klines da Binance API com retry automático
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
            
            # Usar session robusta com retry e timeout
            response = self.session.get_with_timeout(self.base_url, params=params, timeout=10)
            
            if response is None:
                logger.error(f"Failed to fetch klines for {symbol} after retries")
                return None
            
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
    
    def get_historical_data(self, symbol: str, timeframe: str, 
                           start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """
        Busca dados históricos com cache: primeiro verifica banco, senão busca da API
        """
        # Calcular pontos esperados (para 1h)
        expected_points = int((end_date - start_date).total_seconds() / 3600)
        
        # Verificar cache no banco
        cached_data = self.db.get_price_data(symbol, timeframe, start_date, end_date)
        
        if not cached_data.empty and len(cached_data) >= expected_points * 0.9:
            # Usar cache se tiver dados suficientes
            logger.info(f"Using cached data for {symbol} {timeframe} ({len(cached_data)} records)")
            print(f"Using cached data: {len(cached_data)} records")
            return cached_data
        
        # Buscar da API se cache insuficiente
        logger.info(f"Fetching fresh data from API for {symbol} {timeframe}")
        print(f"Fetching fresh data from API")
        df = self.fetch_klines(
            symbol, timeframe, 
            start_time=start_date.isoformat(),
            end_time=end_date.isoformat(),
            limit=1000
        )
        
        if df is not None and not df.empty:
            # Salvar no cache
            self.db.save_price_data(df, symbol, timeframe)
            logger.info(f"Saved {len(df)} records to cache")
            return df
        
        # Retornar cache se API falhar
        if not cached_data.empty:
            logger.warning("API fetch failed, using cached data")
            return cached_data
        
        return None
    
    def _generate_signature(self, params: dict) -> str:
        """Gera assinatura HMAC-SHA256 para requisições autenticadas"""
        query_string = urlencode(params)
        signature = hmac.new(
            settings.API_SECRET.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return signature
    
    def _make_authenticated_request(self, method: str, endpoint: str, params: dict = None) -> dict:
        """Faz requisição autenticada para API de trading"""
        if not settings.API_KEY or not settings.API_SECRET:
            logger.error("API keys not configured")
            return None
        
        if params is None:
            params = {}
        
        # Adicionar timestamp
        params['timestamp'] = int(time.time() * 1000)
        
        # Gerar assinatura
        signature = self._generate_signature(params)
        params['signature'] = signature
        
        headers = {
            'X-MBX-APIKEY': settings.API_KEY
        }
        
        url = f"{settings.BINANCE_TRADE_URL}{endpoint}"
        
        try:
            if method.upper() == 'GET':
                response = self.session.get(url, params=params, headers=headers, timeout=10)
            elif method.upper() == 'POST':
                response = self.session.post(url, params=params, headers=headers, timeout=10)
            else:
                logger.error(f"Unsupported HTTP method: {method}")
                return None
            
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Authenticated request failed: {e}")
            return None
    
    def get_account_balance(self) -> dict:
        """Obtém saldo da conta"""
        return self._make_authenticated_request('GET', '/account')
    
    def place_order(self, symbol: str, side: str, order_type: str, quantity: float, 
                   price: float = None, stop_price: float = None) -> dict:
        """Coloca uma ordem de compra/venda"""
        params = {
            'symbol': symbol,
            'side': side.upper(),
            'type': order_type.upper(),
            'quantity': quantity
        }
        
        if price:
            params['price'] = price
        if stop_price:
            params['stopPrice'] = stop_price
        
        return self._make_authenticated_request('POST', '/order', params)
    
    def get_open_orders(self, symbol: str = None) -> list:
        """Obtém ordens abertas"""
        params = {}
        if symbol:
            params['symbol'] = symbol
        return self._make_authenticated_request('GET', '/openOrders', params)
    
    def cancel_order(self, symbol: str, order_id: int) -> dict:
        """Cancela uma ordem"""
        params = {
            'symbol': symbol,
            'orderId': order_id
        }
        return self._make_authenticated_request('DELETE', '/order', params)