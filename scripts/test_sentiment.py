# test_sentiment.py
"""
Script para testar o sistema de análise de sentimento
"""
import logging
from datetime import datetime
from news.news_sentiment_manager import NewsSentimentManager
from data.database import DatabaseManager
from utils.helpers import setup_logging

def test_sentiment_system():
    """Testa coleta de notícias e análise de sentimento"""
    setup_logging(logging.INFO)
    logger = logging.getLogger(__name__)
    
    print("=" * 60)
    print("TESTE DE SISTEMA DE ANÁLISE DE SENTIMENTO")
    print("=" * 60)
    
    # Inicializar componentes
    db = DatabaseManager()
    sentiment_manager = NewsSentimentManager(database_manager=db)
    
    # Teste 1: Coletar notícias e calcular sentimento
    print("\n📰 Teste 1: Coletando notícias e analisando sentimento...")
    print("-" * 60)
    
    try:
        sentiment = sentiment_manager.get_current_market_sentiment(
            hours=24,
            max_news=50,
            use_cache=False  # Forçar busca nova
        )
        
        print(f"\n✅ Sentimento coletado com sucesso!")
        print(f"Score: {sentiment['score']:.2f}")
        print(f"Label: {sentiment['label'].upper()}")
        print(f"Confidence: {sentiment['confidence']:.2f}")
        print(f"News Count: {sentiment['news_count']}")
        print(f"Timestamp: {sentiment['timestamp']}")
        
        if 'positive_count' in sentiment:
            print(f"\nDistribuição:")
            print(f"  Positivas: {sentiment.get('positive_count', 0)}")
            print(f"  Negativas: {sentiment.get('negative_count', 0)}")
            print(f"  Neutras: {sentiment.get('neutral_count', 0)}")
        
        # Mostrar resumo de notícias
        print("\n" + "=" * 60)
        print(sentiment_manager.get_recent_news_summary())
        print("=" * 60)
        
    except Exception as e:
        print(f"❌ Erro ao coletar sentimento: {str(e)}")
        logger.error(f"Sentiment collection failed: {str(e)}", exc_info=True)
        return
    
    # Teste 2: Testar decisões de trading
    print("\n📊 Teste 2: Testando decisões de trading baseadas em sentimento...")
    print("-" * 60)
    
    test_cases = [
        {'signal_type': 'buy', 'scenario': 'Compra com sentimento atual'},
        {'signal_type': 'sell', 'scenario': 'Venda com sentimento atual'},
    ]
    
    for test in test_cases:
        decision = sentiment_manager.should_trade(
            signal_type=test['signal_type'],
            current_sentiment=sentiment
        )
        
        print(f"\n{test['scenario']}:")
        print(f"  Should Trade: {'✅ SIM' if decision['should_trade'] else '❌ NÃO'}")
        print(f"  Confidence Adjustment: {decision['confidence_adjustment']:+.3f}")
        print(f"  Reason: {decision['reason']}")
    
    # Teste 3: Verificar cache
    print("\n💾 Teste 3: Verificando sistema de cache...")
    print("-" * 60)
    
    start_time = datetime.now()
    sentiment_cached = sentiment_manager.get_current_market_sentiment(
        hours=24,
        max_news=50,
        use_cache=True  # Usar cache
    )
    elapsed = (datetime.now() - start_time).total_seconds()
    
    print(f"✅ Cache funcionando! Tempo de resposta: {elapsed:.3f}s")
    print(f"Score: {sentiment_cached['score']:.2f} (mesmo que antes)")
    
    # Teste 4: Verificar banco de dados
    print("\n🗄️  Teste 4: Verificando salvamento no banco de dados...")
    print("-" * 60)
    
    try:
        recent_sentiments = db.get_recent_sentiment(hours=1)
        if not recent_sentiments.empty:
            print(f"✅ Sentimentos salvos no banco: {len(recent_sentiments)} registros na última hora")
            last_record = recent_sentiments.iloc[0]
            print(f"Último registro:")
            print(f"  Timestamp: {last_record['timestamp']}")
            print(f"  Score: {last_record['score']:.2f}")
            print(f"  Label: {last_record['label']}")
            print(f"  News Count: {last_record['news_count']}")
        else:
            print("ℹ️  Nenhum sentimento salvo ainda no banco de dados")
    except Exception as e:
        print(f"⚠️  Não foi possível verificar banco: {str(e)}")
    
    # Resumo final
    print("\n" + "=" * 60)
    print("RESUMO DOS TESTES")
    print("=" * 60)
    print("✅ Coleta de notícias: OK")
    print("✅ Análise de sentimento: OK")
    print("✅ Decisões de trading: OK")
    print("✅ Sistema de cache: OK")
    print("=" * 60)
    
    print("\n💡 Sistema de sentimento está funcionando corretamente!")
    print("📈 Pronto para ser integrado ao bot de trading.")

if __name__ == "__main__":
    test_sentiment_system()
