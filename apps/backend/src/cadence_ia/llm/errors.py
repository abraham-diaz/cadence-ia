class LLMUnavailable(Exception):
    """The LLM can't be used (no API key, quota exceeded, network...)."""
