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
            logger.warning("WARNING: Falling back to offline in-memory MockDatabase client.")
            from app.db.mock_db import MockDatabase
            self.db = MockDatabase()


    async def init_indexes(self):
        """Create necessary indexes for payments and recovery cases."""
        if self.db is None:
            logger.warning("Database not connected. Cannot initialize indexes.")
            return
        try:
            from app.db.collections import (
                PAYMENTS_COLLECTION, 
                RECOVERY_CASES_COLLECTION,
                AGENT_DECISIONS_COLLECTION,
                AUDIT_LOGS_COLLECTION,
                RECOVERY_ACTIONS_COLLECTION,
                WEBHOOK_EVENTS_COLLECTION,
                EVALUATION_RUNS_COLLECTION,
                EVALUATION_RESULTS_COLLECTION
            )
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
            # Indexes on agent decisions
            await self.db[AGENT_DECISIONS_COLLECTION].create_index("case_id")
            await self.db[AGENT_DECISIONS_COLLECTION].create_index("payment_id")
            # Indexes on audit logs
            await self.db[AUDIT_LOGS_COLLECTION].create_index("entity_id")
            await self.db[AUDIT_LOGS_COLLECTION].create_index("timestamp")
            # Indexes on recovery actions
            await self.db[RECOVERY_ACTIONS_COLLECTION].create_index("action_id", unique=True)
            await self.db[RECOVERY_ACTIONS_COLLECTION].create_index("case_id")
            await self.db[RECOVERY_ACTIONS_COLLECTION].create_index("payment_id")
            # Indexes on webhook events
            await self.db[WEBHOOK_EVENTS_COLLECTION].create_index("event_id", unique=True)
            # Indexes on evaluation runs
            await self.db[EVALUATION_RUNS_COLLECTION].create_index("evaluation_id", unique=True)
            # Indexes on evaluation results
            await self.db[EVALUATION_RESULTS_COLLECTION].create_index("evaluation_id")
            await self.db[EVALUATION_RESULTS_COLLECTION].create_index("case_id")
            await self.db[EVALUATION_RESULTS_COLLECTION].create_index("payment_id")
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
