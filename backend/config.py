from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    """
    All app config lives here.
    Values are auto loaded from .env
    Var names are CASE-INSENSITIVE - database_url matches DATABASE_URL in .env
    """

    # db
    database_url: str = "postgresql+asyncpg://hastelink:localdev@localhost:5432/haste_link"

    # S3 / MinIO
    s3_endpoint_url: str | None = None
    s3_bucket: str = "haste-link"
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_region: str = "us-east-1"

    # auth
    secret_key: str = "changemelater"
    access_token_expire_minutes: int = 480 # 8hrs

    # CORS
    allowed_origins: str = "http://localhost:5173"

    # admin seed
    admin_email: str = ""
    admin_password: str = ""

    # upload limits
    max_upload_size_mb: int = 50
    allowed_file_types: str = "application/pdf, image/png, image/jpeg"

    # cache
    cache_ttl_seconds: int = 5

    # fwd to pydantic
    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    # helper
    @property
    def allowed_origins_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",")]

    @property
    def allowed_file_types_list(self) -> list[str]:
        return [t.strip() for t in self.allowed_file_types.split(",")]

    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024
    
@lru_cache
def get_settings() -> Settings:
    """
    Returns a cached Settings instance.
    @lru_cache means this function only runs once — after that,
    it returns the same object every time. This avoids reading
    the .env file on every request.
    """
    return Settings()