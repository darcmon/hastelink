from pydantic import BaseModel

class LoginRequest(BaseModel):
    email: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class AdminUserResponse(BaseModel):
    email: str
    display_name: str

    model_config = {"from_attributes": True}


