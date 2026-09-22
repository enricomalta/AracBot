# ml/advanced_features.py
"""
Feature Engineering Avançado
Integra dados de Open Interest, Funding Rate, Volatilidade, Sentimento, etc.
para melhorar as previsões do ML
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)


class AdvancedFeatureEngineer:
    """Cria features avançadas combinando múltiplas fontes de dados"""
    
    def __init__(self, db_manager):
        self.db = db_manager
    
    def create_advanced_features(self, 
                                price_df: pd.DataFrame,
                                sentiment_score: Optional[float] = None,
                                oi_data: Optional[Dict] = None,
                                fr_data: Optional[Dict] = None,
                                iv_data: Optional[Dict] = None,
                                dominance_data: Optional[Dict] = None,
                                order_book_data: Optional[Dict] = None) -> pd.DataFrame:
        """
        Cria features avançadas combinando preço + contexto de mercado
        
        Args:
            price_df: DataFrame com OHLCV
            sentiment_score: Score de sentimento (-1 a 1)
            oi_data: Dados de Open Interest
            fr_data: Dados de Funding Rate
            iv_data: Dados de Volatilidade Implícita
            dominance_data: Dados de Dominância do BTC
            order_book_data: Snapshot do Order Book
            
        Returns:
            DataFrame com features técnicas + avançadas
        """
        features_df = price_df.copy()
        
        # ==================== 1. SENTIMENTO ====================
        
        if sentiment_score is not None:
            features_df['sentiment_score'] = sentiment_score
            features_df['sentiment_signal'] = self._sentiment_to_signal(sentiment_score)
        else:
            features_df['sentiment_score'] = 0.0
            features_df['sentiment_signal'] = 0
        
        # ==================== 2. OPEN INTEREST ====================
        
        if oi_data:
            oi_current = oi_data.get('oi_current', 0)
            oi_change = oi_data.get('change_percent', 0)
            
            features_df['oi_current'] = oi_current
            features_df['oi_change_percent'] = oi_change
            
            # OI aumentando = mais posições abertas
            # OI diminuindo = posições sendo fechadas
            # Alto OI + preço subindo = tendência forte
            # Alto OI + preço caindo = squeeze iminente
            features_df['oi_signal'] = self._oi_to_signal(oi_current, oi_change)
        
        # ==================== 3. FUNDING RATE ====================
        
        if fr_data:
            fr = fr_data.get('funding_rate', 0)
            features_df['funding_rate'] = fr
            
            # Funding rate alto positivo = muito bullish = reversão iminente
            # Funding rate alto negativo = muito bearish = bounce iminente
            # Abs(FR) > 0.1% é extremo
            features_df['fr_extremism'] = abs(fr)
            features_df['fr_direction'] = np.sign(fr)
            features_df['fr_signal'] = self._funding_rate_to_signal(fr)
        
        # ==================== 4. VOLATILIDADE IMPLÍCITA ====================
        
        if iv_data:
            volatility = iv_data.get('volatility', 0)
            features_df['implied_volatility'] = volatility
            
            # IV alto = mercado espera movimento
            # IV baixo = consolidação esperada
            # Comparar com volatilidade histórica para detecção de anomalias
            features_df['iv_signal'] = self._iv_to_signal(volatility)
        
        # ==================== 5. DOMINÂNCIA DO BTC ====================
        
        if dominance_data:
            btc_dom = dominance_data.get('btc_dominance', 50)
            features_df['btc_dominance'] = btc_dom
            
            # BTC dominância alta = Risk OFF (conservador)
            # BTC dominância baixa = Risk ON (agressivo)
            features_df['risk_sentiment'] = self._dominance_to_risk(btc_dom)
        
        # ==================== 6. ORDER BOOK ====================
        
        if order_book_data:
            bid_ask_ratio = order_book_data.get('bid_ask_ratio', 1.0)
            spread_percent = order_book_data.get('spread_percent', 0.01)
            
            features_df['bid_ask_ratio'] = bid_ask_ratio
            features_df['spread_percent'] = spread_percent
            
            # Bid/Ask ratio > 1.0 = mais compras que vendas
            # Spread alto = baixa liquidez = volatilidade possível
            features_df['ob_signal'] = self._orderbook_to_signal(bid_ask_ratio, spread_percent)
        
        # ==================== 7. COMBINAÇÕES AVANÇADAS ====================
        
        features_df = self._create_composite_features(features_df, oi_data, fr_data, iv_data)
        
        # ==================== 8. CICLOS TEMPORAIS ====================
        
        features_df = self._add_temporal_features(features_df)
        
        return features_df
    
    # ==================== SIGNAL CONVERTERS ====================
    
    def _sentiment_to_signal(self, score: float) -> float:
        """Converte sentimento para sinal tradável (-1 a 1)"""
        # score já está em -1 a 1
        return score
    
    def _oi_to_signal(self, oi_current: float, oi_change: float) -> float:
        """
        Converte Open Interest para sinal
        
        OI aumentando + preço subindo = bullish confirmado
        OI diminuindo + preço caindo = bearish confirmado
        OI aumentando + preço caindo = preparação para squeeze
        OI diminuindo + preço subindo = weak rally
        """
        if oi_change > 20:  # OI aumentou muito
            return 0.5 if oi_current > 0 else -0.5
        elif oi_change < -20:  # OI diminuiu muito
            return -0.3 if oi_current > 0 else 0.3
        else:
            return 0.0
    
    def _funding_rate_to_signal(self, fr: float) -> float:
        """
        Funding rate extremo sinaliza reversão iminente
        
        FR > 0.1% = muito bullish = vem reversão bearish
        FR < -0.1% = muito bearish = vem reversão bullish
        """
        if fr > 0.001:  # 0.1%
            return -0.7  # Bearish signal (reversão)
        elif fr < -0.001:
            return 0.7  # Bullish signal
        elif fr > 0.0005:
            return -0.3
        elif fr < -0.0005:
            return 0.3
        else:
            return 0.0
    
    def _iv_to_signal(self, volatility: float) -> float:
        """
        Volatilidade implícita alta = breakout esperado
        Volatilidade implícita baixa = consolidação esperada
        """
        # IV normalmente varia de 30-80
        # Normalizar para -1 a 1
        normalized = (volatility - 50) / 25  # Assume range 25-75
        return np.clip(normalized, -1, 1)
    
    def _dominance_to_risk(self, btc_dom: float) -> float:
        """
        Converte dominância para risco (risk sentiment)
        
        BTC > 45% = Risk OFF (seguro, Bitcoin forte)
        BTC < 40% = Risk ON (altcoins ganhando)
        """
        if btc_dom > 45:
            return 1.0  # Risk OFF
        elif btc_dom < 40:
            return -1.0  # Risk ON
        else:
            return (btc_dom - 40) / 5 - 1  # Interpolação linear
    
    def _orderbook_to_signal(self, bid_ask_ratio: float, spread_percent: float) -> float:
        """
        Order book imbalance sinaliza direção de curto prazo
        
        Bid/Ask > 1.5 = pressão compradora
        Bid/Ask < 0.67 = pressão vendedora
        Spread alto = movimento esperado
        """
        if bid_ask_ratio > 1.5:
            ratio_signal = 0.6
        elif bid_ask_ratio < 0.67:
            ratio_signal = -0.6
        elif bid_ask_ratio > 1.2:
            ratio_signal = 0.3
        elif bid_ask_ratio < 0.8:
            ratio_signal = -0.3
        else:
            ratio_signal = 0.0
        
        # Spread alto pode indicar volatilidade
        spread_signal = 0.1 if spread_percent > 0.05 else 0.0
        
        return ratio_signal + spread_signal * 0.3
    
    # ==================== FEATURES COMPOSTAS ====================
    
    def _create_composite_features(self, df: pd.DataFrame, 
                                   oi_data: Optional[Dict],
                                   fr_data: Optional[Dict],
                                   iv_data: Optional[Dict]) -> pd.DataFrame:
        """Cria features compostas combinando múltiplos sinais"""
        
        # Market Strength Index (combinação de OI, FR, IV)
        signals = []
        
        if 'oi_signal' in df.columns:
            signals.append(df['oi_signal'] * 0.3)
        
        if 'fr_signal' in df.columns:
            signals.append(df['fr_signal'] * 0.3)
        
        if 'iv_signal' in df.columns:
            signals.append(df['iv_signal'] * 0.2)
        
        if 'sentiment_signal' in df.columns:
            signals.append(df['sentiment_signal'] * 0.2)
        
        if signals:
            df['composite_signal'] = sum(signals)
            df['composite_signal'] = df['composite_signal'].rolling(3).mean()  # Smooth
        else:
            df['composite_signal'] = 0.0
        
        # Squeeze Detection (baixo IV + baixo ATR + OI alto)
        if 'iv_signal' in df.columns and 'implied_volatility' in df.columns:
            df['squeeze_probability'] = 0.0
            
            # IV abaixo de 30 = squeeze possível
            if 'implied_volatility' in df.columns:
                low_iv = df['implied_volatility'] < 40
                
                if 'atr' in df.columns:
                    low_atr = df['atr'] < df['atr'].rolling(20).mean() * 0.8
                    df.loc[low_iv & low_atr, 'squeeze_probability'] = 0.7
        
        return df
    
    def _add_temporal_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Adiciona features temporais (hora, dia da semana, etc)"""
        
        if 'timestamp' not in df.columns:
            return df
        
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        # Hora UTC
        df['hour'] = df['timestamp'].dt.hour
        
        # Dia da semana (0=Monday, 6=Sunday)
        df['day_of_week'] = df['timestamp'].dt.dayofweek
        
        # Dia do mês
        df['day_of_month'] = df['timestamp'].dt.day
        
        # Semana do ano
        df['week_of_year'] = df['timestamp'].dt.isocalendar().week
        
        # Hour cyclical (para capturar padrões circulares)
        df['hour_sin'] = np.sin(2 * np.pi * df['hour'] / 24)
        df['hour_cos'] = np.cos(2 * np.pi * df['hour'] / 24)
        
        # Day cyclical
        df['day_sin'] = np.sin(2 * np.pi * df['day_of_week'] / 7)
        df['day_cos'] = np.cos(2 * np.pi * df['day_of_week'] / 7)
        
        return df
    
    # ==================== HISTÓRICO DE FEATURES ====================
    
    def get_historical_features(self,
                               days_back: int = 30) -> pd.DataFrame:
        """
        Recupera histórico de features avançadas do banco
        
        Returns:
            DataFrame com todas as features capturadas
        """
        try:
            conn = self.db.get_connection()
            
            # Combinar dados de múltiplas tabelas
            query = '''
                SELECT 
                    p.timestamp as price_timestamp,
                    p.close,
                    p.volume,
                    oi.oi_current,
                    oi.change_percent as oi_change,
                    fr.funding_rate,
                    iv.volatility as implied_volatility,
                    md.btc_dominance,
                    ob.bid_ask_ratio,
                    ob.spread_percent,
                    ns.score as sentiment_score
                FROM price_history p
                LEFT JOIN open_interest oi ON oi.timestamp BETWEEN p.timestamp - interval '1 hour' AND p.timestamp + interval '1 hour'
                LEFT JOIN funding_rates fr ON fr.timestamp BETWEEN p.timestamp - interval '4 hours' AND p.timestamp + interval '4 hours'
                LEFT JOIN implied_volatility iv ON iv.timestamp BETWEEN p.timestamp - interval '4 hours' AND p.timestamp + interval '4 hours'
                LEFT JOIN market_dominance md ON md.timestamp BETWEEN p.timestamp - interval '1 hour' AND p.timestamp + interval '1 hour'
                LEFT JOIN order_book_snapshot ob ON ob.timestamp BETWEEN p.timestamp - interval '10 minutes' AND p.timestamp + interval '10 minutes'
                LEFT JOIN news_sentiment ns ON ns.timestamp BETWEEN p.timestamp - interval '24 hours' AND p.timestamp + interval '24 hours'
                WHERE p.timestamp > now() + (%s * interval '1 day')
                ORDER BY p.timestamp DESC
            '''
            
            df = pd.read_sql_query(query, conn, params=[-days_back])
            conn.close()
            
            logger.info(f"Loaded {len(df)} historical feature records")
            return df
            
        except Exception as e:
            logger.error(f"Error loading historical features: {e}")
            return pd.DataFrame()
    
    # ==================== VALIDAÇÃO DE FEATURES ====================
    
    def validate_features(self, features_df: pd.DataFrame) -> Dict:
        """
        Valida features para detectar problemas
        
        Returns:
            Dicionário com status de validação
        """
        validation = {
            'total_rows': len(features_df),
            'null_counts': features_df.isnull().sum().to_dict(),
            'infinite_counts': {},
            'out_of_range': {}
        }
        
        # Detectar infinitos
        for col in features_df.columns:
            inf_count = np.isinf(features_df[col]).sum()
            if inf_count > 0:
                validation['infinite_counts'][col] = inf_count
        
        # Validar ranges
        range_checks = {
            'sentiment_score': (-1, 1),
            'funding_rate': (-0.01, 0.01),
            'bid_ask_ratio': (0.1, 10.0),
            'spread_percent': (0, 1.0)
        }
        
        for col, (min_val, max_val) in range_checks.items():
            if col in features_df.columns:
                out_of_range = ((features_df[col] < min_val) | (features_df[col] > max_val)).sum()
                if out_of_range > 0:
                    validation['out_of_range'][col] = out_of_range
        
        validation['is_valid'] = len(validation['infinite_counts']) == 0
        
        return validation


class RealTimeFeatureUpdater:
    """Atualiza features em tempo real para modo live"""
    
    def __init__(self, db_manager, market_data_collector):
        self.db = db_manager
        self.market_collector = market_data_collector
        self.feature_engineer = AdvancedFeatureEngineer(db_manager)
    
    def update_features(self, current_price: float) -> Dict:
        """
        Atualiza todas as features em tempo real
        
        Chamado a cada nova vela ou em intervalo fixo
        
        Returns:
            Dicionário com features atualizadas
        """
        features = {
            'timestamp': datetime.now(),
            'price': current_price
        }
        
        # Coletar dados paralelos
        features['oi_data'] = self.market_collector.fetch_open_interest()
        features['fr_data'] = self.market_collector.fetch_funding_rate()
        features['iv_data'] = self.market_collector.fetch_implied_volatility()
        features['dominance_data'] = self.market_collector.fetch_market_dominance()
        features['order_book_data'] = self.market_collector.fetch_order_book_snapshot()
        
        return features


if __name__ == "__main__":
    from data.database import DatabaseManager
    
    logging.basicConfig(level=logging.INFO)
    db = DatabaseManager()
    engineer = AdvancedFeatureEngineer(db)
    
    print("\n=== Advanced Feature Engineer ===\n")
    
    # Carregar features históricas
    df = engineer.get_historical_features(days_back=7)
    
    if not df.empty:
        print(f"Loaded {len(df)} records")
        print(df.head())
        
        # Validar
        validation = engineer.validate_features(df)
        print(f"\nValidation: {validation['is_valid']}")
