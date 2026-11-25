from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str
    # HS256 needs a key at least as long as its 256-bit output to be secure.
    SECRET_KEY: str = Field(min_length=32)
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 14
    # Set True in production (HTTPS) so the refresh cookie is never sent over
    # plain HTTP.
    SESSION_HTTPS_ONLY: bool = False
    # Interactive docs at /api/docs; off in production so the API isn't advertised.
    ENABLE_API_DOCS: bool = False

    @field_validator("DATABASE_URL")
    @classmethod
    def use_sqlalchemy_scheme(cls, url: str) -> str:
        """Some hosts, such as Heroku, hand out postgres:// URLs, a scheme
        SQLAlchemy 2 no longer accepts."""
        if url.startswith("postgres://"):
            return "postgresql://" + url.removeprefix("postgres://")
        return url


settings = Settings()
