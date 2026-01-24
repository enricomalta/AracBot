# news/news_collector.py
import requests
import feedparser
from datetime import datetime, timedelta
from typing import List, Dict
import logging
import time

logger = logging.getLogger(__name__)

class NewsCollector:
    """Coleta notícias sobre Bitcoin de múltiplas fontes"""
    
    def __init__(self):
        self.sources = {
            'google_news_rss': 'https://news.google.com/rss/search?q=bitcoin&hl=en-US&gl=US&ceid=US:en',
            'coindesk_rss': 'https://www.coindesk.com/arc/outboundfeeds/rss/',
            'cointelegraph_rss': 'https://cointelegraph.com/rss'
        }
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def collect_recent_news(self, hours: int = 24, max_news: int = 50) -> List[Dict]:
        """Coleta notícias recentes de todas as fontes (apenas RSS feeds gratuitos)"""
        all_news = []
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        # Coletar de RSS feeds (gratuito, sem API key)
        all_news.extend(self._collect_from_rss('google_news_rss', cutoff_time))
        all_news.extend(self._collect_from_rss('coindesk_rss', cutoff_time))
        all_news.extend(self._collect_from_rss('cointelegraph_rss', cutoff_time))
        
        # Remover duplicatas por título
        seen_titles = set()
        unique_news = []
        for news in all_news:
            title_lower = news['title'].lower()
            if title_lower not in seen_titles:
                seen_titles.add(title_lower)
                unique_news.append(news)
        
        # Ordenar por recência
        unique_news.sort(key=lambda x: x['published'], reverse=True)
        
        logger.info(f"Collected {len(unique_news)} unique news articles from {hours}h")
        return unique_news[:max_news]
    
    def _collect_from_rss(self, source_name: str, cutoff_time: datetime) -> List[Dict]:
        """Coleta notícias de um feed RSS"""
        try:
            url = self.sources[source_name]
            feed = feedparser.parse(url)
            
            news_list = []
            for entry in feed.entries[:30]:  # Limitar a 30 por fonte
                try:
                    # Parsear data de publicação
                    if hasattr(entry, 'published_parsed'):
                        pub_date = datetime(*entry.published_parsed[:6])
                    elif hasattr(entry, 'updated_parsed'):
                        pub_date = datetime(*entry.updated_parsed[:6])
                    else:
                        pub_date = datetime.now()
                    
                    # Filtrar por data
                    if pub_date < cutoff_time:
                        continue
                    
                    # Extrair título e descrição
                    title = entry.get('title', '')
                    description = entry.get('summary', entry.get('description', ''))
                    
                    # Filtrar apenas notícias relacionadas a Bitcoin/crypto
                    if not self._is_bitcoin_related(title + ' ' + description):
                        continue
                    
                    news_list.append({
                        'title': title,
                        'description': description,
                        'source': source_name,
                        'url': entry.get('link', ''),
                        'published': pub_date,
                        'text': f"{title}. {description}"
                    })
                    
                except Exception as e:
                    logger.debug(f"Error parsing entry from {source_name}: {str(e)}")
                    continue
            
            logger.info(f"Collected {len(news_list)} articles from {source_name}")
            return news_list
            
        except Exception as e:
            logger.error(f"Error collecting from {source_name}: {str(e)}")
            return []
    
    def _is_bitcoin_related(self, text: str) -> bool:
        """Verifica se o texto é relacionado a Bitcoin/cripto"""
        keywords = [
            'bitcoin', 'btc', 'crypto', 'cryptocurrency', 
            'blockchain', 'satoshi', 'mining', 'halving',
            'hash rate', 'difficulty', 'mempool'
        ]
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in keywords)
    

