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
    
    def detect_double_tops_bottoms(self, window: int = 25) -> List[Dict]:  # Balanceado para 25
        """Detecta topos e fundos duplos com validação rigorosa"""
        signals = []
        
        for i in range(window, len(self.df)-5):  # Buffer de 5 velas
            # Topos duplos - versão rigorosa
            double_top = self._find_double_top_rigorous(i, window)
            if double_top['found']:
                signals.append({
                    'pattern': 'double_top',
                    'signal': 'sell',
                    'confidence': double_top['confidence'],
                    'index': i,
                    'price': self.close[i]
                })
            
            # Fundos duplos - versão rigorosa
            double_bottom = self._find_double_bottom_rigorous(i, window)
            if double_bottom['found']:
                signals.append({
                    'pattern': 'double_bottom',
                    'signal': 'buy',
                    'confidence': double_bottom['confidence'],
                    'index': i,
                    'price': self.close[i]
                })
        
        return signals
    
    def _find_double_top_rigorous(self, index: int, window: int) -> Dict:
        """Encontra padrão de topo duplo com validação rigorosa"""
        import talib
        
        if index < window + 14:  # Precisa de dados para RSI
            return {'found': False, 'confidence': 0.0}
        
        recent_highs = self.high[max(0, index-window):index]
        recent_closes = self.close[max(0, index-window):index]
        recent_volumes = self.volume[max(0, index-window):index]
        
        if len(recent_highs) < 10:
            return {'found': False, 'confidence': 0.0}
        
        # Encontrar picos locais
        peaks = self._find_peaks(recent_highs, count=2)
        if len(peaks) < 2:
            return {'found': False, 'confidence': 0.0}
        
        peak1, peak2 = peaks[0], peaks[1]
        
        # Validação 1: Picos devem ser similares (< 1.5% diferença)
        price_diff = abs(peak1['value'] - peak2['value']) / peak1['value']
        if price_diff > 0.015:
            return {'found': False, 'confidence': 0.0}
        
        # Validação 2: Deve haver vale entre os picos
        if peak2['index'] <= peak1['index']:
            peak1, peak2 = peak2, peak1
        
        valley_segment = recent_highs[peak1['index']:peak2['index']]
        if len(valley_segment) < 3:
            return {'found': False, 'confidence': 0.0}
        
        valley_min = min(valley_segment)
        retrace = (peak1['value'] - valley_min) / peak1['value']
        if retrace < 0.02:  # Mínimo 2% de retração
            return {'found': False, 'confidence': 0.0}
        
        # Validação 3: Volume deve diminuir no segundo pico
        vol1 = np.mean(recent_volumes[max(0, peak1['index']-2):peak1['index']+2])
        vol2 = np.mean(recent_volumes[max(0, peak2['index']-2):peak2['index']+2])
        if vol2 > vol1 * 0.9:  # Volume do 2º pico deve ser menor
            return {'found': False, 'confidence': 0.0}
        
        # Validação 4: RSI divergence OBRIGATÓRIO (preço faz novo topo, RSI não)
        rsi_data = talib.RSI(self.close[max(0, index-window-14):index], timeperiod=14)
        if len(rsi_data) > window:
            rsi1 = rsi_data[-(window - peak1['index'])]
            rsi2 = rsi_data[-(window - peak2['index'])] if window - peak2['index'] > 0 else rsi_data[-1]
            
            # Divergência bearish OBRIGATÓRIA: RSI menor no 2º pico
            if rsi2 >= rsi1:
                return {'found': False, 'confidence': 0.0}  # SEM divergência = falso positivo
            
            # Quanto maior a divergência, maior a confiança
            if rsi2 < rsi1 - 10:
                confidence = 0.90
            elif rsi2 < rsi1 - 5:
                confidence = 0.80
            else:
                confidence = 0.75
        else:
            return {'found': False, 'confidence': 0.0}  # Sem dados RSI = rejei tar
        
        # Ajustar confiança baseado em volume
        volume_ratio = vol2 / vol1 if vol1 > 0 else 1
        if volume_ratio < 0.7:  # Volume muito menor
            confidence = min(confidence + 0.05, 0.95)
        
        return {'found': True, 'confidence': confidence}
    
    def _find_double_bottom_rigorous(self, index: int, window: int) -> Dict:
        """Encontra padrão de fundo duplo com validação rigorosa"""
        import talib
        
        if index < window + 14:
            return {'found': False, 'confidence': 0.0}
        
        recent_lows = self.low[max(0, index-window):index]
        recent_closes = self.close[max(0, index-window):index]
        recent_volumes = self.volume[max(0, index-window):index]
        
        if len(recent_lows) < 10:
            return {'found': False, 'confidence': 0.0}
        
        # Encontrar vales locais
        troughs = self._find_troughs(recent_lows, count=2)
        if len(troughs) < 2:
            return {'found': False, 'confidence': 0.0}
        
        trough1, trough2 = troughs[0], troughs[1]
        
        # Validação 1: Fundos similares (< 1.5%)
        price_diff = abs(trough1['value'] - trough2['value']) / trough1['value']
        if price_diff > 0.015:
            return {'found': False, 'confidence': 0.0}
        
        # Validação 2: Pico entre fundos
        if trough2['index'] <= trough1['index']:
            trough1, trough2 = trough2, trough1
        
        peak_segment = recent_lows[trough1['index']:trough2['index']]
        if len(peak_segment) < 3:
            return {'found': False, 'confidence': 0.0}
        
        peak_max = max(peak_segment)
        rally = (peak_max - trough1['value']) / trough1['value']
        if rally < 0.02:  # Mínimo 2% de rally
            return {'found': False, 'confidence': 0.0}
        
        # Validação 3: Volume aumenta no segundo fundo (buyers stepping in)
        vol1 = np.mean(recent_volumes[max(0, trough1['index']-2):trough1['index']+2])
        vol2 = np.mean(recent_volumes[max(0, trough2['index']-2):trough2['index']+2])
        if vol2 < vol1 * 1.1:  # Volume deve aumentar
            return {'found': False, 'confidence': 0.0}
        
        # Validação 4: RSI divergence bullish OBRIGATÓRIA
        rsi_data = talib.RSI(self.close[max(0, index-window-14):index], timeperiod=14)
        if len(rsi_data) > window:
            rsi1 = rsi_data[-(window - trough1['index'])]
            rsi2 = rsi_data[-(window - trough2['index'])] if window - trough2['index'] > 0 else rsi_data[-1]
            
            # Divergência bullish OBRIGATÓRIA: RSI maior no 2º fundo
            if rsi2 <= rsi1:
                return {'found': False, 'confidence': 0.0}
            
            # Quanto maior a divergência, maior a confiança
            if rsi2 > rsi1 + 10:
                confidence = 0.90
            elif rsi2 > rsi1 + 5:
                confidence = 0.80
            else:
                confidence = 0.75
        else:
            return {'found': False, 'confidence': 0.0}
        
        # Ajustar por volume
        volume_ratio = vol2 / vol1 if vol1 > 0 else 1
        if volume_ratio > 1.3:  # Volume significativamente maior
            confidence = min(confidence + 0.05, 0.95)
        
        return {'found': True, 'confidence': confidence}