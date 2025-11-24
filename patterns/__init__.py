# patterns/__init__.py
import pandas as pd
from typing import List, Dict
from .base_detector import BasePatternDetector
from .continuation_patterns import ContinuationPatterns
from .reversal_patterns import ReversalPatterns
from .elliott_waves import ElliottWavePatterns

class PatternRecognitionBot:
    def __init__(self):
        self.detectors = []
    
    def analyze_market(self, df: pd.DataFrame) -> List[Dict]:
        """Analisa o mercado usando todos os detectores de padrão"""
        signals = []
        
        # Inicializar detectores
        continuation_detector = ContinuationPatterns(df)
        reversal_detector = ReversalPatterns(df)
        elliott_detector = ElliottWavePatterns(df)
        
        # Executar detecção
        signals.extend(continuation_detector.detect())
        signals.extend(reversal_detector.detect())
        signals.extend(elliott_detector.detect())
        
        # Filtrar e ordenar sinais
        filtered_signals = self._filter_signals(signals)
        return filtered_signals
    
    def _filter_signals(self, signals: List[Dict]) -> List[Dict]:
        """Filtra sinais por confiança e remove duplicatas"""
        # Ordenar por confiança
        signals.sort(key=lambda x: x['confidence'], reverse=True)
        
        # Remover sinais muito próximos
        filtered = []
        used_indices = set()
        
        for signal in signals:
            if signal['index'] not in used_indices:
                filtered.append(signal)
                # Marcar índices próximos como usados
                for i in range(signal['index']-3, signal['index']+4):
                    used_indices.add(i)
        
        return filtered