# utils/watchdog.py
"""
Watchdog para monitorar e reiniciar o bot se ele ficar travado
Detecta inatividade por muito tempo e tira o bot de um estado travado
"""

import logging
import time
import threading
from datetime import datetime, timedelta
from typing import Callable, Optional

logger = logging.getLogger(__name__)

class BotWatchdog:
    """Monitora o bot e detecta travamentos"""
    
    def __init__(self, timeout_minutes: int = 30, check_interval: int = 5):
        """
        Args:
            timeout_minutes: Minutos sem atividade antes de considerar travado
            check_interval: Intervalo de verificação em segundos
        """
        self.timeout = timedelta(minutes=timeout_minutes)
        self.check_interval = check_interval
        self.last_activity = datetime.now()
        self.running = False
        self.thread = None
        self.on_timeout_callback: Optional[Callable] = None
    
    def mark_activity(self):
        """Marca que o bot está ativo (chamado após cada ciclo)"""
        self.last_activity = datetime.now()
    
    def start(self, on_timeout_callback: Optional[Callable] = None):
        """Inicia o watchdog"""
        self.on_timeout_callback = on_timeout_callback
        self.running = True
        self.thread = threading.Thread(target=self._watch, daemon=True)
        self.thread.start()
        logger.info(f"Watchdog started (timeout: {self.timeout.total_seconds():.0f}s)")
    
    def stop(self):
        """Para o watchdog"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        logger.info("Watchdog stopped")
    
    def _watch(self):
        """Loop de monitoramento"""
        while self.running:
            time.sleep(self.check_interval)
            
            elapsed = datetime.now() - self.last_activity
            
            if elapsed > self.timeout:
                logger.error(
                    f"Bot appears to be frozen! No activity for {elapsed.total_seconds():.0f}s "
                    f"(timeout: {self.timeout.total_seconds():.0f}s)"
                )
                
                if self.on_timeout_callback:
                    try:
                        logger.info("Triggering timeout callback...")
                        self.on_timeout_callback()
                    except Exception as e:
                        logger.error(f"Error in timeout callback: {e}")


class InactivityDetector:
    """Detecta padrões de inatividade periódica (por exemplo, durante sleep)"""
    
    def __init__(self, expected_cycle_interval_minutes: int = 60):
        """
        Args:
            expected_cycle_interval_minutes: Intervalo esperado entre ciclos (ex: 60 min)
        """
        self.expected_interval = timedelta(minutes=expected_cycle_interval_minutes)
        self.last_cycle_start = datetime.now()
        self.cycle_count = 0
    
    def mark_cycle_start(self):
        """Marca o início de um novo ciclo"""
        now = datetime.now()
        
        if self.cycle_count > 0:
            elapsed = now - self.last_cycle_start
            
            # Verificar se o ciclo tomou tempo demais
            if elapsed > self.expected_interval * 1.5:  # 50% mais que o esperado
                logger.warning(
                    f"Cycle #{self.cycle_count} took {elapsed.total_seconds():.0f}s "
                    f"(expected ~{self.expected_interval.total_seconds():.0f}s)"
                )
        
        self.last_cycle_start = now
        self.cycle_count += 1
        logger.debug(f"Cycle #{self.cycle_count} started at {now.isoformat()}")
    
    def mark_cycle_end(self):
        """Marca o fim do ciclo"""
        elapsed = datetime.now() - self.last_cycle_start
        logger.debug(f"Cycle #{self.cycle_count} completed in {elapsed.total_seconds():.2f}s")
