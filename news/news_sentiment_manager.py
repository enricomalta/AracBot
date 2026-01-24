# news/news_sentiment_manager.py
import logging
from datetime import datetime
from typing import Dict, Optional
from .news_collector import NewsCollector
from .sentiment_analyzer import SentimentAnalyzer

logger = logging.getLogger(__name__)

class NewsSentimentManager:
    """Gerencia coleta e análise de sentimento de notícias"""
    
    def __init__(self, database_manager=None):
        self.collector = NewsCollector()
        self.analyzer = SentimentAnalyzer()
        self.db = database_manager
        self.cache = {
            'sentiment': None,
            'timestamp': None,
            'news_list': []
        }
        self.cache_duration_minutes = 30  # Cache por 30 minutos
    
    def get_current_market_sentiment(self, hours: int = 24, max_news: int = 50, 
                                    use_cache: bool = True) -> Dict:
        """
        Obtém sentimento atual do mercado baseado em notícias recentes
        
        Returns:
            {
                'score': float (-1 a 1),
                'label': str ('bullish', 'bearish', 'neutral'),
                'confidence': float (0 a 1),
                'news_count': int,
                'timestamp': datetime
            }
        """
        # Verificar cache
        if use_cache and self._is_cache_valid():
            logger.info("Using cached sentiment data")
            return self.cache['sentiment']
        
        try:
            # Coletar notícias
            logger.info(f"Collecting news from last {hours} hours...")
            news_list = self.collector.collect_recent_news(hours=hours, max_news=max_news)
            
            if not news_list:
                logger.warning("No news collected, returning neutral sentiment")
                return self._neutral_sentiment()
            
            # Analisar sentimento
            logger.info(f"Analyzing sentiment for {len(news_list)} news articles...")
            analyzed_news = self.analyzer.analyze_news_batch(news_list)
            
            # Calcular sentimento agregado
            aggregate_sentiment = self.analyzer.get_aggregate_sentiment(
                analyzed_news, 
                recency_weight=True
            )
            
            # Adicionar timestamp
            aggregate_sentiment['timestamp'] = datetime.now()
            aggregate_sentiment['news_count'] = len(analyzed_news)
            
            # Salvar no banco se disponível
            if self.db:
                self._save_to_database(aggregate_sentiment, analyzed_news)
            
            # Atualizar cache
            self.cache = {
                'sentiment': aggregate_sentiment,
                'timestamp': datetime.now(),
                'news_list': analyzed_news
            }
            
            logger.info(f"Market sentiment: {aggregate_sentiment['label']} "
                       f"(score: {aggregate_sentiment['score']:.2f}, "
                       f"confidence: {aggregate_sentiment['confidence']:.2f})")
            
            return aggregate_sentiment
            
        except Exception as e:
            logger.error(f"Error getting market sentiment: {str(e)}")
            return self._neutral_sentiment()
    
    def should_trade(self, signal_type: str, current_sentiment: Optional[Dict] = None) -> Dict:
        """
        Determina se deve executar trade baseado no sentimento
        
        Args:
            signal_type: 'buy' ou 'sell'
            current_sentiment: sentimento atual (se None, busca novo)
        
        Returns:
            {
                'should_trade': bool,
                'confidence_adjustment': float,
                'reason': str
            }
        """
        if current_sentiment is None:
            current_sentiment = self.get_current_market_sentiment()
        
        score = current_sentiment['score']
        label = current_sentiment['label']
        confidence = current_sentiment['confidence']
        
        # Regras de decisão
        if signal_type == 'buy':
            if label == 'bearish' and score < -0.4:
                # Sentimento muito negativo - não comprar
                return {
                    'should_trade': False,
                    'confidence_adjustment': 0.0,
                    'reason': f'Market sentiment is very bearish (score: {score:.2f})'
                }
            elif label == 'bullish' and score > 0.3:
                # Sentimento positivo - aumentar confiança
                return {
                    'should_trade': True,
                    'confidence_adjustment': 0.05 * confidence,  # +5% máximo
                    'reason': f'Market sentiment is bullish (score: {score:.2f})'
                }
            elif label == 'bearish' and score < -0.2:
                # Sentimento negativo moderado - reduzir confiança
                return {
                    'should_trade': True,
                    'confidence_adjustment': -0.03 * confidence,  # -3% máximo
                    'reason': f'Market sentiment is moderately bearish (score: {score:.2f})'
                }
            else:
                # Sentimento neutro
                return {
                    'should_trade': True,
                    'confidence_adjustment': 0.0,
                    'reason': 'Market sentiment is neutral'
                }
        
        elif signal_type == 'sell':
            if label == 'bullish' and score > 0.4:
                # Sentimento muito positivo - não vender (pode subir mais)
                return {
                    'should_trade': False,
                    'confidence_adjustment': 0.0,
                    'reason': f'Market sentiment is very bullish (score: {score:.2f})'
                }
            elif label == 'bearish' and score < -0.3:
                # Sentimento negativo - aumentar confiança na venda
                return {
                    'should_trade': True,
                    'confidence_adjustment': 0.05 * confidence,
                    'reason': f'Market sentiment is bearish (score: {score:.2f})'
                }
            elif label == 'bullish' and score > 0.2:
                # Sentimento positivo moderado - reduzir confiança
                return {
                    'should_trade': True,
                    'confidence_adjustment': -0.03 * confidence,
                    'reason': f'Market sentiment is moderately bullish (score: {score:.2f})'
                }
            else:
                # Sentimento neutro
                return {
                    'should_trade': True,
                    'confidence_adjustment': 0.0,
                    'reason': 'Market sentiment is neutral'
                }
        
        return {
            'should_trade': True,
            'confidence_adjustment': 0.0,
            'reason': 'Unknown signal type'
        }
    
    def _is_cache_valid(self) -> bool:
        """Verifica se o cache ainda é válido"""
        if self.cache['timestamp'] is None:
            return False
        
        minutes_elapsed = (datetime.now() - self.cache['timestamp']).total_seconds() / 60
        return minutes_elapsed < self.cache_duration_minutes
    
    def _neutral_sentiment(self) -> Dict:
        """Retorna sentimento neutro padrão"""
        return {
            'score': 0.0,
            'label': 'neutral',
            'confidence': 0.0,
            'news_count': 0,
            'timestamp': datetime.now(),
            'positive_count': 0,
            'negative_count': 0,
            'neutral_count': 0
        }
    
    def _save_to_database(self, sentiment: Dict, news_list: list):
        """Salva sentimento e notícias no banco de dados"""
        try:
            # Salvar sentimento agregado
            self.db.save_news_sentiment({
                'timestamp': sentiment['timestamp'],
                'score': sentiment['score'],
                'label': sentiment['label'],
                'confidence': sentiment['confidence'],
                'news_count': len(news_list),
                'positive_count': sentiment.get('positive_count', 0),
                'negative_count': sentiment.get('negative_count', 0),
                'neutral_count': sentiment.get('neutral_count', 0)
            })
            
            # Salvar notícias individuais (opcional, limitar a top 10)
            for news in news_list[:10]:
                self.db.save_news_article({
                    'timestamp': news.get('published', datetime.now()),
                    'title': news.get('title', ''),
                    'source': news.get('source', ''),
                    'sentiment_score': news.get('sentiment', {}).get('score', 0.0),
                    'sentiment_label': news.get('sentiment', {}).get('label', 'neutral'),
                    'url': news.get('url', '')
                })
            
            logger.info(f"Saved sentiment and {len(news_list[:10])} articles to database")
            
        except Exception as e:
            logger.error(f"Error saving to database: {str(e)}")
    
    def get_recent_news_summary(self) -> str:
        """Retorna resumo das notícias recentes"""
        if not self.cache['news_list']:
            return "No recent news available"
        
        sentiment = self.cache['sentiment']
        news_list = self.cache['news_list'][:5]  # Top 5
        
        summary = f"📰 Market Sentiment: {sentiment['label'].upper()} "
        summary += f"(score: {sentiment['score']:.2f}, confidence: {sentiment['confidence']:.2f})\n\n"
        summary += f"Recent headlines ({len(news_list)}):\n"
        
        for i, news in enumerate(news_list, 1):
            sent = news.get('sentiment', {})
            emoji = "📈" if sent.get('label') == 'positive' else "📉" if sent.get('label') == 'negative' else "➡️"
            summary += f"{i}. {emoji} {news.get('title', 'N/A')[:80]}...\n"
        
        return summary
