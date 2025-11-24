# patterns/continuation_patterns.py
from .base_detector import BasePatternDetector
import pandas as pd
import numpy as np
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)

class ContinuationPatterns(BasePatternDetector):
    def __init__(self, df: pd.DataFrame):
        super().__init__(df)
    
    def detect(self) -> List[Dict]:
        """Detecta todos os padrões de continuação"""
        signals = []
        signals.extend(self.detect_triangles())
        signals.extend(self.detect_flags_pennants())
        return signals
    
    def detect_triangles(self, window: int = 20) -> List[Dict]:
        """Detecta triângulos simétricos, ascendentes e descendentes"""
        signals = []
        
        for i in range(window, len(self.df)):
            window_high = self.high[i-window:i]
            window_low = self.low[i-window:i]
            
            # Calcular inclinações
            high_slope = self._calculate_slope(window_high)
            low_slope = self._calculate_slope(window_low)
            
            # Classificar triângulo
            triangle_type, confidence = self._classify_triangle(high_slope, low_slope)
            
            if triangle_type and confidence > 0.6:
                signals.append({
                    'pattern': f'triangle_{triangle_type}',
                    'signal': 'continuation',
                    'confidence': confidence,
                    'index': i,
                    'price': self.close[i]
                })
        
        return signals
    
    def _classify_triangle(self, high_slope: float, low_slope: float) -> tuple:
        """Classifica o tipo de triângulo baseado nas inclinações"""
        threshold = 0.001
        
        if high_slope < -threshold and low_slope > threshold:
            # Triângulo simétrico
            confidence = min(abs(high_slope), abs(low_slope)) * 1000
            return "simetrico", min(confidence, 0.95)
        
        elif high_slope < -threshold and abs(low_slope) < threshold:
            # Triângulo descendente
            confidence = abs(high_slope) * 1000
            return "descendente", min(confidence, 0.95)
        
        elif low_slope > threshold and abs(high_slope) < threshold:
            # Triângulo ascendente
            confidence = abs(low_slope) * 1000
            return "ascendente", min(confidence, 0.95)
        
        return None, 0
    
    def detect_flags_pennants(self, window: int = 15) -> List[Dict]:
        """Detecta bandeiras e flâmulas"""
        signals = []
        
        for i in range(window, len(self.df)-5):
            # Verificar movimento anterior forte
            prior_move = self._check_prior_move(i, window)
            
            if prior_move['is_strong']:
                # Verificar consolidação
                consolidation = self._check_consolidation(i, window)
                
                if consolidation['is_tight']:
                    signals.append({
                        'pattern': 'flag_pennant',
                        'signal': 'continuation',
                        'direction': prior_move['direction'],
                        'confidence': consolidation['confidence'],
                        'index': i,
                        'price': self.close[i]
                    })
        
        return signals
    
    def _check_prior_move(self, index: int, window: int) -> Dict:
        """Verifica se houve um movimento forte anterior"""
        start_idx = index - window * 2
        if start_idx < 0:
            return {'is_strong': False, 'direction': None}
        
        price_change = (self.close[index] - self.close[start_idx]) / self.close[start_idx]
        is_strong = abs(price_change) > 0.02  # 2% de movimento
        direction = 'bullish' if price_change > 0 else 'bearish'
        
        return {'is_strong': is_strong, 'direction': direction}
    
    def _check_consolidation(self, index: int, window: int) -> Dict:
        """Verifica período de consolidação"""
        consolidation_high = max(self.high[index-window:index])
        consolidation_low = min(self.low[index-window:index])
        consolidation_range = (consolidation_high - consolidation_low) / consolidation_low
        
        is_tight = consolidation_range < 0.015  # 1.5% de range
        confidence = 0.7 if is_tight else 0.0
        
        return {'is_tight': is_tight, 'confidence': confidence}