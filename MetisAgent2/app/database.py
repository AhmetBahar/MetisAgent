"""
Database Manager - SQLite tabanlı kullanıcı ve memory yönetimi
ChromaDB'den SQLite'a geçiş (Backward compatibility için import redirect)
"""

# SQLite versiyonunu import et
from .database_sqlite import DatabaseManager, db_manager

# Legacy ChromaDB kullanımı için warning
import logging
logger = logging.getLogger(__name__)
logger.warning("database.py deprecated, database_sqlite.py kullanılıyor")

# Backward compatibility için export
__all__ = ['DatabaseManager', 'db_manager']