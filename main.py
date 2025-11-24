# main.py
import logging
import argparse
from datetime import datetime, timedelta

from config.settings import settings
from data.database import DatabaseManager
from data.api_client import APIClient
from patterns import PatternRecognitionBot
from ml.validator import PatternMLValidator
from risk.risk_manager import RiskManager
from analysis.multi_timeframe import MultiTimeframeAnalyzer
from analysis.backtester import Backtester
from analysis.performance import PerformanceAnalyzer
from utils.helpers import setup_logging

class AdvancedBitcoinPatternTracker:
    def __init__(self):
        setup_logging(logging.WARNING)
        self.logger = logging.getLogger(__name__)
        
        # Initialize components
        self.db = DatabaseManager()
        self.api_client = APIClient()
        self.pattern_bot = PatternRecognitionBot()
        self.ml_validator = PatternMLValidator()
        self.risk_manager = RiskManager()
        self.multi_tf_analyzer = MultiTimeframeAnalyzer()
        self.performance_analyzer = PerformanceAnalyzer(self.db)
        
        # Load ML models
        self._load_ml_models()
    
    def _load_ml_models(self):
        """Carrega modelos ML ou treina novos se necessário"""
        if not self.ml_validator.load_models():
            self.logger.info("Training new ML models...")
            historical_data = self.api_client.fetch_klines(
                settings.SYMBOL, '1h', limit=1000
            )
            if historical_data is not None:
                self.ml_validator.train_models(historical_data)
                self.ml_validator.save_models()
    
    def run_live_monitoring(self, duration_hours: int = 24):
        """Executa monitoramento em tempo real"""
        self.logger.info(f"Starting live monitoring for {duration_hours} hours...")
        
        # Implementation would go here
        # Similar to previous implementation but using modular components
        pass
    
    def run_backtest(self, days: int = 30):
        """Executa backtest com dados históricos"""
        self.logger.info(f"Running backtest for {days} days...")
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        print(f"Fetching data from {start_date} to {end_date}")
        historical_data = self.api_client.fetch_klines(
            settings.SYMBOL, '1h', 
            start_time=start_date,
            end_time=end_date,
            limit=days*24
        )
        
        print(f"Fetched {len(historical_data) if historical_data is not None else 0} data points")
        
        if historical_data is not None:
            backtester = Backtester()
            results = backtester.run_backtest(historical_data)
            
            if 'error' in results:
                print(f"Backtest Error: {results['error']}")
                return None
            
            print("=== BACKTEST RESULTS ===")
            print(f"Total Trades: {results['total_trades']}")
            print(f"Winning Trades: {results['winning_trades']}")
            print(f"Losing Trades: {results['losing_trades']}")
            print(f"Win Rate: {results['win_rate']:.2%}")
            print(f"Total Return: ${results['total_return']:.2f}")
            print(f"Return %: {results['return_percent']:.2f}%")
            print(f"Sharpe Ratio: {results['sharpe_ratio']:.2f}")
            print(f"Max Drawdown: {results['max_drawdown']:.2f}%")
            print(f"Profit Factor: {results['profit_factor']:.2f}")
            print(f"Average Trade Return: ${results['avg_trade_return']:.2f}")
            print(f"Final Capital: ${results['final_capital']:.2f}")
            
            print("\n=== PERFORMANCE BY PATTERN ===")
            for pattern, metrics in results['by_pattern'].items():
                print(f"{pattern}:")
                print(f"  Count: {metrics['count']}")
                print(f"  Win Rate: {metrics['win_rate']:.2%}")
                print(f"  Avg Profit: ${metrics['avg_profit']:.2f}")
                print(f"  Total Profit: ${metrics['total_profit']:.2f}")
            
            print("========================")
            
            return results
        else:
            self.logger.error("Failed to fetch historical data for backtest")
            return None
    
    def show_performance_report(self):
        """Mostra relatório de performance"""
        report = self.performance_analyzer.generate_performance_report()
        print(report)
        
        # Generate charts
        self.performance_analyzer.plot_performance_charts()

def main():
    parser = argparse.ArgumentParser(description='Advanced Bitcoin Pattern Tracker')
    parser.add_argument('--mode', choices=['live', 'backtest', 'report'], 
                       default='live', help='Execution mode')
    parser.add_argument('--duration', type=int, default=24, 
                       help='Duration in hours for live monitoring')
    parser.add_argument('--backtest-days', type=int, default=30,
                       help='Number of days for backtest')
    
    args = parser.parse_args()
    
    tracker = AdvancedBitcoinPatternTracker()
    
    try:
        if args.mode == 'live':
            tracker.run_live_monitoring(args.duration)
        elif args.mode == 'backtest':
            tracker.run_backtest(args.backtest_days)
        elif args.mode == 'report':
            tracker.show_performance_report()
    
    except KeyboardInterrupt:
        tracker.logger.info("Execution interrupted by user")
    except Exception as e:
        tracker.logger.error(f"Execution failed: {e}")

if __name__ == "__main__":
    main()