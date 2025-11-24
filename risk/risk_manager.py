# risk/risk_manager.py
import numpy as np
from typing import Dict
import logging
from config.settings import settings

logger = logging.getLogger(__name__)

class RiskManager:
    def __init__(self, capital: float = settings.INITIAL_CAPITAL):
        self.capital = capital
        self.position_size = 0.0
        self.max_drawdown = settings.MAX_DRAWDOWN
        self.daily_loss_limit = settings.DAILY_LOSS_LIMIT
        self.daily_losses = 0.0
        self.active_positions = []
        
        # Historical performance by pattern
        self.pattern_performance = {
            'head_shoulders': {'win_rate': 0.65, 'avg_win': 0.03, 'avg_loss': 0.02},
            'double_top': {'win_rate': 0.62, 'avg_win': 0.025, 'avg_loss': 0.018},
            'triangle_simetrico': {'win_rate': 0.58, 'avg_win': 0.02, 'avg_loss': 0.015},
            'flag_pennant': {'win_rate': 0.60, 'avg_win': 0.018, 'avg_loss': 0.016},
            'elliott_impulse': {'win_rate': 0.55, 'avg_win': 0.025, 'avg_loss': 0.02}
        }
    
    def calculate_position_size(self, confidence: float, volatility: float, pattern_type: str) -> float:
        """Calcula tamanho da posição usando Kelly Criterion adaptado"""
        if pattern_type not in self.pattern_performance:
            return 0.0
        
        perf = self.pattern_performance[pattern_type]
        win_prob = confidence
        win_loss_ratio = perf['avg_win'] / perf['avg_loss'] if perf['avg_loss'] > 0 else 1.5
        
        # Kelly formula
        kelly_fraction = win_prob - (1 - win_prob) / win_loss_ratio
        
        # Conservative Kelly (25% do valor)
        position_fraction = max(0, kelly_fraction * 0.25)
        
        # Ajustar por volatilidade
        volatility_adjustment = 1.0 / (volatility * np.sqrt(252) + 0.1)
        
        final_position = self.capital * position_fraction * volatility_adjustment
        
        # Limites de posição
        max_position = self.capital * settings.MAX_POSITION_SIZE
        min_position = self.capital * 0.01  # Mínimo 1%
        
        position = min(max(final_position, min_position), max_position)
        
        logger.info(f"Position size calculated: ${position:.2f} for {pattern_type} "
                   f"(confidence: {confidence:.2f}, volatility: {volatility:.4f})")
        
        return position
    
    def calculate_stop_loss(self, entry_price: float, signal_type: str, volatility: float) -> float:
        """Calcula stop-loss baseado em ATR"""
        atr_multiplier = 2.0  # 2x ATR
        
        if signal_type == 'buy':
            stop_loss = entry_price * (1 - atr_multiplier * volatility)
        else:  # sell
            stop_loss = entry_price * (1 + atr_multiplier * volatility)
        
        # Garantir stop-loss razoável
        max_stop_loss = 0.05  # 5% máximo
        if abs(stop_loss - entry_price) / entry_price > max_stop_loss:
            if signal_type == 'buy':
                stop_loss = entry_price * (1 - max_stop_loss)
            else:
                stop_loss = entry_price * (1 + max_stop_loss)
        
        return stop_loss
    
    def calculate_take_profit(self, entry_price: float, signal_type: str, pattern_type: str) -> float:
        """Calcula take-profit baseado no padrão"""
        targets = {
            'head_shoulders': 0.03,
            'double_top': 0.025,
            'triangle_simetrico': 0.02,
            'flag_pennant': 0.015,
            'elliott_impulse': 0.04
        }
        
        target_percent = targets.get(pattern_type, 0.02)
        
        if signal_type == 'buy':
            take_profit = entry_price * (1 + target_percent)
        else:  # sell
            take_profit = entry_price * (1 - target_percent)
        
        return take_profit
    
    def update_daily_losses(self, loss_amount: float):
        """Atualiza perdas diárias"""
        self.daily_losses += loss_amount
        logger.info(f"Daily losses updated: ${self.daily_losses:.2f}")
    
    def can_trade(self) -> bool:
        """Verifica se pode realizar novo trade baseado em limites de risco"""
        if self.daily_losses >= self.capital * self.daily_loss_limit:
            logger.warning("Daily loss limit reached - trading suspended")
            return False
        
        total_allocated = sum(pos['size'] for pos in self.active_positions)
        if total_allocated >= self.capital * settings.MAX_PORTFOLIO_RISK:
            logger.warning("Portfolio risk limit reached - trading suspended")
            return False
        
        return True
    
    def add_position(self, position_data: Dict):
        """Adiciona uma posição ativa"""
        self.active_positions.append(position_data)
        self.position_size += position_data['size']
    
    def remove_position(self, position_id: str):
        """Remove uma posição ativa"""
        self.active_positions = [pos for pos in self.active_positions if pos['id'] != position_id]
        self.position_size = sum(pos['size'] for pos in self.active_positions)
    
    def reset_daily_losses(self):
        """Reinicia perdas diárias (chamar no início do dia)"""
        self.daily_losses = 0.0
        logger.info("Daily losses reset")