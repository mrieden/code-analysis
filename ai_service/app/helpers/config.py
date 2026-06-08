from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """App settings.

    Only the LLM-related keys are consumed through this object. Auth/DB keys
    (GITHUB_CLIENT_ID, GITHUB_CLIENT_SECRET, JWT_SECRET, MONGODB_URL, DB_NAME,
    FRONTEND_URL, HUGGINGFACE_API_KEY, SERPAPI_API_KEY, ...) are read elsewhere
    via os.getenv, so unknown keys in .env are ignored here instead of being
    rejected.
    """

    # ── LLM secrets (read from .env; default "" so a missing key never
    #    crashes boot — the relevant LLM call will surface a clear error
    #    only if/when it is actually used) ─────────────────────────
    GROQ_API_KEY: str = ""
    OPENROUTER_API_KEY: str = ""

    # ── Models used by the multi-language agent pipeline ──────────
    # Defaulted so the app still boots if your .env doesn't define one
    # (e.g. model3); any value set in your .env overrides the default.
    model1: str = "openrouter/owl-alpha"
    model2: str = "meta-llama/llama-4-scout-17b-16e-instruct"
    model3: str = "llama-3.3-70b-versatile"
    model4: str = "meta-llama/llama-3.3-70b-instruct:free"
    max_iterations: int = 3
    max_improvement_loops: int = 3
    min_gain: float = 0.05
    openai_api_base: str = "https://openrouter.ai/api/v1"

    # ── LangChain / tracing (optional) ────────────────────────────
    LANGSMITH_API_KEY: str = ""
    LANGCHAIN_TRACING_V2: str = "false"
    LANGCHAIN_ENDPOINT: str = "https://api.smith.langchain.com"
    LANGCHAIN_PROJECT: str = "CodeGuard"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


def get_settings():
    return Settings()
