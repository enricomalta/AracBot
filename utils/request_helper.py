# utils/request_helper.py
"""
Helper para requisições HTTP com retry automático e timeout robusto
Evita travamentos do bot por APIs lentas ou desresponsivas
"""

import requests
import logging
import time
from typing import Optional, Dict, Any
from functools import wraps
import threading

logger = logging.getLogger(__name__)

class RobustRequestSession:
    """Session HTTP com retry automático e timeout"""
    
    def __init__(self, max_retries: int = 3, timeout: int = 10, 
                 backoff_factor: float = 1.5, thread_timeout: int = 15):
        """
        Args:
            max_retries: Número máximo de tentativas
            timeout: Timeout padrão em segundos (por tentativa)
            backoff_factor: Multiplicador para exponential backoff
            thread_timeout: Timeout máximo da thread (para evitar travamentos)
        """
        self.session = requests.Session()
        self.max_retries = max_retries
        self.timeout = timeout
        self.backoff_factor = backoff_factor
        self.thread_timeout = thread_timeout
    
    def get_with_timeout(self, url: str, params: Optional[Dict] = None, 
                        timeout: Optional[int] = None, **kwargs) -> Optional[requests.Response]:
        """
        GET com timeout e retry automático
        
        Args:
            url: URL alvo
            params: Parâmetros da query
            timeout: Timeout custom (padrão: self.timeout)
            **kwargs: Argumentos adicionais para requests
            
        Returns:
            Response ou None se falhar em todas as tentativas
        """
        timeout = timeout or self.timeout
        
        # Executar em thread separada com timeout para evitar travamento
        result = {'response': None, 'error': None}
        
        def make_request():
            for attempt in range(1, self.max_retries + 1):
                try:
                    response = self.session.get(
                        url, 
                        params=params, 
                        timeout=timeout,
                        **kwargs
                    )
                    response.raise_for_status()
                    result['response'] = response
                    return
                    
                except requests.Timeout:
                    wait_time = self.backoff_factor ** (attempt - 1)
                    logger.warning(
                        f"[Attempt {attempt}/{self.max_retries}] Timeout ({timeout}s) "
                        f"for {url}. Retrying in {wait_time:.1f}s..."
                    )
                    time.sleep(wait_time)
                    
                except requests.ConnectionError as e:
                    wait_time = self.backoff_factor ** (attempt - 1)
                    logger.warning(
                        f"[Attempt {attempt}/{self.max_retries}] Connection error: {e}. "
                        f"Retrying in {wait_time:.1f}s..."
                    )
                    time.sleep(wait_time)
                    
                except requests.HTTPError as e:
                    if 429 in str(e):  # Rate limit
                        wait_time = self.backoff_factor ** attempt * 5  # Esperar mais para rate limit
                        logger.warning(
                            f"[Attempt {attempt}/{self.max_retries}] Rate limited. "
                            f"Waiting {wait_time:.1f}s..."
                        )
                        time.sleep(wait_time)
                    else:
                        result['error'] = e
                        logger.error(f"HTTP Error: {e}")
                        return
                        
                except Exception as e:
                    result['error'] = e
                    logger.error(f"Error in attempt {attempt}: {e}")
                    return
            
            result['error'] = f"Failed after {self.max_retries} attempts"
        
        # Executar com timeout de thread
        thread = threading.Thread(target=make_request, daemon=True)
        thread.start()
        thread.join(timeout=self.thread_timeout)
        
        if thread.is_alive():
            logger.error(f"Request to {url} timed out after {self.thread_timeout}s (thread still running)")
            return None
        
        if result['error']:
            logger.error(f"Request failed: {result['error']}")
            return None
        
        return result['response']
    
    def post_with_timeout(self, url: str, json: Optional[Dict] = None,
                         timeout: Optional[int] = None, **kwargs) -> Optional[requests.Response]:
        """POST com retry automático"""
        timeout = timeout or self.timeout
        
        result = {'response': None, 'error': None}
        
        def make_request():
            for attempt in range(1, self.max_retries + 1):
                try:
                    response = self.session.post(
                        url,
                        json=json,
                        timeout=timeout,
                        **kwargs
                    )
                    response.raise_for_status()
                    result['response'] = response
                    return
                    
                except requests.Timeout:
                    wait_time = self.backoff_factor ** (attempt - 1)
                    logger.warning(f"[POST Attempt {attempt}/{self.max_retries}] Timeout. Retrying in {wait_time:.1f}s...")
                    time.sleep(wait_time)
                    
                except Exception as e:
                    result['error'] = e
                    logger.error(f"POST Error: {e}")
                    return
        
        thread = threading.Thread(target=make_request, daemon=True)
        thread.start()
        thread.join(timeout=self.thread_timeout)
        
        if thread.is_alive():
            logger.error(f"POST to {url} timed out")
            return None
        
        if result['error']:
            return None
        
        return result['response']
    
    def close(self):
        """Fechar session"""
        self.session.close()


def retry_on_failure(max_retries: int = 3, backoff_factor: float = 1.5, timeout: int = 10):
    """
    Decorator para adicionar retry a qualquer função
    
    Usage:
        @retry_on_failure(max_retries=3, timeout=10)
        def my_function():
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(1, max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries:
                        logger.error(f"Failed after {max_retries} attempts: {e}")
                        return None
                    
                    wait_time = backoff_factor ** (attempt - 1)
                    logger.warning(
                        f"[{func.__name__}] Attempt {attempt}/{max_retries} failed. "
                        f"Retrying in {wait_time:.1f}s... Error: {e}"
                    )
                    time.sleep(wait_time)
            
            return None
        return wrapper
    return decorator
