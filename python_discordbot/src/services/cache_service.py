import asyncpg
import json
import hashlib
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class CacheService:
    """PostgreSQL-based caching service to reduce API calls"""
    
    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self.pool: Optional[asyncpg.Pool] = None
    
    async def connect(self):
        """Initialize connection pool"""
        try:
            self.pool = await asyncpg.create_pool(
                self.connection_string,
                min_size=2,
                max_size=10,
                command_timeout=60
            )
            logger.info("✅ PostgreSQL cache connection pool created")
        except Exception as e:
            logger.error(f"❌ Failed to connect to PostgreSQL: {e}")
            raise
    
    async def close(self):
        """Close connection pool"""
        if self.pool:
            await self.pool.close()
            logger.info("PostgreSQL cache connection pool closed")
    
    async def initialize_schema(self):
        """Create cache table if not exists"""
        if not self.pool:
            raise RuntimeError("Cache service not connected")
        
        async with self.pool.acquire() as conn:
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS cache (
                    key VARCHAR(255) PRIMARY KEY,
                    data JSONB NOT NULL,
                    expires_at TIMESTAMP NOT NULL,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            ''')
            
            await conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_expires_at ON cache(expires_at)
            ''')
            
            logger.info("✅ Cache schema initialized")
    
    async def get(self, key: str) -> Optional[Dict[str, Any]]:
        """Retrieve cached data by key"""
        if not self.pool:
            return None
        
        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(
                    'SELECT data, expires_at FROM cache WHERE key = $1',
                    key
                )
                
                if not row:
                    logger.debug(f"Cache MISS: {key}")
                    return None
                
                # Check if expired
                if row['expires_at'] < datetime.utcnow():
                    logger.debug(f"Cache EXPIRED: {key}")
                    await self.delete(key)
                    return None
                
                logger.info(f"Cache HIT: {key}")
                return json.loads(row['data'])
        
        except Exception as e:
            logger.error(f"Cache get error for {key}: {e}")
            return None
    
    async def set(self, key: str, data: Dict[str, Any], ttl_seconds: int = 300):
        """Store data in cache with TTL"""
        if not self.pool:
            return
        
        try:
            expires_at = datetime.utcnow() + timedelta(seconds=ttl_seconds)
            data_json = json.dumps(data)
            
            async with self.pool.acquire() as conn:
                await conn.execute('''
                    INSERT INTO cache (key, data, expires_at)
                    VALUES ($1, $2, $3)
                    ON CONFLICT (key) 
                    DO UPDATE SET data = $2, expires_at = $3, created_at = NOW()
                ''', key, data_json, expires_at)
            
            logger.debug(f"Cache SET: {key} (TTL: {ttl_seconds}s)")
        
        except Exception as e:
            logger.error(f"Cache set error for {key}: {e}")
    
    async def delete(self, key: str):
        """Delete cached entry"""
        if not self.pool:
            return
        
        try:
            async with self.pool.acquire() as conn:
                await conn.execute('DELETE FROM cache WHERE key = $1', key)
            logger.debug(f"Cache DELETE: {key}")
        except Exception as e:
            logger.error(f"Cache delete error for {key}: {e}")
    
    async def invalidate_pattern(self, pattern: str):
        """Delete all cache entries matching pattern"""
        if not self.pool:
            return
        
        try:
            async with self.pool.acquire() as conn:
                result = await conn.execute(
                    'DELETE FROM cache WHERE key LIKE $1',
                    f"{pattern}%"
                )
            logger.info(f"Cache INVALIDATE: {pattern}* ({result})")
        except Exception as e:
            logger.error(f"Cache invalidate error for {pattern}: {e}")
    
    async def cleanup_expired(self):
        """Remove expired cache entries"""
        if not self.pool:
            return
        
        try:
            async with self.pool.acquire() as conn:
                result = await conn.execute(
                    'DELETE FROM cache WHERE expires_at < NOW()'
                )
            logger.info(f"Cache cleanup: removed {result} expired entries")
        except Exception as e:
            logger.error(f"Cache cleanup error: {e}")
    
    @staticmethod
    def generate_key(*parts) -> str:
        """Generate cache key from parts"""
        return ":".join(str(p) for p in parts)
    
    @staticmethod
    def hash_data(data: Any) -> str:
        """Generate hash for data (useful for complex objects)"""
        data_str = json.dumps(data, sort_keys=True)
        return hashlib.md5(data_str.encode()).hexdigest()
