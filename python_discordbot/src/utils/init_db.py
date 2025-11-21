import asyncio
import logging
from ..services.cache_service import CacheService
from ..config.settings import Settings

logger = logging.getLogger(__name__)

async def initialize_database(settings: Settings):
    """Initialize database schema and connections"""
    
    # Build PostgreSQL connection string
    if not settings.POSTGRES_HOST:
        logger.warning("⚠️ PostgreSQL not configured, caching disabled")
        return None
    
    connection_string = (
        f"postgresql://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}"
        f"@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"
    )
    
    try:
        cache_service = CacheService(connection_string)
        await cache_service.connect()
        await cache_service.initialize_schema()
        logger.info("✅ Database initialized successfully")
        return cache_service
    
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        logger.warning("⚠️ Continuing without caching")
        return None

if __name__ == "__main__":
    # Standalone script to initialize database
    from dotenv import load_dotenv
    load_dotenv()
    
    settings = Settings()
    asyncio.run(initialize_database(settings))
