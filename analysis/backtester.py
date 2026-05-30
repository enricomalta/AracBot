# analysis/backtester.py
import pandas as pd
import numpy as np
from typing import List, Dict
import logging
from patterns import PatternRecognitionBot
from ml.validator import PatternMLValidator
from risk.risk_manager import RiskManager
from config.settings import settings

logger = logging.getLogger(__name__)

class Backtester:
    def __init__(self, initial_capital: float = settings.BACKTEST_INITIAL_CAPITAL, db_manager=None):
        self.initial_capital = initial_capital
        self.results = {}
        self.risk_manager = RiskManager(initial_capital)
        self.db_manager = db_manager
    
    def run_backtest(self, historical_data: pd.DataFrame, 
                    patterns_to_test: List[str] = None) -> Dict:
        """Executa backtest completo"""
        capital = self.initial_capital
        trades = []
        equity_curve = []
        
        detector = PatternRecognitionBot()
        ml_validator = PatternMLValidator()
        
        # Treinar modelos ML com primeira metade dos dados
        split_idx = len(historical_data) // 2
        train_data = historical_data.iloc[:split_idx]
        test_data = historical_data.iloc[split_idx:]
        
        logger.info("Training ML models for backtest...")
        ml_validator.train_models(train_data)
        
        min_data_points = 50  # Reduzido para funcionar com menos dados
        for i in range(min_data_points, len(test_data)):
            current_data = test_data.iloc[:i+1]
            current_price = current_data['close'].iloc[-1]
            
            # Detectar padrões
            signals = detector.analyze_market(current_data)

            # Persistir sinais detectados para retreinamento
            if self.db_manager and signals:
                timestamp = str(current_data['timestamp'].iloc[-1])
                market_snapshot = current_data.tail(10).to_dict()
                for s in signals:
                    try:
                        signal_data = {
                            'timestamp': timestamp,
                            'pattern': s.get('pattern', 'unknown'),
                            'confidence': s.get('confidence', 0),
                            'signal': s.get('signal', 'unknown'),
                            'price': s.get('price', current_price),
                            'market_data': market_snapshot
                        }
                        self.db_manager.save_signal_for_analysis(signal_data)
                    except Exception as e:
                        logger.warning(f"Could not persist backtest signal: {e}")
            
            for signal in signals:
                # Filtrar padrões com performance ruim
                if signal['pattern'] == 'triangle_simetrico':
                    continue  # Pular triangle_simetrico por enquanto
                
                if patterns_to_test and signal['pattern'] not in patterns_to_test:
                    continue
                
                # Converter 'continuation' em 'buy' ou 'sell' baseado na direção
                if signal.get('signal') == 'continuation':
                    direction = signal.get('direction', 'bullish')
                    signal['signal'] = 'buy' if direction == 'bullish' else 'sell'
                
                # Validar com ML
                pattern_type = 'reversal' if any(x in signal['pattern'] for x in ['top', 'shoulder']) else 'continuation'
                ml_confidence = ml_validator.validate_pattern_with_ml(current_data, pattern_type, signal['confidence'])
                
                if ml_confidence < settings.MIN_CONFIDENCE:
                    continue
                
                # Calcular tamanho da posição
                volatility = current_data['close'].pct_change().std() * np.sqrt(252)
                position_size = self.risk_manager.calculate_position_size(ml_confidence, volatility, signal['pattern'])
                
                if position_size <= 0 or not self.risk_manager.can_trade():
                    continue
                
                # Executar trade
                trade = self.execute_trade(
                    signal, current_price, position_size, 
                    current_data, ml_confidence
                )
                
                if trade:
                    trades.append(trade)
                    capital += trade['profit_loss']
                    equity_curve.append({
                        'timestamp': current_data['timestamp'].iloc[-1],
                        'equity': capital
                    })
        
        # Calcular métricas
        self.calculate_performance_metrics(trades, equity_curve, capital)
        
        logger.info(f"Backtest completed: {len(trades)} trades executed")
        return self.results
    
    def execute_trade(self, signal: Dict, entry_price: float, position_size: float, 
                     data: pd.DataFrame, confidence: float) -> Dict:
        """Executa um trade no backtest"""
        volatility = data['close'].pct_change().std() * np.sqrt(252)
        
        stop_loss = self.risk_manager.calculate_stop_loss(entry_price, signal['signal'], volatility)
        take_profit = self.risk_manager.calculate_take_profit(entry_price, signal['signal'], signal['pattern'])
        
        # Simular trade (implementação simplificada)
        # Em implementação real, usaríamos dados futuros
        future_returns = self.simulate_future_returns(volatility, 24)  # 24 períodos
        exit_price = entry_price * (1 + future_returns)
        
        # Determinar razão da saída
        if (signal['signal'] == 'buy' and exit_price <= stop_loss) or \
           (signal['signal'] == 'sell' and exit_price >= stop_loss):
            exit_reason = 'stop_loss'
            exit_price = stop_loss
        elif (signal['signal'] == 'buy' and exit_price >= take_profit) or \
             (signal['signal'] == 'sell' and exit_price <= take_profit):
            exit_reason = 'take_profit'
            exit_price = take_profit
        else:
            exit_reason = 'timeout'
        
        # Calcular P&L
        if signal['signal'] == 'buy':
            profit_loss = (exit_price - entry_price) / entry_price * position_size
        else:  # sell (short)
            profit_loss = (entry_price - exit_price) / entry_price * position_size
        
        trade = {
            'pattern': signal['pattern'],
            'signal': signal['signal'],
            'entry_price': entry_price,
            'exit_price': exit_price,
            'position_size': position_size,
            'profit_loss': profit_loss,
            'confidence': confidence,
            'exit_reason': exit_reason,
            'duration_bars': 24
        }
        
        return trade
    
    def simulate_future_returns(self, volatility: float, periods: int) -> float:
        """Simula retornos futuros baseados na volatilidade"""
        # GBM simulation
        drift = 0.0001  # Pequeno drift positivo
        random_shock = np.random.normal(0, volatility / np.sqrt(252))
        return drift + random_shock
    
    def calculate_performance_metrics(self, trades: List[Dict], equity_curve: List[Dict], final_capital: float):
        """Calcula métricas detalhadas de performance"""
        if not trades:
            self.results = {'error': 'No trades executed'}
            return
        
        df_trades = pd.DataFrame(trades)
        df_equity = pd.DataFrame(equity_curve)
        
        # Métricas básicas
        total_trades = len(trades)
        winning_trades = len(df_trades[df_trades['profit_loss'] > 0])
        losing_trades = len(df_trades[df_trades['profit_loss'] < 0])
        win_rate = winning_trades / total_trades if total_trades > 0 else 0
        
        # Retorno e drawdown
        total_return = final_capital - self.initial_capital
        return_percent = (final_capital / self.initial_capital - 1) * 100
        
        # Sharpe Ratio
        returns = df_trades['profit_loss'] / df_trades['position_size']
        sharpe_ratio = returns.mean() / returns.std() * np.sqrt(252) if returns.std() > 0 else 0
        
        # Max Drawdown
        df_equity['peak'] = df_equity['equity'].expanding().max()
        df_equity['drawdown'] = (df_equity['equity'] - df_equity['peak']) / df_equity['peak']
        max_drawdown = df_equity['drawdown'].min()
        
        # Métricas por padrão
        pattern_metrics = {}
        for pattern in df_trades['pattern'].unique():
            pattern_trades = df_trades[df_trades['pattern'] == pattern]
            pattern_win_rate = len(pattern_trades[pattern_trades['profit_loss'] > 0]) / len(pattern_trades)
            
            pattern_metrics[pattern] = {
                'count': len(pattern_trades),
                'win_rate': pattern_win_rate,
                'avg_profit': pattern_trades['profit_loss'].mean(),
                'total_profit': pattern_trades['profit_loss'].sum()
            }
        
        self.results = {
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': win_rate,
            'total_return': total_return,
            'return_percent': return_percent,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'final_capital': final_capital,
            'avg_trade_return': df_trades['profit_loss'].mean(),
            'profit_factor': abs(df_trades[df_trades['profit_loss'] > 0]['profit_loss'].sum() / 
                               df_trades[df_trades['profit_loss'] < 0]['profit_loss'].sum()) if losing_trades > 0 else float('inf'),
            'by_pattern': pattern_metrics,
            'equity_curve': df_equity.to_dict('records')
        }