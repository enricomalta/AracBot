# ml/feature_engineering.py
import pandas as pd
import numpy as np
import talib
from typing import List

class FeatureEngineer:
    def __init__(self):
        self.feature_config = {
            'rsi_periods': [14, 21],
            'macd_fast': 12,
            'macd_slow': 26,
            'macd_signal': 9,
            'bb_period': 20,
            'atr_period': 14,
            'adx_period': 14
        }
    
    def create_technical_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Cria features técnicas completas"""
        features_df = df.copy()
        
        # RSI múltiplos períodos
        for period in self.feature_config['rsi_periods']:
            features_df[f'rsi_{period}'] = talib.RSI(df['close'], timeperiod=period)
        
        # MACD
        features_df['macd'], features_df['macd_signal'], features_df['macd_hist'] = talib.MACD(
            df['close'], 
            fastperiod=self.feature_config['macd_fast'],
            slowperiod=self.feature_config['macd_slow'], 
            signalperiod=self.feature_config['macd_signal']
        )
        
        # Bollinger Bands
        features_df['bb_upper'], features_df['bb_middle'], features_df['bb_lower'] = talib.BBANDS(
            df['close'], timeperiod=self.feature_config['bb_period']
        )
        features_df['bb_width'] = (features_df['bb_upper'] - features_df['bb_lower']) / features_df['bb_middle']
        features_df['bb_position'] = (df['close'] - features_df['bb_lower']) / (features_df['bb_upper'] - features_df['bb_lower'])
        
        # ATR e ADX
        features_df['atr'] = talib.ATR(df['high'], df['low'], df['close'], timeperiod=self.feature_config['atr_period'])
        features_df['adx'] = talib.ADX(df['high'], df['low'], df['close'], timeperiod=self.feature_config['adx_period'])
        
        # Volume indicators
        features_df['obv'] = talib.OBV(df['close'], df['volume'])
        features_df['volume_sma'] = df['volume'].rolling(20).mean()
        features_df['volume_ratio'] = df['volume'] / features_df['volume_sma']
        
        # Price features
        features_df['returns_1'] = df['close'].pct_change(1)
        features_df['returns_5'] = df['close'].pct_change(5)
        features_df['returns_10'] = df['close'].pct_change(10)
        features_df['volatility_10'] = df['close'].pct_change().rolling(10).std()
        features_df['high_low_ratio'] = df['high'] / df['low']
        features_df['close_open_ratio'] = df['close'] / df['open']
        
        # Support and Resistance features
        features_df['resistance_level'] = self._calculate_resistance_level(df)
        features_df['support_level'] = self._calculate_support_level(df)
        
        return features_df.dropna()
    
    def _calculate_resistance_level(self, df: pd.DataFrame, window: int = 20) -> pd.Series:
        """Calcula nível de resistência"""
        return df['high'].rolling(window).max()
    
    def _calculate_support_level(self, df: pd.DataFrame, window: int = 20) -> pd.Series:
        """Calcula nível de suporte"""
        return df['low'].rolling(window).min()
    
    def create_pattern_features(self, df: pd.DataFrame, pattern_signals: List[Dict]) -> pd.DataFrame:
        """Cria features baseadas em padrões detectados"""
        features_df = df.copy()
        
        # Contagem de padrões por tipo
        pattern_counts = {}
        for signal in pattern_signals:
            pattern_type = signal['pattern']
            if pattern_type not in pattern_counts:
                pattern_counts[pattern_type] = 0
            pattern_counts[pattern_type] += 1
        
        for pattern_type, count in pattern_counts.items():
            features_df[f'pattern_{pattern_type}_count'] = count
        
        return features_df