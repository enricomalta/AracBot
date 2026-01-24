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
        
        conn.commit()
        conn.close()
        logger.info("Database setup completed")
    
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
        
        conn.execute('''INSERT INTO collected_signals 
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