# ml/validator.py
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.svm import SVC
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report, accuracy_score
import joblib
import talib
from typing import Dict, List, Tuple
import logging
from config.settings import settings

logger = logging.getLogger(__name__)

class PatternMLValidator:
    def __init__(self):
        self.models = {}
        self.scalers = {}
        self.feature_importance = {}
        
    def create_ml_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Cria features técnicas para o modelo ML (sem look-ahead bias)"""
        features_df = df.copy()
        
        # Indicadores técnicos
        features_df['rsi'] = talib.RSI(df['close'], timeperiod=14)
        features_df['rsi_21'] = talib.RSI(df['close'], timeperiod=21)
        features_df['macd'], features_df['macd_signal'], features_df['macd_hist'] = talib.MACD(df['close'])
        features_df['bb_upper'], features_df['bb_middle'], features_df['bb_lower'] = talib.BBANDS(df['close'], timeperiod=20)
        features_df['atr'] = talib.ATR(df['high'], df['low'], df['close'], timeperiod=14)
        features_df['adx'] = talib.ADX(df['high'], df['low'], df['close'], timeperiod=14)
        features_df['obv'] = talib.OBV(df['close'], df['volume'])
        
        # Features de momentum (passado)
        features_df['momentum_5'] = df['close'].pct_change(5)
        features_df['momentum_10'] = df['close'].pct_change(10)
        features_df['momentum_20'] = df['close'].pct_change(20)
        features_df['volatility_10'] = df['close'].pct_change().rolling(10).std()
        features_df['volatility_20'] = df['close'].pct_change().rolling(20).std()
        
        # Features de volume
        features_df['volume_sma'] = df['volume'].rolling(20).mean()
        features_df['volume_ratio'] = df['volume'] / features_df['volume_sma']
        features_df['volume_change'] = df['volume'].pct_change(5)
        
        # Features de preço
        features_df['high_low_ratio'] = df['high'] / df['low']
        features_df['close_open_ratio'] = df['close'] / df['open']
        features_df['price_to_sma_20'] = df['close'] / df['close'].rolling(20).mean()
        features_df['price_to_sma_50'] = df['close'] / df['close'].rolling(50).mean()
        
        # Trend features
        features_df['sma_20'] = df['close'].rolling(20).mean()
        features_df['sma_50'] = df['close'].rolling(50).mean()
        features_df['trend_strength'] = (features_df['sma_20'] - features_df['sma_50']) / features_df['sma_50']
        
        # BB position
        features_df['bb_position'] = (df['close'] - features_df['bb_lower']) / (features_df['bb_upper'] - features_df['bb_lower'])
        
        # Stochastic
        features_df['slowk'], features_df['slowd'] = talib.STOCH(df['high'], df['low'], df['close'])
        
        # Target: retorno futuro real (para treino) - shift negativo
        features_df['future_return_1h'] = df['close'].shift(-6) / df['close'] - 1
        features_df['future_return_4h'] = df['close'].shift(-24) / df['close'] - 1
        
        return features_df.dropna()
    
    def prepare_ml_data(self, features_df: pd.DataFrame, pattern_type: str) -> Tuple[np.ndarray, np.ndarray]:
        """Prepara dados para treinamento baseado no tipo de padrão"""
        if pattern_type == 'reversal':
            target = (features_df['future_return_1h'] * features_df['future_return_4h'] < 0).astype(int)
        else:  # continuation
            target = (features_df['future_return_1h'] * features_df['future_return_4h'] > 0).astype(int)
        
        feature_columns = [col for col in features_df.columns if col not in 
                          ['future_return_1h', 'future_return_4h', 'timestamp', 'open', 'high', 'low', 'close', 'volume']]
        
        X = features_df[feature_columns].values
        y = target.values
        
        return X, y
    
    def train_models(self, historical_data: pd.DataFrame) -> Dict[str, Dict]:
        """Treina modelos ML e retorna métricas para auditoria do treino."""
        features_df = self.create_ml_features(historical_data)
        training_summary: Dict[str, Dict] = {}
        
        for pattern_type in ['reversal', 'continuation']:
            X, y = self.prepare_ml_data(features_df, pattern_type)
            
            if len(np.unique(y)) < 2:
                logger.warning(f"Not enough classes for {pattern_type} model")
                training_summary[pattern_type] = {
                    'trained': False,
                    'reason': 'not_enough_target_classes',
                    'samples': int(len(y)),
                }
                continue
                
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
            
            # Scale features
            scaler = StandardScaler()
            X_train_scaled = scaler.fit_transform(X_train)
            X_test_scaled = scaler.transform(X_test)
            
            # Treinar múltiplos modelos
            models = {
                'random_forest': RandomForestClassifier(n_estimators=100, random_state=42),
                'gradient_boosting': GradientBoostingClassifier(n_estimators=100, random_state=42),
            }
            
            best_score = -1.0
            best_model = None
            best_model_name = None
            
            for name, model in models.items():
                model.fit(X_train_scaled, y_train)
                score = model.score(X_test_scaled, y_test)
                
                if score > best_score:
                    best_score = score
                    best_model = model
                    best_model_name = name
            
            self.models[pattern_type] = best_model
            self.scalers[pattern_type] = scaler
            
            # Feature importance
            if hasattr(best_model, 'feature_importances_'):
                feature_names = [col for col in features_df.columns if col not in 
                               ['future_return_1h', 'future_return_4h', 'timestamp', 'open', 'high', 'low', 'close', 'volume']]
                self.feature_importance[pattern_type] = dict(zip(feature_names, best_model.feature_importances_))
            
            logger.info(f"Model {pattern_type} trained - Accuracy: {best_score:.3f}")
            training_summary[pattern_type] = {
                'trained': True,
                'samples': int(len(y)),
                'train_samples': int(len(X_train)),
                'test_samples': int(len(X_test)),
                'accuracy': float(best_score),
                'model': best_model_name,
            }

        if not self.models:
            raise ValueError("No ML model was trained; historical data is insufficient or has one target class.")
        return training_summary
    
    def validate_pattern_with_ml(self, current_data: pd.DataFrame, pattern_type: str, pattern_confidence: float) -> float:
        """Usa ML para validar e ajustar a confiança do padrão"""
        if pattern_type not in self.models:
            return pattern_confidence
        
        try:
            features_df = self.create_ml_features(current_data)
            if len(features_df) == 0:
                return pattern_confidence
            
            feature_columns = [col for col in features_df.columns if col not in 
                             ['future_return_1h', 'future_return_4h', 'timestamp', 'open', 'high', 'low', 'close', 'volume']]
            
            X_current = features_df[feature_columns].iloc[-1:].values
            X_scaled = self.scalers[pattern_type].transform(X_current)
            
            ml_confidence = self.models[pattern_type].predict_proba(X_scaled)[0, 1]
            # Peso 50/50 entre pattern e ML
            combined_confidence = (pattern_confidence * 0.5 + ml_confidence * 0.5)
            
            # Se ML discorda fortemente (< 0.4), reduzir ainda mais
            if ml_confidence < 0.4:
                combined_confidence *= 0.8
            
            return combined_confidence
            
        except Exception as e:
            logger.error(f"ML validation error: {e}")
            return pattern_confidence
    
    def save_models(self, model_path: str = None, scaler_path: str = None):
        """Salva modelos treinados"""
        try:
            joblib.dump(self.models, model_path or settings.ML_MODEL_PATH)
            joblib.dump(self.scalers, scaler_path or settings.ML_SCALER_PATH)
            logger.info("ML models saved successfully")
        except Exception as e:
            logger.error(f"Error saving ML models: {e}")
    
    def load_models(self):
        """Carrega modelos treinados"""
        try:
            self.models = joblib.load(settings.ML_MODEL_PATH)
            self.scalers = joblib.load(settings.ML_SCALER_PATH)
            logger.info("ML models loaded successfully")
            return True
        except Exception as e:
            logger.warning(f"Could not load ML models: {e}")
            return False
