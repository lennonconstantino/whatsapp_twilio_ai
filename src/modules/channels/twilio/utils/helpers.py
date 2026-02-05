import mimetypes
import os
from typing import Optional

import requests

from src.core.config import settings
from src.core.utils import get_logger

logger = get_logger(__name__)


def download_media(media_type: str, media_url: str) -> Optional[str]:
    """
    Baixa o media do Twilio.
    
    Args:
        media_type: Content-Type da mídia (ex: image/jpeg)
        media_url: URL para download
        
    Returns:
        Caminho do arquivo salvo ou None se falhar
    """
    try:
        # Tenta pegar credenciais das settings, fallback para env vars
        account_sid = settings.twilio.account_sid or os.environ.get("TWILIO_ACCOUNT_SID")
        auth_token = settings.twilio.auth_token or os.environ.get("TWILIO_AUTH_TOKEN")
        
        if not account_sid or not auth_token:
            logger.warning("Twilio credentials missing. Cannot download media.")
            return None

        auth = (account_sid, auth_token)
        media_response = requests.get(media_url, auth=auth, timeout=50)

        # Verificar se o download foi bem-sucedido
        media_response.raise_for_status()

        # Determinar extensão
        ext = mimetypes.guess_extension(media_type)
        if not ext:
            # Fallback simples
            parts = media_type.split("/")
            ext = f".{parts[-1]}" if len(parts) > 1 else ""

        # Nome do arquivo
        original_name = media_url.split("/")[-1]
        # Limpar query params se existirem
        if "?" in original_name:
            original_name = original_name.split("?")[0]
        
        filename = f"{original_name}{ext}" if not original_name.endswith(ext) else original_name

        # Diretório de downloads
        download_dir = "downloads"
        os.makedirs(download_dir, exist_ok=True)
        
        filepath = os.path.join(download_dir, filename)

        # Salvar localmente
        with open(filepath, "wb") as f:
            f.write(media_response.content)

        logger.info(f"Media saved to {filepath}")
        return filepath
        
    except Exception as e:
        logger.error(f"Error downloading media: {e}")
        return None
