"""Exceptions shared by the service layer. main.py maps them to HTTP responses."""


class PdfError(Exception):
    """The PDF is unusable (corrupt, encrypted, ...). The message is safe to show to users."""


class OllamaError(Exception):
    """The local Ollama server could not answer. The message is safe to show to users."""


class AiGenerationError(Exception):
    """The model answered, but the output could not be turned into valid content."""
