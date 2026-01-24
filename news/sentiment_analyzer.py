# news/sentiment_analyzer.py
import logging
from typing import Dict, List
import re

logger = logging.getLogger(__name__)

class SentimentAnalyzer:
    """Analisa sentimento de notícias sobre Bitcoin usando análise léxica"""
    
    def __init__(self):
        # Palavras positivas (bullish)
        self.positive_words = {
            # Ação de preço
            'surge', 'soar', 'rally', 'gain', 'rise', 'climb', 'jump', 'spike',
            'breakout', 'moon', 'bull', 'bullish', 'pump', 'green', 'profit',
            'growth', 'increase', 'up', 'higher', 'record', 'peak', 'high',
            'breakthrough', 'adoption', 'institutional', 'invest', 'buy',
            
            # Sentimento geral
            'positive', 'optimistic', 'confidence', 'strong', 'robust',
            'momentum', 'opportunity', 'potential', 'promising', 'favorable',
            'upgrade', 'innovation', 'success', 'winning', 'outperform',
            'recover', 'rebound', 'bounce', 'support', 'accumulation'
        }
        
        # Palavras negativas (bearish)
        self.negative_words = {
            # Ação de preço
            'crash', 'plunge', 'drop', 'fall', 'decline', 'sink', 'tumble',
            'collapse', 'bear', 'bearish', 'dump', 'red', 'loss', 'losses',
            'decrease', 'down', 'lower', 'bottom', 'low', 'liquidation',
            'sell', 'selling', 'selloff', 'correction', 'retreat',
            
            # Sentimento geral
            'negative', 'pessimistic', 'fear', 'weak', 'fragile', 'concern',
            'warning', 'risk', 'danger', 'threat', 'crisis', 'panic',
            'uncertain', 'volatility', 'struggle', 'failure', 'reject',
            'resistance', 'breakdown', 'underperform', 'regulation', 'ban'
        }
        
        # Intensificadores
        self.intensifiers = {
            'very': 1.5, 'extremely': 2.0, 'highly': 1.5, 'absolutely': 2.0,
            'massive': 2.0, 'huge': 1.8, 'significant': 1.5, 'major': 1.5,
            'sharp': 1.5, 'dramatic': 1.8, 'unprecedented': 2.0
        }
        
        # Negações
        self.negations = {'not', 'no', 'never', 'neither', 'nor', 'nothing', 'nobody'}
    
    def analyze_sentiment(self, text: str) -> Dict:
        """
        Analisa sentimento de um texto
        Returns: {'score': float, 'label': str, 'confidence': float}
        Score: -1 (muito negativo) a +1 (muito positivo)
        """
        if not text:
            return {'score': 0.0, 'label': 'neutral', 'confidence': 0.0}
        
        text_lower = text.lower()
        words = re.findall(r'\b\w+\b', text_lower)
        
        positive_score = 0.0
        negative_score = 0.0
        
        for i, word in enumerate(words):
            # Verificar negação antes da palavra
            is_negated = i > 0 and words[i-1] in self.negations
            
            # Verificar intensificador antes da palavra
            intensity = 1.0
            if i > 0 and words[i-1] in self.intensifiers:
                intensity = self.intensifiers[words[i-1]]
            
            # Calcular scores
            if word in self.positive_words:
                if is_negated:
                    negative_score += intensity
                else:
                    positive_score += intensity
            
            elif word in self.negative_words:
                if is_negated:
                    positive_score += intensity
                else:
                    negative_score += intensity
        
        # Calcular score final normalizado
        total_words = max(len(words), 1)
        pos_norm = positive_score / total_words
        neg_norm = negative_score / total_words
        
        # Score entre -1 e 1
        raw_score = pos_norm - neg_norm
        score = max(-1.0, min(1.0, raw_score * 10))  # Escalar e limitar
        
        # Determinar label e confidence
        if score > 0.3:
            label = 'positive'
            confidence = min(abs(score), 1.0)
        elif score < -0.3:
            label = 'negative'
            confidence = min(abs(score), 1.0)
        else:
            label = 'neutral'
            confidence = 1.0 - abs(score)
        
        return {
            'score': score,
            'label': label,
            'confidence': confidence,
            'positive_count': positive_score,
            'negative_count': negative_score
        }
    
    def analyze_news_batch(self, news_list: List[Dict]) -> List[Dict]:
        """Analisa sentimento de múltiplas notícias"""
        results = []
        
        for news in news_list:
            text = news.get('text', news.get('title', ''))
            sentiment = self.analyze_sentiment(text)
            
            result = news.copy()
            result['sentiment'] = sentiment
            results.append(result)
        
        logger.info(f"Analyzed sentiment for {len(results)} news articles")
        return results
    
    def get_aggregate_sentiment(self, news_list: List[Dict], recency_weight: bool = True) -> Dict:
        """
        Calcula sentimento agregado de múltiplas notícias
        Args:
            news_list: Lista de notícias com sentimento analisado
            recency_weight: Se True, notícias mais recentes têm mais peso
        """
        if not news_list:
            return {'score': 0.0, 'label': 'neutral', 'confidence': 0.0, 'count': 0}
        
        from datetime import datetime
        now = datetime.now()
        
        weighted_scores = []
        for news in news_list:
            sentiment = news.get('sentiment', {})
            score = sentiment.get('score', 0.0)
            confidence = sentiment.get('confidence', 0.0)
            
            # Calcular peso por recência (últimas 6h = peso 1.0, decai até 0.5)
            if recency_weight and 'published' in news:
                hours_ago = (now - news['published']).total_seconds() / 3600
                recency_factor = max(0.5, 1.0 - (hours_ago / 48))  # Decai em 48h
            else:
                recency_factor = 1.0
            
            # Peso final = confidence * recency
            weight = confidence * recency_factor
            weighted_scores.append(score * weight)
        
        # Média ponderada
        if weighted_scores:
            avg_score = sum(weighted_scores) / len(weighted_scores)
        else:
            avg_score = 0.0
        
        # Label agregado
        if avg_score > 0.2:
            label = 'bullish'
        elif avg_score < -0.2:
            label = 'bearish'
        else:
            label = 'neutral'
        
        return {
            'score': avg_score,
            'label': label,
            'confidence': abs(avg_score),
            'count': len(news_list),
            'positive_count': sum(1 for n in news_list if n.get('sentiment', {}).get('score', 0) > 0.3),
            'negative_count': sum(1 for n in news_list if n.get('sentiment', {}).get('score', 0) < -0.3),
            'neutral_count': sum(1 for n in news_list if -0.3 <= n.get('sentiment', {}).get('score', 0) <= 0.3)
        }
