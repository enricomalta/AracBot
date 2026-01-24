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
    
    def detect_triangles(self, window: int = 20) -> List[Dict]:  # Aumentado para 20
        """Detecta triângulos simétricos com validação de breakout e volume"""
        signals = []
        
        for i in range(window, len(self.df)-3):
            if i < window:
                continue
            
            # Calcular trendlines de suporte e resistência
            highs = self.high[i-window:i]
            lows = self.low[i-window:i]
            volumes = self.volume[i-window:i]
            
            # Verificar convergência
            recent_range = max(highs) - min(lows)
            prev_range = max(self.high[i-window*2:i-window]) - min(self.low[i-window*2:i-window]) if i >= window*2 else recent_range
            
            if prev_range == 0:
                continue
            
            # Convergência: range atual menor que anterior
            convergence_ratio = recent_range / prev_range
            if convergence_ratio > 0.7:  # Não está convergindo suficiente
                continue
            
            # Validação 1: Volume deve diminuir durante consolidação
            recent_vol = np.mean(volumes[-5:])
            prev_vol = np.mean(volumes[:-5]) if len(volumes) > 5 else recent_vol
            
            if prev_vol == 0 or recent_vol > prev_vol * 1.1:
                continue  # Volume não está diminuindo
            
            # Validação 2: Verificar se houve breakout
            current_price = self.close[i]
            upper_bound = max(highs[-5:])
            lower_bound = min(lows[-5:])
            
            # Aguardar breakout confirmado
            if i < len(self.close) - 1:
                next_price = self.close[i+1] if i+1 < len(self.close) else current_price
                
                # Breakout para cima
                if next_price > upper_bound * 1.005:  # 0.5% acima
                    # Confirmar com volume
                    breakout_volume = self.volume[i+1] if i+1 < len(self.volume) else recent_vol
                    if breakout_volume > prev_vol * 1.2:  # Volume 20% maior
                        confidence = 0.80
                        signal = 'buy'
                    else:
                        confidence = 0.70
                        signal = 'buy'
                    
                    signals.append({
                        'pattern': 'triangle_simetrico',
                        'signal': signal,
                        'confidence': confidence,
                        'index': i,
                        'price': current_price
                    })
                
                # Breakout para baixo
                elif next_price < lower_bound * 0.995:  # 0.5% abaixo
                    breakout_volume = self.volume[i+1] if i+1 < len(self.volume) else recent_vol
                    if breakout_volume > prev_vol * 1.2:
                        confidence = 0.80
                        signal = 'sell'
                    else:
                        confidence = 0.70
                        signal = 'sell'
                    
                    signals.append({
                        'pattern': 'triangle_simetrico',
                        'signal': signal,
                        'confidence': confidence,
                        'index': i,
                        'price': current_price
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
        """Verifica período de consolidação com volume"""
        consolidation_high = max(self.high[index-window:index])
        consolidation_low = min(self.low[index-window:index])
        consolidation_range = (consolidation_high - consolidation_low) / consolidation_low
        
        if consolidation_range >= 0.015:  # Range muito grande
            return {'is_tight': False, 'confidence': 0.0}
        
        # Verificar volume: deve diminuir durante consolidação
        recent_vol = np.mean(self.volume[index-5:index])
        prev_vol = np.mean(self.volume[index-15:index-5]) if index >= 15 else recent_vol
        
        if prev_vol == 0 or recent_vol > prev_vol * 0.9:
            return {'is_tight': False, 'confidence': 0.0}
        
        # Verificar breakout iminente com volume
        if index < len(self.close) - 1:
            next_candle_vol = self.volume[index] if index < len(self.volume) else recent_vol
            if next_candle_vol > prev_vol * 1.3:  # Volume 30% maior indica breakout
                confidence = 0.85
            else:
                confidence = 0.75
        else:
            confidence = 0.75
        
        return {'is_tight': True, 'confidence': confidence}