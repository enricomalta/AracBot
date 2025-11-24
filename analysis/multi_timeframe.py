# analysis/multi_timeframe.py
from typing import Dict, List
import pandas as pd
import logging
from data.api_client import APIClient
from patterns import PatternRecognitionBot
from config.settings import settings

logger = logging.getLogger(__name__)

class MultiTimeframeAnalyzer:
    def __init__(self):
        self.api_client = APIClient()
        self.pattern_bot = PatternRecognitionBot()
        self.timeframe_weights = {
            '1m': 0.1, 
            '5m': 0.2, 
            '15m': 0.3, 
            '1h': 0.25, 
            '4h': 0.15
        }
    
    def analyze_symbol(self, symbol: str = settings.SYMBOL) -> Dict:
        """Analisa padrões em múltiplos timeframes para um símbolo"""
        timeframe_signals = {}
        
        for timeframe in settings.TIMEFRAMES:
            try:
                data = self.api_client.fetch_klines(symbol, timeframe, limit=100)
                if data is not None:
                    signals = self.pattern_bot.analyze_market(data)
                    
                    # Ajustar confiança pelo peso do timeframe
                    for signal in signals:
                        signal['confidence'] *= self.timeframe_weights[timeframe]
                        signal['timeframe'] = timeframe
                    
                    timeframe_signals[timeframe] = signals
                    logger.info(f"Timeframe {timeframe}: {len(signals)} signals found")
                    
            except Exception as e:
                logger.error(f"Error analyzing {timeframe} for {symbol}: {e}")
        
        return self.consolidate_signals(timeframe_signals)
    
    def consolidate_signals(self, timeframe_signals: Dict) -> List[Dict]:
        """Consolida sinais de diferentes timeframes"""
        all_signals = []
        
        for timeframe, signals in timeframe_signals.items():
            all_signals.extend(signals)
        
        # Agrupar por tipo de padrão
        pattern_groups = {}
        for signal in all_signals:
            pattern = signal['pattern']
            if pattern not in pattern_groups:
                pattern_groups[pattern] = []
            pattern_groups[pattern].append(signal)
        
        # Calcular confiança consolidada
        consolidated = []
        for pattern, signals in pattern_groups.items():
            total_confidence = sum(s['confidence'] for s in signals)
            avg_confidence = total_confidence / len(signals)
            confirming_tfs = len(set(s['timeframe'] for s in signals))
            
            # Só considerar se múltiplos timeframes confirmam
            if confirming_tfs >= 2 and avg_confidence > settings.MIN_CONFIDENCE:
                consolidated.append({
                    'pattern': pattern,
                    'signal': signals[0]['signal'],  # Assumir mesmo sinal
                    'confidence': avg_confidence,
                    'combined_confidence': avg_confidence,
                    'confirming_timeframes': confirming_tfs,
                    'timeframes': list(set(s['timeframe'] for s in signals)),
                    'price': signals[0]['price']  # Preço mais recente
                })
        
        logger.info(f"Consolidated {len(consolidated)} signals from multiple timeframes")
        return consolidated
    
    def get_timeframe_consensus(self, symbol: str) -> Dict:
        """Retorna consenso entre timeframes"""
        signals = self.analyze_symbol(symbol)
        
        bullish_signals = [s for s in signals if s['signal'] in ['buy', 'continuation']]
        bearish_signals = [s for s in signals if s['signal'] == 'sell']
        
        total_confidence_bullish = sum(s['confidence'] for s in bullish_signals)
        total_confidence_bearish = sum(s['confidence'] for s in bearish_signals)
        
        consensus = {
            'bullish_confidence': total_confidence_bullish,
            'bearish_confidence': total_confidence_bearish,
            'net_confidence': total_confidence_bullish - total_confidence_bearish,
            'total_signals': len(signals),
            'bullish_signals': len(bullish_signals),
            'bearish_signals': len(bearish_signals),
            'signals': signals
        }
        
        return consensus