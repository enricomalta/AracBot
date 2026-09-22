# ml/prediction_tracker.py
"""
Sistema de rastreamento de previsões para validação e feedback
Permite medir acurácia real das previsões e fazer ajustes
"""

import pandas as pd
from datetime import datetime, timedelta
import logging
from typing import Dict, Optional, List
import json
from config.settings import settings

logger = logging.getLogger(__name__)


class PredictionTracker:
    """Rastreia previsões e valida resultados posteriormente"""
    
    def __init__(self, db_manager):
        self.db = db_manager
    
    def create_prediction(self, 
                         timeframe: str,
                         prediction_type: str,
                         predicted_direction: str,
                         target_price: float,
                         confidence: float,
                         model_type: str,
                         features_dict: Dict,
                         sentiment_score: Optional[float] = None,
                         oi_ratio: Optional[float] = None,
                         funding_rate: Optional[float] = None,
                         additional_context: Optional[Dict] = None) -> int:
        """
        Cria uma nova previsão no banco de dados
        
        Args:
            timeframe: '1h', '4h', '24h'
            prediction_type: 'direction', 'range', 'volatility'
            predicted_direction: 'up', 'down', 'sideways'
            target_price: Preço alvo
            confidence: 0-1
            model_type: 'random_forest', 'gradient_boost', 'ensemble'
            features_dict: Dicionário com features utilizadas
            sentiment_score: Score de sentimento (-1 a 1)
            oi_ratio: Open Interest ratio
            funding_rate: Taxa de financiamento
            additional_context: Contexto adicional (patterns detectados, etc)
            
        Returns:
            ID da previsão criada
        """
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            timestamp = datetime.now()
            
            # Calcular tempo de expiração baseado no timeframe
            if timeframe == '1h':
                expires_at = timestamp + timedelta(hours=1)
            elif timeframe == '4h':
                expires_at = timestamp + timedelta(hours=4)
            elif timeframe == '24h':
                expires_at = timestamp + timedelta(hours=24)
            else:
                expires_at = timestamp + timedelta(hours=1)
            
            # Serializar features para JSON
            features_json = json.dumps(features_dict)
            context_json = json.dumps(additional_context) if additional_context else None
            
            cursor.execute('''
                INSERT INTO predictions 
                (timestamp, timeframe, prediction_type, predicted_direction, target_price,
                 confidence, model_type, features_used, sentiment_score, oi_ratio, 
                 funding_rate, additional_context, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s, %s, %s::jsonb, %s)
                RETURNING id
            ''', (
                timestamp,
                timeframe,
                prediction_type,
                predicted_direction,
                target_price,
                confidence,
                model_type,
                features_json,
                sentiment_score,
                oi_ratio,
                funding_rate,
                context_json,
                datetime.now()
            ))
            
            conn.commit()
            prediction_id = cursor.fetchone()[0]
            conn.close()
            
            logger.info(f"Prediction #{prediction_id} created: {predicted_direction} "
                       f"to {target_price:.2f} (confidence: {confidence:.2%})")
            
            return prediction_id
            
        except Exception as e:
            logger.error(f"Error creating prediction: {e}")
            return -1
    
    def validate_prediction(self,
                           prediction_id: int,
                           actual_direction: str,
                           actual_price: float,
                           error_percent: Optional[float] = None) -> Dict:
        """
        Valida uma previsão com dados reais
        
        Args:
            prediction_id: ID da previsão
            actual_direction: Direção real observada ('up', 'down', 'sideways')
            actual_price: Preço real alcançado
            error_percent: Erro percentual da previsão
            
        Returns:
            Dicionário com resultado da validação
        """
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            # Buscar previsão
            cursor.execute('SELECT * FROM predictions WHERE id = %s', (prediction_id,))
            pred_row = cursor.fetchone()
            
            if not pred_row:
                logger.warning(f"Prediction #{prediction_id} not found")
                return {'success': False, 'error': 'Prediction not found'}
            
            # Converter para dicionário
            columns = [description[0] for description in cursor.description]
            prediction = dict(zip(columns, pred_row))
            
            # Validar
            was_correct = (prediction['predicted_direction'] == actual_direction)
            
            # Calcular profit/loss estimado
            target_price = prediction['target_price']
            profit_loss = ((actual_price - target_price) / target_price * 100) if target_price > 0 else 0
            
            # Atualizar previsão
            resolved_at = datetime.now()
            
            cursor.execute('''
                UPDATE predictions 
                SET actual_direction = %s, actual_price = %s, was_correct = %s,
                    profit_loss = %s, error_percent = %s, resolved_at = %s
                WHERE id = %s
            ''', (
                actual_direction,
                actual_price,
                was_correct,
                profit_loss,
                error_percent,
                resolved_at,
                prediction_id
            ))
            
            conn.commit()
            conn.close()
            
            result = {
                'success': True,
                'prediction_id': prediction_id,
                'was_correct': was_correct,
                'predicted': prediction['predicted_direction'],
                'actual': actual_direction,
                'target_price': target_price,
                'actual_price': actual_price,
                'error_percent': error_percent,
                'profit_loss': profit_loss,
                'model_type': prediction['model_type'],
                'confidence': prediction['confidence']
            }
            
            status = "[✓] ACERTO" if was_correct else "[✗] ERRO"
            logger.info(f"{status} - Prediction #{prediction_id}: {actual_direction} "
                       f"@ {actual_price:.2f} (expected {target_price:.2f})")
            
            return result
            
        except Exception as e:
            logger.error(f"Error validating prediction: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_pending_predictions(self, limit: int = 100) -> List[Dict]:
        """
        Retorna previsões pendentes de validação
        
        Returns:
            Lista de previsões que já expiraram mas não foram validadas
        """
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            # Calcular tempo de expiração
            # Uma previsão é "expirada" quando seu timeframe passou
            # 1h prediction: expira 1h depois de created_at
            # 4h prediction: expira 4h depois
            # etc.
            
            now = datetime.now()
            
            cursor.execute('''
                SELECT id, timestamp, timeframe, predicted_direction, target_price, 
                       confidence, model_type, created_at
                FROM predictions 
                WHERE was_correct IS NULL
                AND (
                    (timeframe = '1h' AND created_at < now() - interval '1 hour')
                    OR (timeframe = '4h' AND created_at < now() - interval '4 hours')
                    OR (timeframe = '24h' AND created_at < now() - interval '24 hours')
                )
                LIMIT %s
            ''', (limit,))
            
            columns = [description[0] for description in cursor.description]
            rows = cursor.fetchall()
            conn.close()
            
            pending = [dict(zip(columns, row)) for row in rows]
            logger.info(f"Found {len(pending)} pending predictions for validation")
            
            return pending
            
        except Exception as e:
            logger.error(f"Error fetching pending predictions: {e}")
            return []
    
    def get_accuracy_stats(self, 
                          model_type: Optional[str] = None,
                          prediction_type: Optional[str] = None,
                          timeframe: Optional[str] = None,
                          hours_back: int = 24) -> Dict:
        """
        Calcula estatísticas de acurácia
        
        Args:
            model_type: Filtrar por modelo ('random_forest', 'gradient_boost', etc)
            prediction_type: Filtrar por tipo ('direction', 'range', etc)
            timeframe: Filtrar por timeframe ('1h', '4h', '24h')
            hours_back: Últimas N horas
            
        Returns:
            Dicionário com estatísticas
        """
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            # Construir query dinamicamente
            query = '''
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN was_correct IS TRUE THEN 1 ELSE 0 END) as correct,
                    AVG(confidence) as avg_confidence,
                    AVG(profit_loss) as avg_profit_loss,
                    MIN(profit_loss) as min_profit_loss,
                    MAX(profit_loss) as max_profit_loss
                FROM predictions
                WHERE was_correct IS NOT NULL
                AND created_at > now() + (%s * interval '1 hour')
            '''
            
            params = [-hours_back]
            
            if model_type:
                query += ' AND model_type = %s'
                params.append(model_type)
            
            if prediction_type:
                query += ' AND prediction_type = %s'
                params.append(prediction_type)
            
            if timeframe:
                query += ' AND timeframe = %s'
                params.append(timeframe)
            
            cursor.execute(query, params)
            result = cursor.fetchone()
            conn.close()
            
            if result[0] == 0:  # total = 0
                return {
                    'total_predictions': 0,
                    'accuracy': 0,
                    'avg_confidence': 0,
                    'avg_profit_loss': 0,
                    'filters': {
                        'model_type': model_type,
                        'prediction_type': prediction_type,
                        'timeframe': timeframe,
                        'hours_back': hours_back
                    }
                }
            
            accuracy = (result[1] / result[0]) * 100 if result[0] > 0 else 0
            
            stats = {
                'total_predictions': result[0],
                'correct_predictions': result[1],
                'accuracy': accuracy,
                'avg_confidence': result[2],
                'avg_profit_loss': result[3],
                'min_profit_loss': result[4],
                'max_profit_loss': result[5],
                'filters': {
                    'model_type': model_type,
                    'prediction_type': prediction_type,
                    'timeframe': timeframe,
                    'hours_back': hours_back
                }
            }
            
            logger.info(f"Accuracy Stats: {accuracy:.2f}% ({result[1]}/{result[0]}) | "
                       f"Avg P&L: {result[3]:.2f}%")
            
            return stats
            
        except Exception as e:
            logger.error(f"Error calculating accuracy stats: {e}")
            return {}
    
    def get_best_models(self, limit: int = 10) -> List[Dict]:
        """
        Retorna modelos com melhor desempenho
        
        Returns:
            Lista ordenada por acurácia
        """
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT 
                    model_type,
                    COUNT(*) as total,
                    SUM(CASE WHEN was_correct IS TRUE THEN 1 ELSE 0 END) as correct,
                    AVG(confidence) as avg_confidence,
                    AVG(profit_loss) as avg_profit_loss
                FROM predictions
                WHERE was_correct IS NOT NULL
                GROUP BY model_type
                ORDER BY (CAST(correct AS FLOAT) / CAST(total AS FLOAT)) DESC
                LIMIT %s
            ''', (limit,))
            
            columns = [description[0] for description in cursor.description]
            rows = cursor.fetchall()
            conn.close()
            
            models = []
            for row in rows:
                model_dict = dict(zip(columns, row))
                model_dict['accuracy'] = (model_dict['correct'] / model_dict['total'] * 100) if model_dict['total'] > 0 else 0
                models.append(model_dict)
            
            return models
            
        except Exception as e:
            logger.error(f"Error fetching best models: {e}")
            return []
    
    def print_accuracy_report(self):
        """Imprime relatório de acurácia formatado"""
        print("\n" + "="*60)
        print("📊 RELATÓRIO DE PREVISÕES - ÚLTIMAS 24 HORAS")
        print("="*60)
        
        # Por timeframe
        for tf in ['1h', '4h', '24h']:
            stats = self.get_accuracy_stats(timeframe=tf, hours_back=24)
            if stats['total_predictions'] > 0:
                print(f"\n⏱️  {tf}:")
                print(f"   Total: {stats['total_predictions']} previsões")
                print(f"   Acertos: {stats['correct_predictions']}")
                print(f"   Acurácia: {stats['accuracy']:.2f}%")
                print(f"   Confiança média: {stats['avg_confidence']:.2%}")
                print(f"   P&L médio: {stats['avg_profit_loss']:.2f}%")
        
        # Melhores modelos
        print("\n" + "="*60)
        print("🏆 MODELOS COM MELHOR DESEMPENHO")
        print("="*60)
        best = self.get_best_models(limit=5)
        for i, model in enumerate(best, 1):
            print(f"\n{i}. {model['model_type']}")
            print(f"   Acurácia: {model['accuracy']:.2f}%")
            print(f"   Total: {model['total']} previsões")
            print(f"   P&L: {model['avg_profit_loss']:.2f}%")


if __name__ == "__main__":
    from data.database import DatabaseManager
    
    logging.basicConfig(level=logging.INFO)
    db = DatabaseManager()
    tracker = PredictionTracker(db)
    
    # Exemplo de uso
    print("\n=== Sistema de Rastreamento de Previsões ===\n")
    
    # Criar previsão
    pred_id = tracker.create_prediction(
        timeframe='1h',
        prediction_type='direction',
        predicted_direction='up',
        target_price=50000.0,
        confidence=0.75,
        model_type='gradient_boost',
        features_dict={'rsi': 45, 'macd': 100},
        sentiment_score=0.3,
        oi_ratio=1.2,
        funding_rate=0.00015
    )
    
    print(f"\nPrevisão criada: #{pred_id}")
    
    # Simular validação após 1 hora
    if pred_id > 0:
        validation = tracker.validate_prediction(
            prediction_id=pred_id,
            actual_direction='up',
            actual_price=50500.0,
            error_percent=1.0
        )
        print(f"Validação: {validation}")
    
    # Mostrar relatório
    tracker.print_accuracy_report()
