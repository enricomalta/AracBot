# analysis/performance.py
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Dict
import logging
from data.database import DatabaseManager

logger = logging.getLogger(__name__)

class PerformanceAnalyzer:
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    def calculate_overall_metrics(self) -> Dict:
        """Calcula métricas gerais de performance"""
        conn = self.db.get_connection()
        
        try:
            # Métricas básicas
            metrics_query = """
                SELECT 
                    COUNT(*) as total_patterns,
                    SUM(CASE WHEN result = 'success' THEN 1 ELSE 0 END) as successes,
                    SUM(CASE WHEN result = 'failure' THEN 1 ELSE 0 END) as failures,
                    AVG(profit_loss) as avg_profit_loss,
                    AVG(combined_confidence) as avg_confidence,
                    AVG(duration_minutes) as avg_duration
                FROM patterns_detected 
                WHERE status = 'closed'
            """
            
            metrics = pd.read_sql(metrics_query, conn).iloc[0]
            
            total = metrics['total_patterns']
            successes = metrics['successes']
            accuracy = (successes / total * 100) if total > 0 else 0
            
            # Métricas por padrão
            pattern_query = """
                SELECT 
                    pattern_name,
                    COUNT(*) as count,
                    AVG(CASE WHEN result = 'success' THEN 1 ELSE 0 END) * 100 as success_rate,
                    AVG(profit_loss) as avg_profit_loss,
                    AVG(combined_confidence) as avg_confidence
                FROM patterns_detected 
                WHERE status = 'closed'
                GROUP BY pattern_name
                ORDER BY count DESC
            """
            
            pattern_metrics = pd.read_sql(pattern_query, conn)
            
            # Performance temporal
            temporal_query = """
                SELECT 
                    DATE(timestamp) as date,
                    COUNT(*) as daily_patterns,
                    AVG(CASE WHEN result = 'success' THEN 1 ELSE 0 END) * 100 as daily_success_rate,
                    SUM(profit_loss) as daily_pnl
                FROM patterns_detected 
                WHERE status = 'closed'
                GROUP BY DATE(timestamp)
                ORDER BY date
            """
            
            temporal_metrics = pd.read_sql(temporal_query, conn)
            
            return {
                'overall': {
                    'total_patterns': total,
                    'success_rate': accuracy,
                    'avg_profit_loss': metrics['avg_profit_loss'],
                    'avg_confidence': metrics['avg_confidence'],
                    'avg_duration': metrics['avg_duration']
                },
                'by_pattern': pattern_metrics.to_dict('records'),
                'temporal': temporal_metrics.to_dict('records')
            }
            
        finally:
            conn.close()
    
    def generate_performance_report(self) -> str:
        """Gera relatório de performance em texto"""
        metrics = self.calculate_overall_metrics()
        
        report = f"""
📊 RELATÓRIO DE PERFORMANCE DO BOT

MÉTRICAS GERAIS:
• Padrões Analisados: {metrics['overall']['total_patterns']}
• Taxa de Acerto: {metrics['overall']['success_rate']:.1f}%
• P&L Médio: {metrics['overall']['avg_profit_loss']:.4f}%
• Confiança Média: {metrics['overall']['avg_confidence']:.2f}
• Duração Média: {metrics['overall']['avg_duration']:.1f} min

DESEMPENHO POR PADRÃO:
"""
        
        for pattern in metrics['by_pattern']:
            report += f"• {pattern['pattern_name']}: {pattern['count']} trades "
            report += f"({pattern['success_rate']:.1f}% sucesso, "
            report += f"P&L: {pattern['avg_profit_loss']:.4f}%)\n"
        
        return report
    
    def plot_performance_charts(self, save_path: str = 'performance_charts.png'):
        """Gera gráficos de performance"""
        metrics = self.calculate_overall_metrics()
        
        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
        
        # Gráfico 1: Success rate por padrão
        pattern_df = pd.DataFrame(metrics['by_pattern'])
        if not pattern_df.empty:
            axes[0, 0].bar(pattern_df['pattern_name'], pattern_df['success_rate'])
            axes[0, 0].set_title('Taxa de Sucesso por Padrão')
            axes[0, 0].tick_params(axis='x', rotation=45)
        
        # Gráfico 2: Distribuição de P&L
        conn = self.db.get_connection()
        pnl_data = pd.read_sql(
            "SELECT profit_loss FROM patterns_detected WHERE status = 'closed'", 
            conn
        )
        conn.close()
        
        if not pnl_data.empty:
            axes[0, 1].hist(pnl_data['profit_loss'], bins=30, alpha=0.7)
            axes[0, 1].axvline(0, color='red', linestyle='--')
            axes[0, 1].set_title('Distribuição de P&L')
            axes[0, 1].set_xlabel('P&L (%)')
            axes[0, 1].set_ylabel('Frequência')
        
        # Gráfico 3: Evolução temporal
        temporal_df = pd.DataFrame(metrics['temporal'])
        if not temporal_df.empty:
            temporal_df['date'] = pd.to_datetime(temporal_df['date'])
            axes[1, 0].plot(temporal_df['date'], temporal_df['daily_success_rate'])
            axes[1, 0].set_title('Evolução da Taxa de Sucesso')
            axes[1, 0].tick_params(axis='x', rotation=45)
        
        # Gráfico 4: Confiança vs Resultado
        conn = self.db.get_connection()
        confidence_data = pd.read_sql("""
            SELECT combined_confidence, 
                   CASE WHEN result = 'success' THEN 1 ELSE 0 END as success
            FROM patterns_detected 
            WHERE status = 'closed'
        """, conn)
        conn.close()
        
        if not confidence_data.empty:
            success_confidence = confidence_data[confidence_data['success'] == 1]['combined_confidence']
            failure_confidence = confidence_data[confidence_data['success'] == 0]['combined_confidence']
            
            axes[1, 1].hist([success_confidence, failure_confidence], 
                           bins=20, alpha=0.7, label=['Sucesso', 'Falha'])
            axes[1, 1].set_title('Confiança vs Resultado')
            axes[1, 1].set_xlabel('Confiança')
            axes[1, 1].legend()
        
        plt.tight_layout()
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        logger.info(f"Performance charts saved to {save_path}")