import os
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    """Configuration settings for the bot"""

    # Discord Configuration
    DISCORD_TOKEN: str
    CLIENT_ID: str
    GUILD_ID: Optional[str] = None
    SIGNAL_CHANNEL_ID: Optional[str] = None
    COMMAND_PREFIX: str = "/"

    # API Keys
    BINANCE_API_KEY: Optional[str] = None
    BINANCE_SECRET_KEY: Optional[str] = None
    DEXSCREENER_API_URL: str = "https://api.dexscreener.com/latest"
    POLYMARKET_API_URL: str = "https://gamma-api.polymarket.com"
    POLYMARKET_API_KEY: Optional[str] = None
    GEMINI_API_KEY: Optional[str] = None
    CLAUDE_API_KEY: Optional[str] = None

    # Rate Limiting
    RATE_LIMIT_WINDOW: int = 60000  # 1 minute in ms
    RATE_LIMIT_MAX_REQUESTS: int = 10
    ANALYSIS_COOLDOWN: int = 30  # seconds

    # Cache Configuration
    CACHE_TTL: int = 60  # seconds
    MAX_CACHE_SIZE: int = 1000

    # Database Configuration
    DATABASE_URL: Optional[str] = None
    REDIS_URL: Optional[str] = None
    
    # PostgreSQL Configuration
    POSTGRES_HOST: Optional[str] = None
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: Optional[str] = None
    POSTGRES_USER: Optional[str] = None
    POSTGRES_PASSWORD: Optional[str] = None

    # Trading Configuration
    DEFAULT_TIMEFRAME: str = "15m"
    SUPPORTED_TIMEFRAMES: list = ["1m", "5m", "15m", "30m", "1h", "4h", "1d", "1w"]
    DEFAULT_LIMIT: int = 500
    MAX_LIMIT: int = 1000

    # Analysis Configuration
    ENABLE_AI_ANALYSIS: bool = True
    ENABLE_POLYMARKET: bool = True
    ENABLE_CACHING: bool = True
    ENABLE_ADVANCED_INDICATORS: bool = True

    # Risk Management
    MAX_POSITION_SIZE: float = 0.1  # 10% of portfolio
    MIN_LIQUIDITY_USD: int = 10000
    MAX_VOLATILITY: float = 50.0  # 50%

    # Performance
    CONCURRENT_REQUESTS: int = 10
    REQUEST_TIMEOUT: int = 30  # seconds
    MAX_RETRIES: int = 3

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "logs/bot.log"
    LOG_ROTATION: str = "1 day"
    LOG_RETENTION: str = "30 days"

    # Feature Flags
    ENABLE_PAPER_TRADING: bool = False
    ENABLE_ALERTS: bool = False
    ENABLE_AUTO_ANALYSIS: bool = False

    # Channels and Roles
    ANALYSIS_CHANNELS: list = []
    MODERATOR_ROLES: list = []
    PREMIUM_ROLES: list = []
    
    # Discord App Configuration URLs
    DISCORD_INTERACTIONS_ENDPOINT_URL: Optional[str] = None
    DISCORD_LINKED_ROLES_VERIFICATION_URL: Optional[str] = None
    DISCORD_TERMS_OF_SERVICE_URL: Optional[str] = None
    DISCORD_PRIVACY_POLICY_URL: Optional[str] = None

    # Security
    MAX_ANALYSIS_PER_HOUR: int = 100
    BLOCKED_USERS: list = []
    ALLOWED_GUILDS: list = []

    class Config:
        env_file = ".env"
        case_sensitive = True

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._validate()

    def _validate(self):
        """Validate configuration"""
        if not self.DISCORD_TOKEN:
            raise ValueError("DISCORD_TOKEN is required")

        if not self.CLIENT_ID:
            raise ValueError("CLIENT_ID is required")

        # Validate timeframe
        if self.DEFAULT_TIMEFRAME not in self.SUPPORTED_TIMEFRAMES:
            self.DEFAULT_TIMEFRAME = "15m"

        # Ensure log directory exists
        os.makedirs(os.path.dirname(self.LOG_FILE), exist_ok=True)

        # Parse channels and roles from comma-separated strings
        if isinstance(self.ANALYSIS_CHANNELS, str):
            self.ANALYSIS_CHANNELS = [c.strip() for c in self.ANALYSIS_CHANNELS.split(",")]
        if isinstance(self.MODERATOR_ROLES, str):
            self.MODERATOR_ROLES = [r.strip() for r in self.MODERATOR_ROLES.split(",")]
        if isinstance(self.PREMIUM_ROLES, str):
            self.PREMIUM_ROLES = [r.strip() for r in self.PREMIUM_ROLES.split(",")]
        if isinstance(self.BLOCKED_USERS, str):
            self.BLOCKED_USERS = [int(u.strip()) for u in self.BLOCKED_USERS.split(",") if u.strip().isdigit()]
        if isinstance(self.ALLOWED_GUILDS, str):
            self.ALLOWED_GUILDS = [int(g.strip()) for g in self.ALLOWED_GUILDS.split(",") if g.strip().isdigit()]