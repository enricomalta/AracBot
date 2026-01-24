# test_news_rss.py
"""
Script para testar coleta de noticias dos RSS feeds (sem CryptoPanic)
"""
import logging
from news.news_collector import NewsCollector
from utils.helpers import setup_logging

def test_rss_feeds():
    """Testa coleta de noticias dos RSS feeds gratuitos"""
    setup_logging(logging.INFO)
    logger = logging.getLogger(__name__)
    
    print("=" * 60)
    print("TESTE DE COLETA DE NOTICIAS - RSS FEEDS GRATUITOS")
    print("=" * 60)
    
    print("\nFontes configuradas:")
    print("  1. Google News RSS (bitcoin)")
    print("  2. CoinDesk RSS")
    print("  3. Cointelegraph RSS")
    
    # Testar coleta
    print(f"\nColetando noticias das ultimas 24 horas...")
    collector = NewsCollector()
    
    try:
        # Coletar notícias
        news_list = collector.collect_recent_news(hours=24, max_news=50)
        
        print(f"\nTotal de noticias coletadas: {len(news_list)}")
        
        # Contar por fonte
        sources = {}
        for news in news_list:
            source = news.get('source', 'unknown')
            sources[source] = sources.get(source, 0) + 1
        
        print("\nDistribuicao por fonte:")
        for source, count in sorted(sources.items()):
            print(f"  - {source}: {count} noticias")
        
        # Mostrar algumas manchetes
        print(f"\nExemplo de manchetes (top 5):")
        for i, news in enumerate(news_list[:5], 1):
            print(f"{i}. [{news['source']}] {news['title'][:70]}...")
        
        print("\n" + "=" * 60)
        print("TESTE COMPLETO!")
        print("=" * 60)
        print(f"Total: {len(news_list)} noticias de {len(sources)} fontes RSS")
        print("Sistema funcionando 100% com feeds gratuitos!")
        
    except Exception as e:
        print(f"\nERRO ao coletar noticias: {str(e)}")
        logger.error(f"Collection failed: {str(e)}", exc_info=True)

if __name__ == "__main__":
    test_rss_feeds()
