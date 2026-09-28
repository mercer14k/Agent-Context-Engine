class EngineError(Exception):
    """Expected safe error suitable for a local operator."""

class ValidationError(EngineError):
    pass

class AccessDenied(EngineError):
    pass

class ReferenceUnavailable(EngineError):
    pass
