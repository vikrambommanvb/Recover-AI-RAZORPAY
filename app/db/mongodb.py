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
            
            # Check for certifi to handle macOS certificate issues
            client_kwargs = {
                "serverSelectionTimeoutMS": 2000
            }
            try:
                import certifi
                client_kwargs["tlsCAFile"] = certifi.where()
            except ImportError:
                client_kwargs["tlsAllowInvalidCertificates"] = True
                
            self.client = AsyncIOMotorClient(
                settings.MONGODB_URI,
                **client_kwargs
            )
            self.db = self.client[settings.MONGODB_DATABASE]
            # Verify connection works
            await self.client.admin.command("ping")
            logger.info(f"Connected to MongoDB database: {settings.MONGODB_DATABASE}")
            await self.init_indexes()
        except Exception as e:
            logger.error(f"Could not connect to MongoDB on startup: {e}")
            # Keep client initialized but don't crash, allowing /health to function

    async def init_indexes(self):
        """Create necessary indexes for payments and recovery cases."""
        if self.db is None:
            logger.warning("Database not connected. Cannot initialize indexes.")
            return
        try:
            from app.db.collections import PAYMENTS_COLLECTION, RECOVERY_CASES_COLLECTION
            logger.info("Initializing database indexes...")
            # Unique index on payment_id
            await self.db[PAYMENTS_COLLECTION].create_index("payment_id", unique=True)
            # Index on customer_id
            await self.db[PAYMENTS_COLLECTION].create_index("customer_id")
            # Unique index on payment_id (in recovery cases) to support idempotency
            await self.db[RECOVERY_CASES_COLLECTION].create_index("payment_id", unique=True)
            # Unique index on case_id
            await self.db[RECOVERY_CASES_COLLECTION].create_index("case_id", unique=True)
            # Index on status
            await self.db[RECOVERY_CASES_COLLECTION].create_index("status")
            logger.info("Database indexes successfully initialized.")
        except Exception as e:
            logger.error(f"Failed to create database indexes: {e}")

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
