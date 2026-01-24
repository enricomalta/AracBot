# main.py
import logging
import argparse
from datetime import datetime, timedelta
import time

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
from news.news_sentiment_manager import NewsSentimentManager
from data.market_data_collector import AdvancedMarketDataCollector
from ml.prediction_tracker import PredictionTracker
from ml.advanced_features import AdvancedFeatureEngineer
from ml.feature_engineering import FeatureEngineer

class AdvancedBitcoinPatternTracker:
    def __init__(self):
        setup_logging(logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # Initialize components - compartilhar instância do database
        self.db = DatabaseManager()
        self.api_client = APIClient(db_manager=self.db)  # Passar db_manager
        self.pattern_bot = PatternRecognitionBot()
        self.ml_validator = PatternMLValidator()
        self.risk_manager = RiskManager()
        self.multi_tf_analyzer = MultiTimeframeAnalyzer(api_client=self.api_client)  # Passar api_client
        self.performance_analyzer = PerformanceAnalyzer(self.db)
        
        # Sentiment Analysis (with kill switch)
        if settings.SENTIMENT_ENABLED:
            self.sentiment_manager = NewsSentimentManager(database_manager=self.db)
            self.logger.info("Sentiment analysis ENABLED (RSS feeds: Google News, CoinDesk, Cointelegraph)")
        else:
            self.sentiment_manager = None
            self.logger.info("Sentiment analysis DISABLED (kill switch activated)")
        
        # ========== NOVOS COMPONENTES PARA MODO LIVE ==========
        self.market_collector = AdvancedMarketDataCollector(self.db)
        self.logger.info("Market data collector initialized")
        
        self.prediction_tracker = PredictionTracker(self.db)
        self.logger.info("Prediction tracker initialized")
        
        self.feature_engineer = AdvancedFeatureEngineer(self.db)
        self.logger.info("Advanced feature engineer initialized")
        
        # Trading state
        self.active_positions = []  # Lista de posições abertas
        self.capital = settings.INITIAL_CAPITAL
        
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
    
    def run_paper_trading(self, duration_hours: int = 1):
        """Executa paper trading (simulação) realista com dados históricos"""
        self.logger.info(f"Starting realistic paper trading simulation for {duration_hours} hours...")
        
        # Buscar dados históricos para simulação realista
        end_date = datetime.now()
        start_date = end_date - timedelta(hours=duration_hours + 24)  # +24h para buffer
        
        self.logger.info(f"Fetching historical data from {start_date} to {end_date}")
        historical_data = self.api_client.get_historical_data(
            settings.SYMBOL, '1h', start_date, end_date
        )
        
        if historical_data is None or len(historical_data) < 20:  # Reduzido de 100 para 20
            self.logger.error("Failed to fetch sufficient historical data for realistic simulation")
            return
        
        self.logger.info(f"Fetched {len(historical_data)} historical candles for simulation")
        
        capital = settings.INITIAL_CAPITAL
        trades = []
        active_trade = None  # Trade pendente
        simulation_index = 10  # Começar após dados suficientes para análise (reduzido de 50)
        
        print(f"Realistic paper trading simulation")
        print(f"Initial capital: ${capital:.2f}")
        print(f"Using {len(historical_data)} historical candles")
        
        self.logger.info(f"Starting realistic paper trading simulation")
        self.logger.info(f"Initial capital: ${capital:.2f}")
        logging.getLogger().handlers[0].flush()
        
        while simulation_index < len(historical_data) - 1:
            current_data = historical_data.iloc[:simulation_index + 1]  # Dados até agora
            
            # Verificar trade ativo
            if active_trade:
                current_price = historical_data.iloc[simulation_index]['close']
                
                # Verificar se atingiu stop loss ou take profit
                if active_trade['signal_type'] == 'buy':
                    if current_price <= active_trade['stop_loss']:
                        # Stop loss atingido
                        exit_price = active_trade['stop_loss']
                        if active_trade['entry_price'] != 0:
                            profit = (exit_price - active_trade['entry_price']) / active_trade['entry_price'] * active_trade['position_size']
                        else:
                            self.logger.error(f"Entry price is zero for trade: {active_trade}")
                            profit = 0
                        result = 'loss'
                    elif current_price >= active_trade['take_profit']:
                        # Take profit atingido
                        exit_price = active_trade['take_profit']
                        if active_trade['entry_price'] != 0:
                            profit = (exit_price - active_trade['entry_price']) / active_trade['entry_price'] * active_trade['position_size']
                        else:
                            self.logger.error(f"Entry price is zero for trade: {active_trade}")
                            profit = 0
                        result = 'win'
                    else:
                        # Trade ainda ativo
                        simulation_index += 1
                        continue
                else:  # sell
                    if current_price >= active_trade['stop_loss']:
                        # Stop loss atingido
                        exit_price = active_trade['stop_loss']
                        if active_trade['entry_price'] != 0:
                            profit = (active_trade['entry_price'] - exit_price) / active_trade['entry_price'] * active_trade['position_size']
                        else:
                            self.logger.error(f"Entry price is zero for trade: {active_trade}")
                            profit = 0
                        result = 'loss'
                    elif current_price <= active_trade['take_profit']:
                        # Take profit atingido
                        exit_price = active_trade['take_profit']
                        if active_trade['entry_price'] != 0:
                            profit = (active_trade['entry_price'] - exit_price) / active_trade['entry_price'] * active_trade['position_size']
                        else:
                            self.logger.error(f"Entry price is zero for trade: {active_trade}")
                            profit = 0
                        result = 'win'
                    else:
                        # Trade ainda ativo
                        simulation_index += 1
                        continue
                
                # Fechar trade
                capital += profit
                trade = {
                    'timestamp': str(historical_data.iloc[simulation_index]['timestamp']),
                    'pattern': active_trade['pattern'],
                    'signal_type': active_trade['signal_type'],
                    'entry_price': active_trade['entry_price'],
                    'exit_price': exit_price,
                    'position_size': active_trade['position_size'],
                    'profit': profit,
                    'result': result,
                    'duration_candles': simulation_index - active_trade['entry_index']
                }
                trades.append(trade)
                
                print(f"Closed trade: {active_trade['pattern']} {active_trade['signal_type']} "
                      f"entry ${active_trade['entry_price']:.2f}, exit ${exit_price:.2f}, "
                      f"profit ${profit:.2f}, capital now ${capital:.2f}")
                
                self.logger.info(f"Closed trade: {active_trade['pattern']} {active_trade['signal_type']} "
                                 f"entry ${active_trade['entry_price']:.2f}, exit ${exit_price:.2f}, "
                                 f"profit ${profit:.2f}, capital now ${capital:.2f}")
                logging.getLogger().handlers[0].flush()
                
                active_trade = None
                simulation_index += 1
                continue
            
            # Procurar novos sinais se não há trade ativo
            if len(current_data) >= 20:  # Mantém 20 para dados limitados
                signals = self.pattern_bot.analyze_market(current_data)
                
                if signals:
                    # Salvar sinais para análise
                    for s in signals:
                        signal_data = {
                            'timestamp': str(historical_data.iloc[simulation_index]['timestamp']),
                            'pattern': s['pattern'],
                            'confidence': s.get('confidence', 0),
                            'signal': s.get('signal', 'unknown'),
                            'price': s.get('price', historical_data.iloc[simulation_index]['close']),
                            'market_data': current_data.tail(10).to_dict()
                        }
                        self.db.save_signal_for_analysis(signal_data)
                
                # Tentar abrir trade com primeiro sinal válido
                for signal in signals:
                    if signal['confidence'] >= settings.MIN_CONFIDENCE:
                        # Atualizar capital no RiskManager
                        self.risk_manager.update_capital(capital)
                        
                        entry_price = historical_data.iloc[simulation_index]['close']
                        try:
                            position_size = self.risk_manager.calculate_position_size(
                                signal['confidence'], 0.02, signal['pattern']
                            )
                        except Exception as e:
                            self.logger.error(f"Erro ao calcular position_size: {str(e)}")
                            self.logger.error(f"Parâmetros: confidence={signal['confidence']}, risk=0.02, pattern={signal['pattern']}")
                            position_size = 0
                        
                        if position_size > 0:
                            stop_loss = self.risk_manager.calculate_stop_loss(
                                entry_price, signal['signal'], 0.02
                            )
                            take_profit = self.risk_manager.calculate_take_profit(
                                entry_price, signal['signal'], signal['pattern']
                            )
                            
                            # Abrir trade
                            active_trade = {
                                'pattern': signal['pattern'],
                                'signal_type': signal['signal'],
                                'entry_price': entry_price,
                                'stop_loss': stop_loss,
                                'take_profit': take_profit,
                                'position_size': position_size,
                                'entry_index': simulation_index
                            }
                            
                            print(f"Opened trade: {signal['pattern']} {signal['signal']} "
                                  f"at ${entry_price:.2f}, stop ${stop_loss:.2f}, target ${take_profit:.2f}")
                            
                            self.logger.info(f"Opened trade: {signal['pattern']} {signal['signal']} "
                                             f"at ${entry_price:.2f}, stop ${stop_loss:.2f}, target ${take_profit:.2f}")
                            logging.getLogger().handlers[0].flush()
                            
                            break  # Só 1 trade por vez
            
            simulation_index += 1
        
        # Fechar trade ativo se chegou ao fim
        if active_trade:
            exit_price = historical_data.iloc[-1]['close']
            if active_trade['signal_type'] == 'buy':
                if active_trade['entry_price'] != 0:
                    profit = (exit_price - active_trade['entry_price']) / active_trade['entry_price'] * active_trade['position_size']
                else:
                    self.logger.error(f"Entry price is zero for final trade: {active_trade}")
                    profit = 0
            else:
                if active_trade['entry_price'] != 0:
                    profit = (active_trade['entry_price'] - exit_price) / active_trade['entry_price'] * active_trade['position_size']
                else:
                    self.logger.error(f"Entry price is zero for final trade: {active_trade}")
                    profit = 0
            
            capital += profit
            result = 'win' if profit > 0 else 'loss'
            
            trade = {
                'timestamp': str(historical_data.iloc[-1]['timestamp']),
                'pattern': active_trade['pattern'],
                'signal_type': active_trade['signal_type'],
                'entry_price': active_trade['entry_price'],
                'exit_price': exit_price,
                'position_size': active_trade['position_size'],
                'profit': profit,
                'result': result,
                'duration_candles': len(historical_data) - 1 - active_trade['entry_index']
            }
            trades.append(trade)
            
            print(f"Closed final trade: {active_trade['pattern']} {active_trade['signal_type']} "
                  f"entry ${active_trade['entry_price']:.2f}, exit ${exit_price:.2f}, "
                  f"profit ${profit:.2f}, capital now ${capital:.2f}")
        
        # Resumo final
        winning_trades = [t for t in trades if t['result'] == 'win']
        total_profit = sum(t['profit'] for t in trades)
        win_rate = f"{len(winning_trades)/len(trades)*100:.1f}%" if trades else "0%"
        avg_duration = f"{sum(t['duration_candles'] for t in trades)/len(trades):.1f}" if trades else "0"
        
        summary = f"""
=== REALISTIC PAPER TRADING RESULTS ===
Total Trades: {len(trades)}
Winning Trades: {len(winning_trades)}
Win Rate: {win_rate}
Total Profit: ${total_profit:.2f}
Final Capital: ${capital:.2f}
Average Trade Duration: {avg_duration} candles
"""
        print(summary)
        self.logger.info(summary)
        logging.getLogger().handlers[0].flush()
        
    def retrain_ml_with_collected_data(self):
        """Retreina modelos ML com dados de sinais coletados"""
        self.logger.info("Retraining ML models with collected signal data...")
        
        # Buscar sinais coletados
        collected_signals = self.db.get_collected_signals()
        
        if collected_signals.empty:
            self.logger.warning("No collected signals found for retraining")
            return
        
        self.logger.info(f"Found {len(collected_signals)} collected signals for retraining")
        
        # Preparar dados para ML
        # Aqui você pode implementar lógica para criar labels (win/loss) baseados em performance futura
        # Por enquanto, apenas log
        for _, signal in collected_signals.iterrows():
            self.logger.info(f"Signal: {signal['pattern']} conf {signal['confidence']:.2f} at ${signal['price']:.2f}")
        
        # TODO: Implementar retreinamento real
        self.logger.info("ML retraining completed (placeholder)")
    
    def run_live_monitoring(self, duration_hours: int = 24):
        """Executa monitoramento ao vivo do mercado"""
        self.logger.info(f"Starting live monitoring for {duration_hours} hours...")
        
        end_time = datetime.now() + timedelta(hours=duration_hours)
        last_check = datetime.now() - timedelta(minutes=10)  # Forçar primeira verificação
        last_sentiment_check = datetime.now() - timedelta(minutes=60)  # Atualizar sentimento a cada hora
        current_market_sentiment = None
        
        # Rastrear sinais já detectados para evitar duplicatas
        detected_signals = set()  # Usar tupla (pattern, timestamp_key) como chave
        
        print(f"🚀 Starting Bitcoin Pattern Tracker - Live Monitoring")
        print(f"⏰ Duration: {duration_hours} hours (until {end_time.strftime('%Y-%m-%d %H:%M:%S')})")
        print(f"📊 Symbol: {settings.SYMBOL}")
        print(f"🔄 Check interval: {settings.CHECK_INTERVAL} seconds")
        
        # Status do sentiment analysis
        if settings.SENTIMENT_ENABLED:
            print(f"📰 Sentiment Analysis: ✅ ENABLED (will check news hourly)")
        else:
            print(f"📰 Sentiment Analysis: ❌ DISABLED (kill switch activated)")
        
        print("=" * 60)
        
        try:
            while datetime.now() < end_time:
                current_time = datetime.now()
                
                # Atualizar sentimento de mercado a cada hora (se habilitado)
                if settings.SENTIMENT_ENABLED and (current_time - last_sentiment_check).total_seconds() >= 3600:  # 1 hora
                    print(f"\n📰 Updating market sentiment...")
                    current_market_sentiment = self.sentiment_manager.get_current_market_sentiment(
                        hours=24, max_news=50
                    )
                    print(self.sentiment_manager.get_recent_news_summary())
                    last_sentiment_check = current_time
                
                # Verificar se é hora de fazer análise
                if (current_time - last_check).total_seconds() >= settings.CHECK_INTERVAL:
                    print(f"\n🔍 [{current_time.strftime('%H:%M:%S')}] Checking for patterns...")
                    
                    # Buscar apenas dados recentes do mercado (últimas 48 horas)
                    # Focar em dados frescos para detectar padrões atuais
                    print(f"  📡 Fetching fresh market data from API...")
                    historical_data = self.api_client.fetch_klines(
                        settings.SYMBOL, '1h',
                        start_time=(current_time - timedelta(hours=48)).isoformat(),  # Apenas 48h recentes
                        end_time=current_time.isoformat(),
                        limit=50  # Suficiente para análise de padrões recentes
                    )
                    
                    if historical_data is not None and len(historical_data) >= 20:
                        # Log para verificar se os dados estão atualizados
                        latest_price = historical_data.iloc[-1]['close']
                        latest_timestamp = historical_data.iloc[-1]['timestamp']
                        print(f"  📊 Latest data: {latest_timestamp} | Price: ${latest_price:.2f}")
                        
                        # Analisar padrões apenas nos dados mais recentes (últimas 24 velas = 24h)
                        # Isso garante que estamos analisando movimento de mercado atual
                        recent_data = historical_data.tail(24)  # Focar nas últimas 24 horas
                        print(f"  📊 Analyzing {len(recent_data)} recent candles (last 24h)")
                        
                        signals = self.pattern_bot.analyze_market(recent_data)
                        print(f"  🔍 Pattern analysis completed, checking {len(signals)} signals")
                        
                        if signals:
                            print(f"📈 Found {len(signals)} potential signals in recent data:")
                            for sig in signals[:3]:  # Mostrar primeiros 3 sinais para debug
                                print(f"    - {sig.get('pattern', 'unknown')} ({sig.get('signal', 'unknown')}) conf {sig.get('confidence', 0):.2f} at index {sig.get('index', -1)}")
                            
                            # Filtrar sinais válidos e verificar se são realmente novos
                            valid_signals = []
                            for signal in signals:
                                confidence = signal.get('confidence', 0)
                                if confidence >= settings.MIN_CONFIDENCE:
                                    # Verificar se o sinal é realmente recente (nos últimos dados)
                                    signal_index = signal.get('index', 0)
                                    if signal_index >= len(recent_data) - 5:  # Apenas sinais das últimas 5 velas
                                        pattern = signal.get('pattern', 'unknown')
                                        
                                        # Criar chave única baseada no padrão e timestamp exato da vela
                                        try:
                                            signal_timestamp = recent_data.iloc[signal_index]['timestamp']
                                            signal_key = (pattern, signal_timestamp.strftime('%Y-%m-%d %H:%M'))
                                            
                                            # Verificar se já detectamos este sinal específico
                                            if signal_key not in detected_signals:
                                                valid_signals.append(signal)
                                                detected_signals.add(signal_key)
                                                print(f"    🔍 Signal timestamp: {signal_timestamp}")
                                        except (IndexError, AttributeError) as e:
                                            print(f"    ⚠️ Error processing signal timestamp: {e}")
                                            # Fallback se não conseguir timestamp
                                            current_minute = current_time.replace(second=0, microsecond=0)
                                            signal_key = (pattern, current_minute.strftime('%Y-%m-%d %H:%M'))
                                            if signal_key not in detected_signals:
                                                valid_signals.append(signal)
                                                detected_signals.add(signal_key)
                            
                            if valid_signals:
                                for signal in valid_signals:
                                    confidence = signal.get('confidence', 0)
                                    pattern = signal.get('pattern', 'unknown')
                                    signal_type = signal.get('signal', 'unknown')
                                    
                                    print(f"  ✅ FRESH {pattern.upper()} signal ({signal_type}) - Confidence: {confidence:.2f}")
                                    
                                    # Salvar sinal para análise
                                    signal_data = {
                                        'timestamp': str(current_time),
                                        'pattern': pattern,
                                        'confidence': confidence,
                                        'signal': signal_type,
                                        'price': recent_data.iloc[-1]['close'],
                                        'market_data': recent_data.tail(10).to_dict()
                                    }
                                    self.db.save_signal_for_analysis(signal_data)
                                    
                                    # Executar trade ao vivo se não há posições abertas
                                    if not self.active_positions and settings.API_KEY and settings.API_SECRET:
                                        # Verificar sentimento antes de executar trade (se habilitado)
                                        if settings.SENTIMENT_ENABLED and self.sentiment_manager:
                                            trade_decision = self.sentiment_manager.should_trade(
                                                signal_type=signal_type,
                                                current_sentiment=current_market_sentiment
                                            )
                                            
                                            if trade_decision['should_trade']:
                                                # Ajustar confiança baseado no sentimento
                                                adjusted_confidence = min(1.0, confidence + trade_decision['confidence_adjustment'])
                                                print(f"  💡 Sentiment analysis: {trade_decision['reason']}")
                                                print(f"  📊 Adjusted confidence: {confidence:.2f} -> {adjusted_confidence:.2f}")
                                                
                                                self._execute_live_trade(signal, recent_data.iloc[-1]['close'], adjusted_confidence)
                                            else:
                                                print(f"  🚫 Trade blocked by sentiment analysis: {trade_decision['reason']}")
                                                self.logger.info(f"Trade blocked by sentiment: {trade_decision['reason']}")
                                        else:
                                            # Sentiment desabilitado - executar trade normalmente
                                            self._execute_live_trade(signal, recent_data.iloc[-1]['close'], confidence)
                                    elif not settings.API_KEY:
                                        print("  ⚠️  API keys not configured - running in monitoring mode only")
                                    
                                    self.logger.info(f"Valid signal detected: {pattern} ({signal_type}) conf {confidence:.2f}")
                            else:
                                print("  ❌ No fresh signals detected in recent market data")
                        else:
                            print("  📊 No patterns detected in recent market data")
                    else:
                        if historical_data is not None:
                            print(f"  ⚠️  Insufficient data for analysis ({len(historical_data)} records, need 20+)")
                        else:
                            print("  ❌ No market data available")
                    
                    # Verificar posições abertas para possível fechamento
                    self._check_and_close_positions(recent_data.iloc[-1]['close'])
                    
                    last_check = current_time
                
                # Pequena pausa para não sobrecarregar CPU
                time.sleep(1)
                
                # Verificar se ainda há tempo
                if datetime.now() >= end_time:
                    break
                    
        except KeyboardInterrupt:
            print("\n⏹️  Monitoring interrupted by user")
            self.logger.info("Live monitoring interrupted by user")
        except Exception as e:
            print(f"\n❌ Error during live monitoring: {str(e)}")
            self.logger.error(f"Live monitoring failed: {str(e)}")
        
        print(f"\n🏁 Live monitoring completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.logger.info("Live monitoring completed")
    
    def run_backtest(self, days: int = 30, start_date_str: str = None, end_date_str: str = None):
        """Executa backtest com dados históricos"""
        self.logger.info(f"Running backtest...")
        
        if start_date_str and end_date_str:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d %H:%M:%S')
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d %H:%M:%S')
        else:
            end_date = datetime.now().replace(minute=0, second=0, microsecond=0)
            start_date = (end_date - timedelta(days=days)).replace(minute=0, second=0, microsecond=0)
        
        print(f"Fetching data from {start_date} to {end_date}")
        historical_data = self.api_client.get_historical_data(
            settings.SYMBOL, '1h', start_date, end_date
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
    
    def _execute_live_trade(self, signal: dict, current_price: float, confidence: float):
        """Executa um trade ao vivo baseado no sinal"""
        try:
            # Calcular tamanho da posição
            self.risk_manager.update_capital(self.capital)
            position_size = self.risk_manager.calculate_position_size(
                confidence, 0.02, signal['pattern']
            )
            
            if position_size <= 0:
                print(f"  ❌ Position size too small: ${position_size:.2f}")
                return
            
            # Calcular stop loss e take profit
            stop_loss = self.risk_manager.calculate_stop_loss(current_price, signal['signal'], 0.02)
            take_profit = self.risk_manager.calculate_take_profit(current_price, signal['signal'], signal['pattern'])
            
            # Para ordens limit, usar preço ligeiramente melhor
            if signal['signal'] == 'buy':
                order_price = current_price * 0.999  # 0.1% melhor
                quantity = position_size / order_price
            else:  # sell (short)
                order_price = current_price * 1.001  # 0.1% pior
                quantity = position_size / order_price
            
            # Arredondar quantidade para precisão do BTC (6 casas decimais)
            quantity = round(quantity, 6)
            
            print(f"  📈 Executing {signal['signal'].upper()} order: {quantity:.6f} BTC at ${order_price:.2f}")
            print(f"  🎯 Stop Loss: ${stop_loss:.2f}, Take Profit: ${take_profit:.2f}")
            
            # Colocar ordem limit
            order_result = self.api_client.place_order(
                settings.SYMBOL, 
                signal['signal'], 
                'LIMIT', 
                quantity, 
                price=order_price
            )
            
            if order_result and 'orderId' in order_result:
                # Registrar posição aberta
                position = {
                    'order_id': order_result['orderId'],
                    'pattern': signal['pattern'],
                    'signal': signal['signal'],
                    'entry_price': order_price,
                    'quantity': quantity,
                    'stop_loss': stop_loss,
                    'take_profit': take_profit,
                    'confidence': confidence,
                    'timestamp': datetime.now(),
                    'status': 'pending'  # aguardando execução
                }
                self.active_positions.append(position)
                print(f"  ✅ Order placed successfully! Order ID: {order_result['orderId']}")
            else:
                print("  ❌ Failed to place order")
                
        except Exception as e:
            print(f"  ❌ Error executing trade: {str(e)}")
            self.logger.error(f"Trade execution failed: {str(e)}")
    
    def _check_and_close_positions(self, current_price: float):
        """Verifica posições abertas e fecha se necessário"""
        positions_to_remove = []
        
        for position in self.active_positions:
            try:
                # Verificar se atingiu stop loss ou take profit
                if position['signal'] == 'buy':
                    if current_price <= position['stop_loss']:
                        # Stop loss atingido
                        self._close_position(position, current_price, 'stop_loss')
                        positions_to_remove.append(position)
                    elif current_price >= position['take_profit']:
                        # Take profit atingido
                        self._close_position(position, current_price, 'take_profit')
                        positions_to_remove.append(position)
                else:  # sell
                    if current_price >= position['stop_loss']:
                        # Stop loss atingido (preço subiu)
                        self._close_position(position, current_price, 'stop_loss')
                        positions_to_remove.append(position)
                    elif current_price <= position['take_profit']:
                        # Take profit atingido (preço caiu)
                        self._close_position(position, current_price, 'take_profit')
                        positions_to_remove.append(position)
                        
            except Exception as e:
                self.logger.error(f"Error checking position: {str(e)}")
        
        # Remover posições fechadas
        for pos in positions_to_remove:
            self.active_positions.remove(pos)

    def _close_position(self, position: dict, exit_price: float, reason: str):
        """Fecha uma posição"""
        try:
            # Calcular P&L
            if position['signal'] == 'buy':
                profit_loss = (exit_price - position['entry_price']) / position['entry_price'] * position['quantity'] * position['entry_price']
            else:  # sell
                profit_loss = (position['entry_price'] - exit_price) / position['entry_price'] * position['quantity'] * position['entry_price']
            
            self.capital += profit_loss
            
            print(f"  🔒 Closed {position['signal'].upper()} position: Entry ${position['entry_price']:.2f}, Exit ${exit_price:.2f}")
            print(f"  💰 P&L: ${profit_loss:.2f}, New Capital: ${self.capital:.2f}")
            
            # Salvar no banco para análise
            trade_data = {
                'timestamp': str(position['timestamp']),
                'pattern': position['pattern'],
                'signal_type': position['signal'],
                'entry_price': position['entry_price'],
                'exit_price': exit_price,
                'position_size': position['quantity'] * position['entry_price'],
                'profit': profit_loss,
                'result': 'win' if profit_loss > 0 else 'loss',
                'exit_reason': reason
            }
            self.db.save_trade_result(trade_data)
            
        except Exception as e:
            self.logger.error(f"Error closing position: {str(e)}")

    def run_live_with_predictions(self, collect_days: int = 30, prediction_horizon: str = '24h', 
                                  update_interval: int = 60):
        """Executa modo LIVE com geração de previsões estruturadas"""
        self.logger.info(f"[LIVE] Starting LIVE MODE with Predictions")
        self.logger.info(f"Collection days: {collect_days}")
        self.logger.info(f"Prediction horizon: {prediction_horizon}")
        self.logger.info(f"Update interval: {update_interval} minutes")
        
        # Carregar histórico inicial
        if collect_days > 0:
            self.logger.info(f"\n[DATA] Loading {collect_days} days of historical data...")
            end_date = datetime.now()
            start_date = end_date - timedelta(days=collect_days)
            
            historical_data = self.api_client.get_historical_data(
                settings.SYMBOL, '1h', start_date, end_date
            )
            
            if historical_data is not None and len(historical_data) > 20:
                self.logger.info(f"[OK] Loaded {len(historical_data)} historical candles")
                self.logger.info(f"[ML] Training ML models with historical data...")
                self.ml_validator.train_models(historical_data)
                self.ml_validator.save_models()
                self.logger.info(f"[OK] ML models trained and saved")
            else:
                self.logger.warning("Could not load sufficient historical data")
        
        # Loop principal
        cycle = 0
        try:
            while True:
                cycle += 1
                timestamp = datetime.now()
                
                self.logger.info(f"\n{'='*70}")
                self.logger.info(f"Cycle #{cycle} - {timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
                self.logger.info(f"{'='*70}")
                
                try:
                    # ========== 1. Obter preço atual ==========
                    current_klines = self.api_client.fetch_klines(settings.SYMBOL, '1m', limit=1)
                    
                    if current_klines is None or len(current_klines) == 0:
                        self.logger.warning("Could not fetch current price, retrying in 5 minutes...")
                        time.sleep(300)
                        continue
                    
                    current_price = float(current_klines['close'].iloc[-1])
                    self.logger.info(f"[PRICE] Current price: ${current_price:,.2f}")
                    
                    # ========== 2. Coletar dados avançados ==========
                    self.logger.info(f"\n[DATA] Collecting advanced market data...")
                    market_data = self.market_collector.save_all_market_data(settings.SYMBOL)
                    self.logger.info(f"[OK] Collected {len(market_data['sources'])} data sources")
                    
                    # Extrair valores
                    sentiment_score = 0.0
                    oi_ratio = 1.0
                    funding_rate = 0.0
                    
                    if 'open_interest' in market_data['sources'] and market_data['sources']['open_interest']:
                        oi_ratio = market_data['sources']['open_interest'].get('oi_current', 1.0)
                    
                    if 'funding_rate' in market_data['sources'] and market_data['sources']['funding_rate']:
                        funding_rate = market_data['sources']['funding_rate'].get('funding_rate', 0.0)
                    
                    # Sentimento
                    if self.sentiment_manager:
                        try:
                            sentiment_result = self.sentiment_manager.get_current_market_sentiment(
                                hours=24, max_news=20
                            )
                            sentiment_score = sentiment_result.get('score', 0.0)
                            self.logger.info(f"[SENT] Sentiment: {sentiment_result['label']} "
                                           f"(score: {sentiment_score:.2f})")
                        except Exception as e:
                            self.logger.warning(f"Could not fetch sentiment: {e}")
                    
                    # ========== 3. Criar features ==========
                    self.logger.info(f"\n[FEAT] Creating technical features...")
                    
                    hist_data = self.api_client.fetch_klines(settings.SYMBOL, '1h', limit=100)
                    features_dict = {}
                    
                    if hist_data is not None and len(hist_data) > 20:
                        fe = FeatureEngineer()
                        features_df = fe.create_technical_features(hist_data)
                        
                        if not features_df.empty:
                            latest_row = features_df.iloc[-1]
                            features_dict = {
                                'rsi_14': float(latest_row.get('rsi_14', 0)),
                                'rsi_21': float(latest_row.get('rsi_21', 0)),
                                'macd': float(latest_row.get('macd', 0)),
                                'macd_hist': float(latest_row.get('macd_hist', 0)),
                                'bb_position': float(latest_row.get('bb_position', 0)),
                                'atr': float(latest_row.get('atr', 0)),
                                'adx': float(latest_row.get('adx', 0)),
                                'obv': float(latest_row.get('obv', 0)),
                                'volatility_10': float(latest_row.get('volatility_10', 0)),
                                'volume_ratio': float(latest_row.get('volume_ratio', 0)),
                                'returns_5': float(latest_row.get('returns_5', 0)),
                                'returns_10': float(latest_row.get('returns_10', 0)),
                                'sentiment_score': sentiment_score,
                                'oi_ratio': oi_ratio,
                                'funding_rate': funding_rate
                            }
                            self.logger.info(f"[OK] Created {len(features_dict)} features")
                    
                    # ========== 4. Gerar previsões ==========
                    self.logger.info(f"\n[PRED] Generating predictions...\n")
                    
                    for horizon in [prediction_horizon]:
                        try:
                            prediction = self._predict_direction(current_price, features_dict, sentiment_score)
                            
                            if prediction and features_dict:
                                pred_id = self.prediction_tracker.create_prediction(
                                    timeframe=horizon,
                                    prediction_type='direction',
                                    predicted_direction=prediction['direction'],
                                    target_price=prediction['target_price'],
                                    confidence=prediction['confidence'],
                                    model_type='ensemble',
                                    features_dict=features_dict,
                                    sentiment_score=sentiment_score,
                                    oi_ratio=oi_ratio,
                                    funding_rate=funding_rate
                                )
                                
                                direction_symbol = "UP" if prediction['direction'] == 'up' else "DOWN"
                                self.logger.info(
                                    f"[{direction_symbol}] [{horizon:5s}] {prediction['direction'].upper():8s} -> "
                                    f"${prediction['target_price']:,.2f} ({prediction['confidence']:.0%} conf) [ID: {pred_id}]"
                                )
                        
                        except Exception as e:
                            self.logger.error(f"Error generating prediction for {horizon}: {e}")
                    
                    # ========== 5. Validar previsões expiradas ==========
                    self.logger.info(f"\n[VAL] Validating expired predictions...")
                    
                    pending = self.prediction_tracker.get_pending_predictions()
                    if pending:
                        self.logger.info(f"Found {len(pending)} predictions to validate")
                        
                        for pred in pending:
                            try:
                                actual_direction = 'up' if current_price > pred['target_price'] else 'down'
                                error_pct = abs(current_price - pred['target_price']) / pred['target_price'] * 100 if pred['target_price'] > 0 else 0
                                
                                self.prediction_tracker.validate_prediction(
                                    prediction_id=pred['id'],
                                    actual_direction=actual_direction,
                                    actual_price=current_price,
                                    error_percent=error_pct
                                )
                            except Exception as e:
                                self.logger.error(f"Error validating prediction #{pred['id']}: {e}")
                    
                    # ========== 6. Relatório diário ==========
                    if cycle % 24 == 0:
                        self.logger.info(f"\n{'='*70}")
                        self.logger.info(f"[REPORT] DAILY PREDICTION REPORT")
                        self.logger.info(f"{'='*70}")
                        try:
                            self.prediction_tracker.print_accuracy_report()
                        except Exception as e:
                            self.logger.error(f"Error printing report: {e}")
                    
                    # ========== Aguardar próximo ciclo ==========
                    self.logger.info(f"\n[WAIT] Next update in {update_interval} minutes...")
                    time.sleep(update_interval * 60)
                    
                except KeyboardInterrupt:
                    self.logger.info("\n[STOP] Live mode interrupted by user")
                    break
                except Exception as e:
                    self.logger.error(f"Error in cycle: {e}", exc_info=True)
                    self.logger.info("Retrying in 5 minutes...")
                    time.sleep(300)
        
        except KeyboardInterrupt:
            self.logger.info("\n[STOP] Live mode stopped")
        except Exception as e:
            self.logger.error(f"Fatal error in live mode: {e}", exc_info=True)
    
    def _predict_direction(self, current_price: float, features: dict, sentiment: float) -> dict:
        """Prediz direção baseada em padrões e ML"""
        try:
            direction = 'sideways'
            confidence = 0.5
            target_price = current_price
            
            # Extrat features
            rsi = features.get('rsi_14', 50)
            macd_hist = features.get('macd_hist', 0)
            bb_pos = features.get('bb_position', 0.5)
            
            signals = []
            
            # RSI signal
            if rsi < 30:
                signals.append(('up', 0.7))
            elif rsi > 70:
                signals.append(('down', 0.7))
            
            # MACD signal
            if macd_hist > 0:
                signals.append(('up', 0.6))
            elif macd_hist < 0:
                signals.append(('down', 0.6))
            
            # Bollinger Bands signal
            if bb_pos < 0.2:
                signals.append(('up', 0.5))
            elif bb_pos > 0.8:
                signals.append(('down', 0.5))
            
            # Sentiment signal
            if sentiment > 0.3:
                signals.append(('up', 0.5))
            elif sentiment < -0.3:
                signals.append(('down', 0.5))
            
            # Aggregate signals
            if signals:
                up_signals = sum(conf for d, conf in signals if d == 'up')
                down_signals = sum(conf for d, conf in signals if d == 'down')
                
                if up_signals > down_signals:
                    direction = 'up'
                    confidence = min(up_signals / len(signals), 0.95)
                    target_price = current_price * 1.01
                elif down_signals > up_signals:
                    direction = 'down'
                    confidence = min(down_signals / len(signals), 0.95)
                    target_price = current_price * 0.99
                else:
                    direction = 'sideways'
                    confidence = 0.5
                    target_price = current_price
            
            return {
                'direction': direction,
                'target_price': target_price,
                'confidence': max(confidence, 0.5)
            }
        
        except Exception as e:
            self.logger.error(f"Error in prediction: {e}")
            return {
                'direction': 'sideways',
                'target_price': current_price,
                'confidence': 0.5
            }

def main():
    parser = argparse.ArgumentParser(description='Advanced Bitcoin Pattern Tracker')
    parser.add_argument('--mode', choices=['live', 'backtest', 'report', 'paper', 'retrain'], 
                       default='live', help='Execution mode')
    parser.add_argument('--duration', type=int, default=24, 
                       help='Duration in hours for live monitoring')
    parser.add_argument('--backtest-days', type=int, default=30,
                       help='Number of days for backtest')
    parser.add_argument('--start-date', type=str, 
                       help='Start date for backtest (YYYY-MM-DD HH:MM:SS)')
    parser.add_argument('--end-date', type=str,
                       help='End date for backtest (YYYY-MM-DD HH:MM:SS)')
    
    # ========== NOVOS ARGUMENTOS PARA MODO LIVE COM PREVISÕES ==========
    parser.add_argument('--collect-days', type=int, default=30,
                       help='Days of historical data to collect (default: 30)')
    parser.add_argument('--prediction-horizon', type=str, default='24h',
                       choices=['1h', '4h', '24h'],
                       help='Primary prediction horizon (default: 24h)')
    parser.add_argument('--update-interval', type=int, default=60,
                       help='Update interval in minutes (default: 60)')
    
    args = parser.parse_args()
    
    tracker = AdvancedBitcoinPatternTracker()
    
    try:
        if args.mode == 'live':
            # Novo modo: Live com previsões
            tracker.run_live_with_predictions(
                collect_days=args.collect_days,
                prediction_horizon=args.prediction_horizon,
                update_interval=args.update_interval
            )
        elif args.mode == 'backtest':
            tracker.run_backtest(args.backtest_days, args.start_date, args.end_date)
        elif args.mode == 'report':
            tracker.show_performance_report()
        elif args.mode == 'paper':
            tracker.run_paper_trading(args.duration)
        elif args.mode == 'retrain':
            tracker.retrain_ml_with_collected_data()
    
    except KeyboardInterrupt:
        tracker.logger.info("Execution interrupted by user")
    except Exception as e:
        tracker.logger.error(f"Execution failed: {e}")

if __name__ == "__main__":
    main()