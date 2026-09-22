# data/database.py
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import logging
from config.settings import settings

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self, db_path=settings.DB_PATH):
        self.db_path = db_path
        self.setup_database()
    
    def setup_database(self):
        """Configura o banco de dados com todas as tabelas necessárias"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Tabela para padrões detectados
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS patterns_detected (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME,
                pattern_name TEXT,
                signal_type TEXT,
                confidence REAL,
                ml_confidence REAL,
                combined_confidence REAL,
                price_detection REAL,
                position_size REAL,
                prediction TEXT,
                timeframe TEXT,
                status TEXT DEFAULT 'open',
                result TEXT,
                profit_loss REAL,
                duration_minutes INTEGER,
                exit_reason TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Tabela para histórico de preços
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS price_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME,
                symbol TEXT,
                timeframe TEXT,
                open REAL,
                high REAL,
                low REAL,
                close REAL,
                volume REAL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Tabela para métricas de performance
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS performance_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME,
                total_patterns INTEGER,
                success_rate REAL,
                avg_profit_loss REAL,
                total_return REAL,
                sharpe_ratio REAL,
                max_drawdown REAL
            )
        ''')
        
        # Tabela para sentimento agregado de notícias
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS news_sentiment (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME,
                score REAL,
                label TEXT,
                confidence REAL,
                news_count INTEGER,
                positive_count INTEGER,
                negative_count INTEGER,
                neutral_count INTEGER,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Tabela para notícias individuais
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS news_articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME,
                title TEXT,
                source TEXT,
                sentiment_score REAL,
                sentiment_label TEXT,
                url TEXT UNIQUE,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Receitas de pipeline ML (hash dos passos/decisões de configuração)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ml_recipe_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                recipe_hash TEXT UNIQUE,
                symbol TEXT,
                timeframe TEXT,
                horizon TEXT,
                config_json TEXT,
                total_predictions INTEGER,
                accuracy REAL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Previsões geradas por uma receita para análise de acertos/erros
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ml_recipe_predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER,
                timestamp DATETIME,
                predicted_direction TEXT,
                actual_direction TEXT,
                confidence REAL,
                was_correct INTEGER,
                decision_hash TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (run_id) REFERENCES ml_recipe_runs(id)
            )
        ''')

        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_ml_recipe_predictions_run_id
            ON ml_recipe_predictions(run_id)
        ''')

        # Tabela para sinais coletados (usada no retrain)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS collected_signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME,
                pattern TEXT,
                confidence REAL,
                signal TEXT,
                price REAL,
                market_data TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Evita duplicata exata do mesmo sinal no mesmo timestamp
        cursor.execute('''
            CREATE UNIQUE INDEX IF NOT EXISTS idx_collected_signals_unique
            ON collected_signals(timestamp, pattern, signal)
        ''')
        
        # Índice para evitar duplicatas por URL
        cursor.execute('''
            CREATE UNIQUE INDEX IF NOT EXISTS idx_news_url ON news_articles(url)
        ''')
        
        # ========== NOVAS TABELAS PARA DADOS AVANÇADOS ==========
        
        # Open Interest
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS open_interest (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME,
                symbol TEXT,
                timeframe TEXT,
                oi_current REAL,
                oi_long REAL,
                oi_short REAL,
                oi_ratio REAL,
                change_percent REAL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Funding Rate
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS funding_rates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME,
                symbol TEXT,
                funding_rate REAL,
                mark_price REAL,
                index_price REAL,
                estimated_settle_time INTEGER,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Liquidações
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS liquidations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME,
                symbol TEXT,
                side TEXT,
                price REAL,
                quantity REAL,
                usd_value REAL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Fluxo de Exchange
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS exchange_flow (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME,
                symbol TEXT,
                exchange TEXT,
                direction TEXT,
                quantity REAL,
                usd_value REAL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Volatilidade Implícita
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS implied_volatility (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME,
                symbol TEXT,
                iv_rank REAL,
                iv_percentile REAL,
                volatility REAL,
                source TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Dominância do Mercado
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS market_dominance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME,
                btc_dominance REAL,
                eth_dominance REAL,
                altcoin_dominance REAL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Previsões Estruturadas
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME,
                timeframe TEXT,
                prediction_type TEXT,
                predicted_direction TEXT,
                target_price REAL,
                confidence REAL,
                model_type TEXT,
                features_used TEXT,
                sentiment_score REAL,
                oi_ratio REAL,
                funding_rate REAL,
                additional_context TEXT,
                
                actual_direction TEXT,
                actual_price REAL,
                was_correct INTEGER,
                profit_loss REAL,
                error_percent REAL,
                
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                resolved_at DATETIME
            )
        ''')
        
        # Eventos Históricos
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS historical_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date DATETIME,
                event_name TEXT,
                category TEXT,
                description TEXT,
                price_before REAL,
                price_1h_after REAL,
                price_24h_after REAL,
                price_7d_after REAL,
                volatility_change REAL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Atividade de Whales
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS whale_activity (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME,
                address TEXT,
                transaction_hash TEXT,
                direction TEXT,
                quantity REAL,
                usd_value REAL,
                from_exchange INTEGER,
                to_exchange INTEGER,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Order Book Snapshot
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS order_book_snapshot (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME,
                symbol TEXT,
                bid_price REAL,
                bid_size REAL,
                ask_price REAL,
                ask_size REAL,
                bid_ask_ratio REAL,
                total_bid_volume REAL,
                total_ask_volume REAL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Correlações Macro
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS macro_correlations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME,
                btc_close REAL,
                gold_close REAL,
                sp500_close REAL,
                dxy_close REAL,
                vix_close REAL,
                yield_10y REAL,
                yield_2y REAL,
                correlation_gold REAL,
                correlation_sp500 REAL,
                correlation_dxy REAL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("Database setup completed - All tables created")
    
    def get_connection(self):
        """Retorna conexão com o banco de dados"""
        return sqlite3.connect(self.db_path)
    
    def save_pattern(self, pattern_data: dict) -> int:
        """Salva um padrão detectado no banco de dados"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO patterns_detected 
            (timestamp, pattern_name, signal_type, confidence, ml_confidence,
             combined_confidence, price_detection, position_size, prediction, timeframe)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            pattern_data.get('timestamp', datetime.now()),
            pattern_data['pattern_name'],
            pattern_data['signal_type'],
            pattern_data.get('confidence', 0),
            pattern_data.get('ml_confidence', 0),
            pattern_data.get('combined_confidence', 0),
            pattern_data['price_detection'],
            pattern_data.get('position_size', 0),
            pattern_data.get('prediction', 'HOLD'),
            pattern_data.get('timeframe', '1m')
        ))
        
        pattern_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        logger.info(f"Pattern saved: {pattern_data['pattern_name']} (ID: {pattern_id})")
        return pattern_id
    
    def update_pattern_result(self, pattern_id: int, result_data: dict):
        """Atualiza o resultado de um padrão"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE patterns_detected 
            SET status = 'closed', 
                result = ?, 
                profit_loss = ?, 
                duration_minutes = ?,
                exit_reason = ?
            WHERE id = ?
        ''', (
            result_data['result'],
            result_data['profit_loss'],
            result_data['duration_minutes'],
            result_data.get('exit_reason', 'timeout'),
            pattern_id
        ))
        
        conn.commit()
        conn.close()
        logger.info(f"Pattern {pattern_id} updated with result: {result_data['result']}")
    
    def get_patterns_by_status(self, status: str = 'open') -> pd.DataFrame:
        """Retorna padrões por status"""
        conn = self.get_connection()
        query = "SELECT * FROM patterns_detected WHERE status = ?"
        df = pd.read_sql(query, conn, params=[status])
        conn.close()
        return df
    
    def save_price_data(self, df: pd.DataFrame, symbol: str, timeframe: str):
        """Salva dados de preço no histórico"""
        conn = self.get_connection()
        
        # Para cache, vamos sobrescrever dados existentes para o período
        # Primeiro, deletar dados existentes no período
        min_ts = df['timestamp'].min()
        max_ts = df['timestamp'].max()
        if isinstance(min_ts, pd.Timestamp):
            min_ts = min_ts.strftime('%Y-%m-%d %H:%M:%S')
        if isinstance(max_ts, pd.Timestamp):
            max_ts = max_ts.strftime('%Y-%m-%d %H:%M:%S')
        
        delete_query = """
            DELETE FROM price_history 
            WHERE symbol = ? AND timeframe = ? AND timestamp >= ? AND timestamp <= ?
        """
        conn.execute(delete_query, [symbol, timeframe, min_ts, max_ts])
        
        # Inserir novos dados
        df_copy = df.copy()
        df_copy['symbol'] = symbol
        df_copy['timeframe'] = timeframe
        df_copy.to_sql('price_history', conn, if_exists='append', index=False)
        
        conn.commit()
        logger.info(f"Saved {len(df)} new price records for {symbol} {timeframe}")
        
        conn.close()
    
    def get_price_data(self, symbol: str, timeframe: str, 
                      start_date: datetime = None, end_date: datetime = None) -> pd.DataFrame:
        """Recupera dados de preço do cache para o período especificado"""
        conn = self.get_connection()
        
        query = """
            SELECT timestamp, open, high, low, close, volume 
            FROM price_history 
            WHERE symbol = ? AND timeframe = ?
        """
        params = [symbol, timeframe]
        
        if start_date:
            query += " AND timestamp >= ?"
            params.append(start_date.strftime('%Y-%m-%d %H:%M:%S'))
        if end_date:
            query += " AND timestamp <= ?"
            params.append(end_date.strftime('%Y-%m-%d %H:%M:%S'))
        
        query += " ORDER BY timestamp"
        
        df = pd.read_sql(query, conn, params=params)
        conn.close()
        
        if not df.empty:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            logger.info(f"Retrieved {len(df)} cached price records for {symbol} {timeframe}")
        
        return df
    
    def save_signal_for_analysis(self, signal_data: dict):
        """Salva sinal detectado para análise e retreinamento ML"""
        conn = self.get_connection()
        
        # Tabela para sinais coletados
        conn.execute('''CREATE TABLE IF NOT EXISTS collected_signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME,
            pattern TEXT,
            confidence REAL,
            signal TEXT,
            price REAL,
            market_data TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )''')
        
        conn.execute('''INSERT OR IGNORE INTO collected_signals 
            (timestamp, pattern, confidence, signal, price, market_data)
            VALUES (?, ?, ?, ?, ?, ?)''', (
            signal_data['timestamp'],
            signal_data['pattern'],
            signal_data['confidence'],
            signal_data['signal'],
            signal_data['price'],
            str(signal_data['market_data'])  # Salvar como string JSON
        ))
        
        conn.commit()
        conn.close()
        
        # logger.info(f"Signal saved for analysis: {signal_data['pattern']} ({signal_data['confidence']:.2f})")
    
    def get_collected_signals(self) -> pd.DataFrame:
        """Retorna sinais coletados para análise"""
        conn = self.get_connection()

        # Garante existência da tabela para suportar execução direta de retrain
        conn.execute('''CREATE TABLE IF NOT EXISTS collected_signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME,
            pattern TEXT,
            confidence REAL,
            signal TEXT,
            price REAL,
            market_data TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )''')

        df = pd.read_sql("SELECT * FROM collected_signals ORDER BY timestamp", conn)
        conn.close()
        return df
    
    def save_trade_result(self, trade_data: dict):
        """Salva resultado de trade executado"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO patterns_detected 
            (timestamp, pattern_name, signal_type, confidence, price_detection, 
             position_size, result, profit_loss, exit_reason, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'closed')
        ''', (
            trade_data['timestamp'],
            trade_data['pattern'],
            trade_data['signal_type'],
            trade_data.get('confidence', 0),
            trade_data['entry_price'],
            trade_data['position_size'],
            trade_data['result'],
            trade_data['profit'],
            trade_data.get('exit_reason', 'manual'),
        ))
        
        conn.commit()
        conn.close()
        logger.info(f"Trade result saved: {trade_data['pattern']} {trade_data['result']} ${trade_data['profit']:.2f}")
    
    def save_news_sentiment(self, sentiment_data: dict):
        """Salva sentimento agregado de notícias"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO news_sentiment 
            (timestamp, score, label, confidence, news_count, 
             positive_count, negative_count, neutral_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            sentiment_data['timestamp'],
            sentiment_data['score'],
            sentiment_data['label'],
            sentiment_data['confidence'],
            sentiment_data['news_count'],
            sentiment_data['positive_count'],
            sentiment_data['negative_count'],
            sentiment_data['neutral_count']
        ))
        
        conn.commit()
        conn.close()
        logger.info(f"News sentiment saved: {sentiment_data['label']} (score: {sentiment_data['score']:.2f})")
    
    def save_news_article(self, news_data: dict):
        """Salva notícia individual com seu sentimento (com proteção contra duplicatas)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Tentar inserir com proteção UNIQUE
            cursor.execute('''
                INSERT OR IGNORE INTO news_articles 
                (timestamp, title, source, sentiment_score, sentiment_label, url)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                news_data['timestamp'],
                news_data['title'],
                news_data['source'],
                news_data['sentiment_score'],
                news_data['sentiment_label'],
                news_data.get('url', '')
            ))
            
            conn.commit()
            # Retornar se foi inserido (rows affected > 0)
            return cursor.rowcount > 0
        except sqlite3.IntegrityError as e:
            logger.debug(f"Duplicate article skipped: {str(e)[:50]}")
            return False
        finally:
            conn.close()

    def save_ml_recipe_run(self, recipe_hash: str, symbol: str, timeframe: str,
                           horizon: str, config_json: str,
                           total_predictions: int, accuracy: float) -> int:
        """Salva execução de receita de ML e retorna run_id."""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            INSERT OR REPLACE INTO ml_recipe_runs
            (recipe_hash, symbol, timeframe, horizon, config_json, total_predictions, accuracy)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            recipe_hash,
            symbol,
            timeframe,
            horizon,
            config_json,
            total_predictions,
            accuracy
        ))

        conn.commit()

        cursor.execute('SELECT id FROM ml_recipe_runs WHERE recipe_hash = ?', (recipe_hash,))
        row = cursor.fetchone()
        conn.close()

        return row[0] if row else -1

    def save_ml_recipe_predictions(self, run_id: int, predictions: list):
        """Salva previsões de uma execução de receita."""
        if run_id <= 0 or not predictions:
            return

        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.executemany('''
            INSERT INTO ml_recipe_predictions
            (run_id, timestamp, predicted_direction, actual_direction, confidence, was_correct, decision_hash)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', [
            (
                run_id,
                p['timestamp'],
                p['predicted_direction'],
                p['actual_direction'],
                p['confidence'],
                p['was_correct'],
                p['decision_hash']
            )
            for p in predictions
        ])

        conn.commit()
        conn.close()
    
    def get_recent_sentiment(self, hours: int = 24) -> pd.DataFrame:
        """Retorna sentimentos recentes"""
        conn = self.get_connection()
        query = f"""
            SELECT * FROM news_sentiment 
            WHERE timestamp >= datetime('now', '-{hours} hours')
            ORDER BY timestamp DESC
        """
        df = pd.read_sql(query, conn)
        conn.close()
        return df