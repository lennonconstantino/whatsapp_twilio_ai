"""
Logging utilities.
Configures structured logging for the application.
"""

import logging
import sys
from typing import Any

import re
from typing import Any, Dict

import structlog

from src.core.config import settings

import os
import colorama

# Regex patterns for PII
EMAIL_REGEX = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
CPF_REGEX = re.compile(r'\b\d{3}\.\d{3}\.\d{3}-\d{2}\b')
PHONE_REGEX = re.compile(r'\b\+?[1-9]\d{1,14}\b') 

class PIIMaskingProcessor:
    """
    Structlog processor that masks PII (Email, CPF, Phone) in log events.
    """
    def __call__(self, logger: Any, method_name: str, event_dict: Dict[str, Any]) -> Dict[str, Any]:
        for key, value in event_dict.items():
            if isinstance(value, str):
                # Mask Email
                value = EMAIL_REGEX.sub('[EMAIL_REDACTED]', value)
                # Mask CPF
                value = CPF_REGEX.sub('[CPF_REDACTED]', value)
                # Mask Phone (be careful with IDs, but this regex expects 10-15 digits)
                # We can be more conservative or specific if needed.
                # For now, let's skip phone masking on keys that look like IDs
                if 'id' not in key.lower() and 'uuid' not in key.lower():
                     if PHONE_REGEX.search(value):
                        # Simple heuristic: if it looks like a phone and key suggests it
                        if any(k in key.lower() for k in ['phone', 'mobile', 'celular', 'telefone', 'whatsapp', 'from', 'to']):
                             value = PHONE_REGEX.sub('[PHONE_REDACTED]', value)
                
                event_dict[key] = value
        return event_dict

# Inicializar colorama
# Se FORCE_COLOR=true, forçamos strip=False para manter cores mesmo em arquivos/pipes
force_color = os.getenv("FORCE_COLOR", "false").lower() == "true"
colorama.init(autoreset=True, strip=False if force_color else None)

class ColoredConsoleRenderer:
    """
    Renderizador customizado que adiciona cores ao output do structlog em dev.
    """
    
    LEVEL_COLORS = {
        'debug': colorama.Fore.CYAN,
        'info': colorama.Fore.GREEN,
        'warning': colorama.Fore.YELLOW,
        'error': colorama.Fore.RED,
        'critical': colorama.Fore.RED + colorama.Style.BRIGHT,
    }
    FG_MAP = {
        'black': colorama.Fore.BLACK,
        'red': colorama.Fore.RED,
        'green': colorama.Fore.GREEN,
        'yellow': colorama.Fore.YELLOW,
        'blue': colorama.Fore.BLUE,
        'magenta': colorama.Fore.MAGENTA,
        'cyan': colorama.Fore.CYAN,
        'white': colorama.Fore.WHITE,
    }
    BG_MAP = {
        'black': colorama.Back.BLACK,
        'red': colorama.Back.RED,
        'green': colorama.Back.GREEN,
        'yellow': colorama.Back.YELLOW,
        'blue': colorama.Back.BLUE,
        'magenta': colorama.Back.MAGENTA,
        'cyan': colorama.Back.CYAN,
        'white': colorama.Back.WHITE,
    }
    STYLE_MAP = {
        'bright': colorama.Style.BRIGHT,
        'dim': colorama.Style.DIM,
        'normal': colorama.Style.NORMAL,
    }
    
    def __call__(self, logger, method_name, event_dict):
        """
        Renderiza o log com cores.
        """
        level = event_dict.get('level', 'info').lower()
        color_override = event_dict.pop('color', None) or event_dict.pop('fg', None)
        bg_override = event_dict.pop('bg', None)
        style_override = event_dict.pop('style', None)
        base_color = self.LEVEL_COLORS.get(level, colorama.Fore.WHITE)
        if color_override:
            base_color = self.FG_MAP.get(str(color_override).lower(), base_color)
        bg = self.BG_MAP.get(str(bg_override).lower(), "")
        style = self.STYLE_MAP.get(str(style_override).lower(), "")
        color = f"{bg}{style}{base_color}"
        
        # Extrair informações principais
        timestamp = event_dict.pop('timestamp', '')
        logger_name = event_dict.pop('logger', '')
        event = event_dict.pop('event', '')
        
        # Montar a mensagem base
        parts = []
        if timestamp:
            parts.append(f"{colorama.Fore.WHITE}{timestamp}")
        if logger_name:
            parts.append(f"{colorama.Fore.MAGENTA}{logger_name}")
        parts.append(f"{color}{level.upper()}")
        parts.append(f"{color}{event}")
        
        # Renderizar pares chave-valor estruturados com destaque
        for k, v in event_dict.items():
            key_style = colorama.Fore.CYAN + colorama.Style.DIM
            eq_style = colorama.Fore.WHITE + colorama.Style.DIM
            val_style = colorama.Fore.GREEN
            
            parts.append(f"{key_style}{k}{eq_style}={val_style}{v}{colorama.Style.RESET_ALL}")

        return ' '.join(parts) + colorama.Style.RESET_ALL


_configured = False


def configure_logging():
    """
    Configure structured logging for the application.
    """
    global _configured
    if _configured:
        return

    # Configure structlog
    shared_processors = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        PIIMaskingProcessor(),
    ]
    
    # Escolher renderizador baseado no ambiente
    if settings.api.environment == "development" or settings.api.debug:
        # Em dev, usa renderizador colorido
        renderer = ColoredConsoleRenderer()
    else:
        # Em prod, usa JSON
        renderer = structlog.processors.JSONRenderer()

    # Configure structlog
    structlog.configure(
        processors=shared_processors + [renderer],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Configure standard logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.log.level.upper()),
    )
    
    _configured = True


def get_logger(name: str) -> Any:
    """
    Get a structured logger instance.
    Automatically configures logging if not yet configured.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Structured logger instance
    """
    if not _configured:
        configure_logging()
    return structlog.get_logger(name)
