from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://permitai:permitai@localhost:5432/permitai"
    DATABASE_URL_SYNC: str = "postgresql://permitai:permitai@localhost:5432/permitai"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Data Sources
    SOCRATA_APP_TOKEN: str = ""
    SOCRATA_DATASET_ID: str = "hbkd-qubn"

    # AI
    ANTHROPIC_API_KEY: str = ""

    # AWS
    AWS_REGION: str = "us-west-2"
    S3_BUCKET_DOCUMENTS: str = "permitai-documents-dev"
    S3_BUCKET_DEAD_LETTERS: str = "permitai-dead-letters-dev"

    # Auth
    ANGELENO_OAUTH_CLIENT_ID: str = ""
    ANGELENO_OAUTH_CLIENT_SECRET: str = ""
    ANGELENO_OAUTH_JWKS_URL: str = ""
    ANGELENO_OAUTH_ISSUER: str = ""
    MOCK_AUTH: bool = False

    # Firebase
    FIREBASE_PROJECT_ID: str = ""
    FIREBASE_CREDENTIALS_PATH: str = ""

    # Twilio
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_FROM_NUMBER: str = ""

    # Monitoring
    SENTRY_DSN: str = ""

    # App
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "DEBUG"
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:8081"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


settings = Settings()
