# data/database.py
import sqlite3
import pandas as pd
from datetime import datetime
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
        
        # Verificar dados existentes
        existing_query = """
            SELECT timestamp FROM price_history 
            WHERE symbol = ? AND timeframe = ? AND timestamp >= ?
        """
        existing_timestamps = pd.read_sql(
            existing_query, conn, 
            params=[symbol, timeframe, df['timestamp'].min()]
        )['timestamp'].values
        
        # Filtrar dados novos
        new_data = df[~df['timestamp'].isin(existing_timestamps)].copy()
        new_data['symbol'] = symbol
        new_data['timeframe'] = timeframe
        
        if not new_data.empty:
            new_data.to_sql('price_history', conn, if_exists='append', index=False)
            logger.info(f"Saved {len(new_data)} new price records for {symbol} {timeframe}")
        
        conn.close()