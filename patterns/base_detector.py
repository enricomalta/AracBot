# patterns/base_detector.py
from abc import ABC, abstractmethod
import pandas as pd
import numpy as np
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)

class BasePatternDetector(ABC):
    def __init__(self, df: pd.DataFrame):
        self.df = df
        self.high = df['high'].values
        self.low = df['low'].values
        self.close = df['close'].values
        self.open = df['open'].values
        self.volume = df['volume'].values
    
    @abstractmethod
    def detect(self) -> List[Dict]:
        """Método abstrato para detecção de padrões"""
        pass
    
    def _find_peaks(self, values: np.ndarray, count: int = 3) -> List[Dict]:
        """Encontra picos locais nos valores"""
        peaks = []
        for i in range(1, len(values)-1):
            if values[i] > values[i-1] and values[i] > values[i+1]:
                peaks.append({'index': i, 'value': values[i]})
        
        return sorted(peaks, key=lambda x: x['value'], reverse=True)[:count]
    
    def _find_troughs(self, values: np.ndarray, count: int = 3) -> List[Dict]:
        """Encontra vales locais nos valores"""
        troughs = []
        for i in range(1, len(values)-1):
            if values[i] < values[i-1] and values[i] < values[i+1]:
                troughs.append({'index': i, 'value': values[i]})
        
        return sorted(troughs, key=lambda x: x['value'])[:count]
    
    def _calculate_slope(self, values: np.ndarray) -> float:
        """Calcula a inclinação de uma série de valores"""
        if len(values) < 2:
            return 0
        x = np.arange(len(values))
        slope = np.polyfit(x, values, 1)[0]
        return slope