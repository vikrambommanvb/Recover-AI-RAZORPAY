import os
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "RecoverAI"
    APP_ENV: str = "development"
    DEBUG: bool = True

    # MongoDB Settings
    MONGODB_URI: Optional[str] = Field(default=None, description="MongoDB Atlas connection URI")
    MONGODB_DATABASE: str = "recoverai"

    # AI Settings
    AI_PROVIDER: str = "groq"
    GROQ_API_KEY: Optional[str] = Field(default=None, description="Groq API key")
    GROQ_MODEL: str = "mixtral-8x7b-32768"

    # Razorpay Settings
    RAZORPAY_KEY_ID: Optional[str] = Field(default=None, description="Razorpay API key ID")
    RAZORPAY_KEY_SECRET: Optional[str] = Field(default=None, description="Razorpay API key secret")
    RAZORPAY_WEBHOOK_SECRET: Optional[str] = Field(default=None, description="Razorpay webhook secret")

    # Safety Bounds Settings
    MAX_RECOVERY_AMOUNT_MINOR: int = Field(default=500000, description="Max recovery amount in minor units (default ₹5,000)")
    MAX_RECOVERY_ATTEMPTS: int = Field(default=2, description="Max recovery attempts allowed per case")
    RECOVERY_COOLDOWN_SECONDS: int = Field(default=300, description="Cooldown duration in seconds between attempts")


    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    def check_mongodb_config(self) -> str:
        """Validate MongoDB configuration when database access is required."""
        if not self.MONGODB_URI:
            raise ValueError(
                "Configuration Error: MONGODB_URI environment variable is required but missing."
            )
        return self.MONGODB_URI

    def check_groq_config(self) -> str:
        """Validate Groq configuration when AI service is required."""
        if not self.GROQ_API_KEY:
            raise ValueError(
                "Configuration Error: GROQ_API_KEY environment variable is required but missing."
            )
        return self.GROQ_API_KEY

    def check_razorpay_config(self) -> tuple[str, str]:
        """Validate Razorpay configuration when payment actions are required."""
        if not self.RAZORPAY_KEY_ID or not self.RAZORPAY_KEY_SECRET:
            raise ValueError(
                "Configuration Error: Both RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET "
                "environment variables are required but missing."
            )
        return self.RAZORPAY_KEY_ID, self.RAZORPAY_KEY_SECRET


# Global settings instance
settings = Settings()
