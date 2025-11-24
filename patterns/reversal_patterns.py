# patterns/reversal_patterns.py
from .base_detector import BasePatternDetector
import pandas as pd
import numpy as np
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)

class ReversalPatterns(BasePatternDetector):
    def __init__(self, df: pd.DataFrame):
        super().__init__(df)
    
    def detect(self) -> List[Dict]:
        """Detecta todos os padrões de reversão"""
        signals = []
        signals.extend(self.detect_head_shoulders())
        signals.extend(self.detect_double_tops_bottoms())
        return signals
    
    def detect_head_shoulders(self, window: int = 40) -> List[Dict]:
        """Detecta padrões Head and Shoulders"""
        signals = []
        
        for i in range(window, len(self.df)-10):
            segment_high = self.high[i-window:i]
            segment_low = self.low[i-window:i]
            
            peaks = self._find_peaks(segment_high, 3)
            troughs = self._find_troughs(segment_low, 2)
            
            if len(peaks) == 3 and len(troughs) == 2:
                pattern_info = self._validate_head_shoulders(peaks, troughs, i)
                if pattern_info['is_valid']:
                    signals.append({
                        'pattern': 'head_shoulders',
                        'signal': 'sell',
                        'confidence': pattern_info['confidence'],
                        'index': i,
                        'price': self.close[i],
                        'neckline_slope': pattern_info['neckline_slope']
                    })
        
        return signals
    
    def _validate_head_shoulders(self, peaks: List[Dict], troughs: List[Dict], current_index: int) -> Dict:
        """Valida se os picos formam um padrão Head and Shoulders válido"""
        left_shoulder, head, right_shoulder = peaks
        neckline1, neckline2 = troughs
        
        conditions = [
            head['value'] > left_shoulder['value'] * 1.01,
            head['value'] > right_shoulder['value'] * 1.01,
            abs(left_shoulder['value'] - right_shoulder['value']) / left_shoulder['value'] < 0.01,
            neckline2['index'] > head['index']
        ]
        
        is_valid = all(conditions)
        
        if is_valid:
            confidence = 0.8
            neckline_slope = (neckline2['value'] - neckline1['value']) / (neckline2['index'] - neckline1['index'])
        else:
            confidence = 0.0
            neckline_slope = 0.0
        
        return {'is_valid': is_valid, 'confidence': confidence, 'neckline_slope': neckline_slope}
    
    def detect_double_tops_bottoms(self, window: int = 30) -> List[Dict]:
        """Detecta topos e fundos duplos"""
        signals = []
        
        for i in range(window, len(self.df)-10):
            # Topos duplos
            double_top = self._find_double_top(i, window)
            if double_top['found']:
                signals.append({
                    'pattern': 'double_top',
                    'signal': 'sell',
                    'confidence': double_top['confidence'],
                    'index': i,
                    'price': self.close[i]
                })
            
            # Fundos duplos
            double_bottom = self._find_double_bottom(i, window)
            if double_bottom['found']:
                signals.append({
                    'pattern': 'double_bottom',
                    'signal': 'buy',
                    'confidence': double_bottom['confidence'],
                    'index': i,
                    'price': self.close[i]
                })
        
        return signals
    
    def _find_double_top(self, index: int, window: int) -> Dict:
        """Encontra padrão de topo duplo"""
        lookback_highs = self.high[index-window:index]
        peaks = self._find_peaks(lookback_highs, 2)
        
        if len(peaks) == 2:
            price_diff = abs(peaks[0]['value'] - peaks[1]['value']) / peaks[0]['value']
            if price_diff < 0.01:  # Preços similares (1% de diferença)
                return {'found': True, 'confidence': 0.75}
        
        return {'found': False, 'confidence': 0.0}
    
    def _find_double_bottom(self, index: int, window: int) -> Dict:
        """Encontra padrão de fundo duplo"""
        lookback_lows = self.low[index-window:index]
        troughs = self._find_troughs(lookback_lows, 2)
        
        if len(troughs) == 2:
            price_diff = abs(troughs[0]['value'] - troughs[1]['value']) / troughs[0]['value']
            if price_diff < 0.01:
                return {'found': True, 'confidence': 0.75}
        
        return {'found': False, 'confidence': 0.0}