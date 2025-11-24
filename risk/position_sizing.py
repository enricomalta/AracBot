# risk/position_sizing.py
import numpy as np
from typing import Dict

class PositionSizing:
    def __init__(self):
        self.methods = {
            'kelly': self._kelly_criterion,
            'fixed_fraction': self._fixed_fraction,
            'volatility_adjusted': self._volatility_adjusted
        }
    
    def calculate_size(self, method: str, capital: float, **kwargs) -> float:
        """Calcula tamanho da posição usando método especificado"""
        if method not in self.methods:
            raise ValueError(f"Unknown position sizing method: {method}")
        
        return self.methods[method](capital, **kwargs)
    
    def _kelly_criterion(self, capital: float, win_rate: float, win_loss_ratio: float) -> float:
        """Kelly Criterion para sizing"""
        kelly_fraction = win_rate - (1 - win_rate) / win_loss_ratio
        # Conservative Kelly (metade)
        return capital * max(0, kelly_fraction * 0.5)
    
    def _fixed_fraction(self, capital: float, risk_per_trade: float = 0.02) -> float:
        """Fixed fractional sizing"""
        return capital * risk_per_trade
    
    def _volatility_adjusted(self, capital: float, volatility: float, 
                           base_risk: float = 0.02, max_risk: float = 0.05) -> float:
        """Volatility-adjusted position sizing"""
        # Reduz risco em alta volatilidade
        volatility_factor = 1.0 / (volatility * np.sqrt(252) + 0.1)
        risk = min(base_risk * volatility_factor, max_risk)
        return capital * risk