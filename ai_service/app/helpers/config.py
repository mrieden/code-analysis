from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # ── Groq ──────────────────────────────────────────────────
    GROQ_API_KEY: str
    HUGGINGFACE_API_KEY: str
    LANGSMITH_API_KEY: str
    SERPAPI_API_KEY: str
    OPENROUTER_API_KEY: str

    # ── LangChain ─────────────────────────────────────────────
    LANGCHAIN_TRACING_V2: str
    LANGCHAIN_ENDPOINT: str
    LANGCHAIN_PROJECT: str

    # ── Models ────────────────────────────────────────────────
    model1: str
    model2: str
    max_iterations: int
    openai_api_base: str

    # ── Auth & DB ─────────────────────────────────────────────
    GITHUB_CLIENT_ID: str
    GITHUB_CLIENT_SECRET: str
    JWT_SECRET: str
    MONGODB_URL: str
    DB_NAME: str
    FRONTEND_URL: str

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore"   # ignore any unknown keys in .env
    )

def get_settings():
    return Settings()
