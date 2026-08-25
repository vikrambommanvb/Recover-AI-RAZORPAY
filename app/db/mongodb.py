from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings
from app.core.logging import logger
from typing import Optional

class Database:
    def __init__(self):
        self.client: Optional[AsyncIOMotorClient] = None
        self.db = None

    async def connect(self):
        """Initialize connection to MongoDB."""
        if not settings.MONGODB_URI:
            logger.warning("MONGODB_URI is not set. Database connections will not be established.")
            return
        
        try:
            logger.info("Connecting to MongoDB...")
            self.client = AsyncIOMotorClient(
                settings.MONGODB_URI,
                serverSelectionTimeoutMS=2000  # Fail fast if connection fails
            )
            self.db = self.client[settings.MONGODB_DATABASE]
            # Verify connection works
            await self.client.admin.command("ping")
            logger.info(f"Connected to MongoDB database: {settings.MONGODB_DATABASE}")
        except Exception as e:
            logger.error(f"Could not connect to MongoDB on startup: {e}")
            # Keep client initialized but don't crash, allowing /health to function

    async def close(self):
        """Close connection to MongoDB."""
        if self.client:
            self.client.close()
            logger.info("Closed MongoDB connection.")
            self.client = None
            self.db = None

db = Database()

async def get_database():
    """Dependency to retrieve the database instance."""
    if db.db is None:
        # Check if config is present first to throw clear config error
        settings.check_mongodb_config()
        raise RuntimeError("MongoDB connection not initialized.")
    return db.db
