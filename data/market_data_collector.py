# data/market_data_collector.py
"""
Coletor de dados avançados do mercado (Open Interest, Funding Rate, etc.)
Fase 1 de dados críticos para melhorar a precisão de previsões
"""

import requests
import pandas as pd
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, List
import time
from config.settings import settings
from utils.request_helper import RobustRequestSession

logger = logging.getLogger(__name__)

# Suprimir logs verbosos de bibliotecas externas
logging.getLogger("yfinance").setLevel(logging.CRITICAL)
logging.getLogger("urllib3").setLevel(logging.CRITICAL)


class AdvancedMarketDataCollector:
    """Coleta dados avançados: Open Interest, Funding Rate, Liquidações, etc."""
    
    def __init__(self, db_manager):
        self.db = db_manager
        self.binance_fapi_url = "https://fapi.binance.com/fapi/v1"
        self.cryptoquant_url = "https://api.cryptoquant.com/v1"
        # Usar session robusta com retry automático
        self.session = RobustRequestSession(max_retries=3, timeout=8, thread_timeout=12)
    
    # ==================== OPEN INTEREST ====================
    
    def fetch_open_interest(self, symbol: str = "BTCUSDT") -> Optional[Dict]:
        """
        Busca Open Interest atual do mercado de futuros Binance com retry automático
        
        Returns:
            {
                'timestamp': datetime,
                'oi_long': float,
                'oi_short': float,
                'oi_ratio': float,
                'change_percent': float
            }
        """
        try:
            url = f"{self.binance_fapi_url}/openInterest"
            params = {'symbol': symbol}
            
            response = self.session.get_with_timeout(url, params=params, timeout=8)
            if response is None:
                logger.error(f"Failed to fetch Open Interest for {symbol} after retries")
                return None
            
            data = response.json()
            
            oi_current = float(data.get('openInterest', 0))
            timestamp = datetime.fromtimestamp(int(data.get('time', 0)) / 1000)
            
            # Buscar OI anterior para calcular mudança
            oi_previous = self._get_previous_oi(symbol)
            change_percent = 0
            if oi_previous:
                change_percent = ((oi_current - oi_previous) / oi_previous) * 100 if oi_previous > 0 else 0
            
            result = {
                'timestamp': timestamp,
                'symbol': symbol,
                'oi_current': oi_current,
                'change_percent': change_percent,
                'raw_data': data
            }
            
            logger.info(f"OI fetched: {oi_current:.2f}, Change: {change_percent:.2f}%")
            return result
            
        except Exception as e:
            logger.error(f"Error fetching Open Interest: {e}")
            return None
    
    def fetch_open_interest_historical(self, symbol: str = "BTCUSDT", 
                                      period: int = 30) -> Optional[pd.DataFrame]:
        """
        Busca histórico de Open Interest dos últimos N dias
        
        Args:
            symbol: Par de trading (ex: BTCUSDT)
            period: Número de dias no passado
            
        Returns:
            DataFrame com histórico de OI
        """
        try:
            # Binance API não fornece histórico completo de OI direto
            # Alternativa: usar CoinGlass ou salvando snapshots localmente
            logger.info(f"Open Interest historical data (últimos {period} dias) - Salvando snapshots")
            
            # Para agora, retornar None e implementar coleta contínua de snapshots
            # Depois os snapshots serão interpolados
            return None
            
        except Exception as e:
            logger.error(f"Error fetching OI history: {e}")
            return None
    
    def _get_previous_oi(self, symbol: str) -> Optional[float]:
        """Obtém OI anterior do banco de dados"""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT oi_current FROM open_interest 
                WHERE symbol = %s
                ORDER BY timestamp DESC 
                LIMIT 1
            ''', (symbol,))
            result = cursor.fetchone()
            conn.close()
            return result[0] if result else None
        except Exception as e:
            logger.warning(f"Could not fetch previous OI: {e}")
            return None
    
    # ==================== FUNDING RATE ====================
    
    def fetch_funding_rate(self, symbol: str = "BTCUSDT") -> Optional[Dict]:
        """
        Busca a taxa de financiamento atual (Perpetual Contracts) com retry automático
        
        Uma taxa alta positiva indica pressão LONG (bearish a curto prazo)
        Uma taxa alta negativa indica pressão SHORT (bullish a curto prazo)
        
        Returns:
            {
                'timestamp': datetime,
                'funding_rate': float,
                'mark_price': float,
                'index_price': float,
                'time_to_settle': int (ms)
            }
        """
        try:
            url = f"{self.binance_fapi_url}/fundingRate"
            params = {'symbol': symbol, 'limit': 1}
            
            response = self.session.get_with_timeout(url, params=params, timeout=8)
            if response is None:
                logger.error(f"Failed to fetch Funding Rate for {symbol} after retries")
                return None
            
            data = response.json()
            
            if data:
                latest = data[0]
                result = {
                    'timestamp': datetime.fromtimestamp(int(latest['fundingTime']) / 1000),
                    'symbol': symbol,
                    'funding_rate': float(latest['fundingRate']),
                    'mark_price': float(latest.get('fundingRate', 0)),  # Aproximado
                    'raw_data': latest
                }
                
                logger.info(f"Funding Rate: {result['funding_rate']:.4f}% "
                           f"(Timestamp: {result['timestamp']})")
                return result
            
            return None
            
        except Exception as e:
            logger.error(f"Error fetching Funding Rate: {e}")
            return None
    
    def fetch_funding_rate_history(self, symbol: str = "BTCUSDT", 
                                  limit: int = 100) -> Optional[pd.DataFrame]:
        """
        Busca histórico de funding rate (últimas N registros)
        
        Returns:
            DataFrame com histórico
        """
        try:
            url = f"{self.binance_fapi_url}/fundingRate"
            params = {'symbol': symbol, 'limit': min(limit, 1000)}
            
            response = self.session.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            df = pd.DataFrame(data)
            df['fundingTime'] = pd.to_datetime(df['fundingTime'], unit='ms')
            df['fundingRate'] = df['fundingRate'].astype(float)
            
            logger.info(f"Funding Rate history fetched: {len(df)} records")
            return df[['fundingTime', 'fundingRate']]
            
        except Exception as e:
            logger.error(f"Error fetching Funding Rate history: {e}")
            return None
    
    # ==================== LIQUIDAÇÕES ====================
    
    def fetch_recent_liquidations(self, symbol: str = "BTCUSDT", 
                                 limit: int = 100) -> Optional[pd.DataFrame]:
        """
        Busca liquidações recentes usando CoinGlass API (free tier)
        
        Liquidações em cascata indicam reversão violenta iminente
        
        Returns:
            DataFrame com liquidações recentes
        """
        try:
            # CoinGlass API é mais confiável que scraping
            # Free tier: https://www.coinglass.com/
            
            # Alternativa: parsear dados do binance trades se disponível
            logger.info("Liquidations tracking - implementar com CoinGlass API")
            return None
            
        except Exception as e:
            logger.error(f"Error fetching liquidations: {e}")
            return None
    
    # ==================== FLUXO DE EXCHANGE ====================
    
    def fetch_exchange_flow(self, symbol: str = "BTCUSDT") -> Optional[Dict]:
        """
        Busca fluxo de BTC entrando/saindo de exchanges
        
        Usa CryptoQuant API (free tier)
        
        BTC leaving exchange = Bullish (HODLing, não vendendo)
        BTC entering exchange = Bearish (Preparando para vender)
        
        Returns:
            {
                'timestamp': datetime,
                'net_flow': float,
                'inflow': float,
                'outflow': float
            }
        """
        try:
            # CryptoQuant free tier é limitado
            # Implementar com API gratuita de CryptoQuant ou Glassnode
            logger.info("Exchange flow tracking - implementar com CryptoQuant/Glassnode API")
            return None
            
        except Exception as e:
            logger.error(f"Error fetching exchange flow: {e}")
            return None
    
    # ==================== VOLATILIDADE IMPLÍCITA ====================
    
    def fetch_implied_volatility(self, symbol: str = "BTCUSDT") -> Optional[Dict]:
        """
        Busca volatilidade implícita do mercado de opções
        
        Alto IV = Mercado espera volatilidade alta
        Baixo IV = Mercado espera movimento pequeno
        
        Deribit é o maior mercado de opções de BTC
        
        Returns:
            {
                'timestamp': datetime,
                'iv_rank': float (0-100),
                'volatility': float
            }
        """
        try:
            # Deribit API pode ter restrições na free tier
            url = "https://www.deribit.com/api/v2/public/get_volatility_index"
            params = {'currency': 'BTC', 'resolution': '60'}  # 1h resolution
            
            response = self.session.get(url, params=params, timeout=5)
            response.raise_for_status()
            data = response.json()
            
            if data.get('result') and data['result']:
                result = {
                    'timestamp': datetime.now(),
                    'symbol': symbol,
                    'volatility': float(data['result']['data'][-1]['value']) if data['result'].get('data') else None,
                    'raw_data': data['result']
                }
                if result['volatility']:
                    logger.info(f"Implied Volatility: {result['volatility']:.2f}")
                    return result
            
            return None
            
        except Exception as e:
            logger.debug(f"Implied Volatility fetch skipped (API free tier may be limited)")
            return None
    
    # ==================== DOMINÂNCIA DO BITCOIN ====================
    
    def fetch_market_dominance(self) -> Optional[Dict]:
        """
        Busca dominância do Bitcoin no mercado cripto
        
        BTC dominância alta = Mercado conservador (risco OFF)
        BTC dominância baixa = Mercado em altcoins (risco ON)
        
        Returns:
            {
                'timestamp': datetime,
                'btc_dominance': float (0-100),
                'eth_dominance': float,
                'altcoin_dominance': float
            }
        """
        try:
            # CoinGecko é free e confiável
            url = "https://api.coingecko.com/api/v3/global"
            
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            # Verificar se as chaves existem
            data_section = data.get('data', {})
            if 'btc_market_cap_percentage' not in data_section:
                logger.debug(f"Market dominance keys not available (may be API response variation)")
                return None
            
            result = {
                'timestamp': datetime.now(),
                'btc_dominance': float(data_section.get('btc_market_cap_percentage', 0)),
                'eth_dominance': float(data_section.get('eth_market_cap_percentage', 0)),
                'altcoin_dominance': float(100 - data_section.get('btc_market_cap_percentage', 0) - 
                                          data_section.get('eth_market_cap_percentage', 0))
            }
            
            logger.info(f"Market Dominance - BTC: {result['btc_dominance']:.2f}%, "
                       f"ETH: {result['eth_dominance']:.2f}%")
            return result
            
        except Exception as e:
            logger.debug(f"Market Dominance fetch skipped: {str(e)[:50]}")
            return None
    
    # ==================== ORDER BOOK ANALYSIS ====================
    
    def fetch_order_book_snapshot(self, symbol: str = "BTCUSDT", 
                                 limit: int = 20) -> Optional[Dict]:
        """
        Captura snapshot do order book (livro de ordens) com retry automático
        
        Detecta:
        - Paredes (huge orders que suportam/resistem)
        - Imbalance bid/ask (força compradora vs vendedora)
        - Liquidez nos níveis chave
        
        Returns:
            {
                'timestamp': datetime,
                'bid_price': float,
                'bid_size': float,
                'ask_price': float,
                'ask_size': float,
                'bid_ask_ratio': float,
                'spread_percent': float
            }
        """
        try:
            url = f"https://api.binance.com/api/v3/depth"
            params = {'symbol': symbol, 'limit': limit}
            
            response = self.session.get_with_timeout(url, params=params, timeout=8)
            if response is None:
                logger.error(f"Failed to fetch Order Book for {symbol} after retries")
                return None
            
            data = response.json()
            
            bids = data.get('bids', [])
            asks = data.get('asks', [])
            
            if bids and asks:
                bid_price = float(bids[0][0])
                bid_size = float(bids[0][1])
                ask_price = float(asks[0][0])
                ask_size = float(asks[0][1])
                
                spread = ask_price - bid_price
                spread_percent = (spread / bid_price) * 100
                bid_ask_ratio = bid_size / ask_size if ask_size > 0 else 0
                
                # Calcular volume total
                total_bid_volume = sum(float(b[1]) for b in bids)
                total_ask_volume = sum(float(a[1]) for a in asks)
                
                result = {
                    'timestamp': datetime.now(),
                    'symbol': symbol,
                    'bid_price': bid_price,
                    'bid_size': bid_size,
                    'ask_price': ask_price,
                    'ask_size': ask_size,
                    'spread': spread,
                    'spread_percent': spread_percent,
                    'bid_ask_ratio': bid_ask_ratio,
                    'total_bid_volume': total_bid_volume,
                    'total_ask_volume': total_ask_volume
                }
                
                logger.info(f"Order Book - Spread: {spread_percent:.4f}%, "
                           f"Bid/Ask Ratio: {bid_ask_ratio:.2f}")
                return result
            
            return None
            
        except Exception as e:
            logger.error(f"Error fetching Order Book: {e}")
            return None
    
    # ==================== MACRO CORRELATIONS ====================
    
    def fetch_macro_data(self) -> Optional[Dict]:
        """
        Busca dados macro (Ouro, Dólar, S&P 500, Juros)
        
        Usa Yahoo Finance (free) via yfinance
        
        Returns:
            {
                'timestamp': datetime,
                'gold_close': float,
                'sp500_close': float,
                'dxy_close': float (Dollar Index),
                'vix_close': float
            }
        """
        try:
            import yfinance as yf
            import warnings
            warnings.filterwarnings('ignore')
            
            # Símbolos com fallbacks
            symbols = {
                'GC=F': 'gold',       # Gold Futures
                '^GSPC': 'sp500',     # S&P 500
                'DXY=F': 'dxy',       # Dollar Index (pode falhar)
                '^VIX': 'vix'         # VIX
            }
            
            data = {}
            for symbol, name in symbols.items():
                try:
                    # Suprimir output do yfinance
                    import sys
                    from io import StringIO
                    old_stdout = sys.stdout
                    old_stderr = sys.stderr
                    sys.stdout = StringIO()
                    sys.stderr = StringIO()
                    
                    try:
                        ticker = yf.Ticker(symbol)
                        hist = ticker.history(period='1d', progress=False)
                        if not hist.empty and 'Close' in hist.columns:
                            close_price = float(hist['Close'].iloc[-1])
                            if close_price > 0:  # Validar que temos um preço válido
                                data[name] = close_price
                            else:
                                logger.debug(f"Invalid price for {symbol}: {close_price}")
                        else:
                            logger.debug(f"No history data for {symbol}")
                    finally:
                        sys.stdout = old_stdout
                        sys.stderr = old_stderr
                except Exception as e:
                    logger.debug(f"Skipped {symbol}: {str(e)[:50]}")
                    # Continuar sem esse símbolo
            
            if data:
                data['timestamp'] = datetime.now()
                logger.info(f"Macro data fetched: {list(data.keys())}")
                return data
            
            logger.debug("No macro data available")
            return None
            
        except ImportError:
            logger.debug("yfinance not installed (optional)")
            return None
        except Exception as e:
            logger.debug(f"Macro data collection skipped: {str(e)[:50]}")
            return None
    
    # ==================== SALVANDO NO BANCO ====================
    
    def save_all_market_data(self, symbol: str = "BTCUSDT") -> Dict:
        """
        Coleta todos os dados disponíveis e salva no banco
        
        Returns:
            Dicionário com todos os dados coletados
        """
        collected_data = {
            'timestamp': datetime.now(),
            'symbol': symbol,
            'sources': {}
        }
        
        # 1. Open Interest
        oi_data = self.fetch_open_interest(symbol)
        if oi_data:
            collected_data['sources']['open_interest'] = oi_data
            self._save_to_db('open_interest', oi_data)
        
        # 2. Funding Rate
        fr_data = self.fetch_funding_rate(symbol)
        if fr_data:
            collected_data['sources']['funding_rate'] = fr_data
            self._save_to_db('funding_rate', fr_data)
        
        # 3. Order Book (substituindo as fontes opcionais que não funcionam)
        ob_data = self.fetch_order_book_snapshot(symbol)
        if ob_data:
            collected_data['sources']['order_book'] = ob_data
            self._save_to_db('order_book_snapshot', ob_data)
        
        logger.info(f"Saved {len(collected_data['sources'])} data sources")
        return collected_data
    
    def _save_to_db(self, table_name: str, data: Dict):
        """Salva dados no banco de dados"""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            if table_name == 'open_interest':
                cursor.execute('''
                    INSERT INTO open_interest 
                    (timestamp, symbol, oi_current, change_percent, created_at)
                    VALUES (%s, %s, %s, %s, %s)
                ''', (
                    data['timestamp'],
                    data['symbol'],
                    data.get('oi_current'),
                    data.get('change_percent'),
                    datetime.now()
                ))
            
            elif table_name == 'funding_rate':
                cursor.execute('''
                    INSERT INTO funding_rates 
                    (timestamp, symbol, funding_rate, created_at)
                    VALUES (%s, %s, %s, %s)
                ''', (
                    data['timestamp'],
                    data['symbol'],
                    data.get('funding_rate'),
                    datetime.now()
                ))
            
            elif table_name == 'implied_volatility':
                cursor.execute('''
                    INSERT INTO implied_volatility 
                    (timestamp, symbol, volatility, source, created_at)
                    VALUES (%s, %s, %s, %s, %s)
                ''', (
                    data['timestamp'],
                    data.get('symbol', 'BTCUSDT'),
                    data.get('volatility'),
                    'deribit',
                    datetime.now()
                ))
            
            elif table_name == 'dominance':
                cursor.execute('''
                    INSERT INTO market_dominance 
                    (timestamp, btc_dominance, eth_dominance, altcoin_dominance, created_at)
                    VALUES (%s, %s, %s, %s, %s)
                ''', (
                    data['timestamp'],
                    data.get('btc_dominance'),
                    data.get('eth_dominance'),
                    data.get('altcoin_dominance'),
                    datetime.now()
                ))
            
            elif table_name == 'order_book_snapshot':
                cursor.execute('''
                    INSERT INTO order_book_snapshot 
                    (timestamp, symbol, bid_price, bid_size, ask_price, ask_size, 
                     bid_ask_ratio, total_bid_volume, total_ask_volume, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ''', (
                    data['timestamp'],
                    data['symbol'],
                    data.get('bid_price'),
                    data.get('bid_size'),
                    data.get('ask_price'),
                    data.get('ask_size'),
                    data.get('bid_ask_ratio'),
                    data.get('total_bid_volume'),
                    data.get('total_ask_volume'),
                    datetime.now()
                ))
            
            elif table_name == 'macro_data':
                cursor.execute('''
                    INSERT INTO macro_correlations 
                    (timestamp, gold_close, sp500_close, dxy_close, vix_close, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s)
                ''', (
                    data['timestamp'],
                    data.get('gold'),
                    data.get('sp500'),
                    data.get('dxy'),
                    data.get('vix'),
                    datetime.now()
                ))
            
            conn.commit()
            conn.close()
            logger.info(f"Data saved to {table_name}")
            
        except Exception as e:
            logger.error(f"Error saving to {table_name}: {e}")


if __name__ == "__main__":
    # Teste local
    from data.database import DatabaseManager
    
    logging.basicConfig(level=logging.INFO)
    db = DatabaseManager()
    collector = AdvancedMarketDataCollector(db)
    
    print("\n=== Coletando dados avançados do mercado ===\n")
    all_data = collector.save_all_market_data()
    
    print("\nDados coletados:")
    for source, data in all_data['sources'].items():
        if data:
            print(f"✅ {source}: {data}")
        else:
            print(f"❌ {source}: Falhou")
