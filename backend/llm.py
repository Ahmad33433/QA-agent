"""Builds the chat model for the configured provider."""
import config


def _rate_limiter():
    if config.REQUESTS_PER_MINUTE <= 0:
        return None
    from langchain_core.rate_limiters import InMemoryRateLimiter

    return InMemoryRateLimiter(
        requests_per_second=config.REQUESTS_PER_MINUTE / 60, check_every_n_seconds=0.2, max_bucket_size=1
    )


def get_chat_model(model: str):
    options = {"model": model, "timeout": 90, "max_retries": 3, "rate_limiter": _rate_limiter()}
    if config.LLM_PROVIDER == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(**options)
    from langchain_openai import ChatOpenAI

    return ChatOpenAI(**options)
