from pydantic import BaseModel

class Token(BaseModel):
    """Token schema.
    
    Attributes:
        access_token: JWT access token
        token_type: Token type (usually "bearer")
    """
    access_token: str
    token_type: str

class TokenPayload(BaseModel):
    """Token payload schema.
    
    Attributes:
        sub: Subject (usually user ID)
    """
    sub: str | None = None 