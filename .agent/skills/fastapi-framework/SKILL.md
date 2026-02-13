---
name: fastapi-framework
description: FastAPI 0.110+ standards — Pydantic models, dependency injection, async endpoints, OpenAPI, security, and Django comparison patterns
---

# FastAPI Framework Standards

## Version & Setup
- **FastAPI**: 0.110+
- **Python**: 3.12+
- **Server**: Uvicorn (+ Gunicorn for production)

---

## Project Structure
```
src/
├── app/
│   ├── main.py               # FastAPI app, CORS, exception handlers
│   ├── config.py              # pydantic-settings based config
│   ├── dependencies.py        # Shared dependencies
│   ├── api/
│   │   ├── v1/
│   │   │   ├── router.py      # Aggregate router
│   │   │   ├── users.py       # User endpoints
│   │   │   └── portfolios.py
│   ├── models/
│   │   ├── user.py            # SQLAlchemy models
│   │   └── portfolio.py
│   ├── schemas/
│   │   ├── user.py            # Pydantic request/response
│   │   └── portfolio.py
│   ├── services/
│   │   └── user_service.py
│   ├── db/
│   │   ├── session.py         # Async session factory
│   │   └── migrations/
│   └── middleware/
│       ├── auth.py
│       └── logging.py
```

---

## Pydantic Models

```python
from pydantic import BaseModel, Field, EmailStr, ConfigDict

class UserCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8)

class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    email: str
    created_at: datetime

class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    pages: int
```

---

## Endpoints

```python
from fastapi import APIRouter, Depends, HTTPException, status, Query

router = APIRouter(prefix="/users", tags=["Users"])

@router.post("/", status_code=status.HTTP_201_CREATED, response_model=UserResponse)
async def create_user(
    data: UserCreate,
    service: UserService = Depends(get_user_service),
) -> UserResponse:
    """Create a new user account."""
    existing = await service.find_by_email(data.email)
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")
    return await service.create(data)

@router.get("/", response_model=PaginatedResponse[UserResponse])
async def list_users(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    service: UserService = Depends(get_user_service),
):
    return await service.list_paginated(page, size)
```

---

## Dependency Injection

```python
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        yield session

async def get_user_service(db: AsyncSession = Depends(get_db)) -> UserService:
    return UserService(UserRepository(db))

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    payload = decode_jwt(token)
    user = await db.get(User, payload["sub"])
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return user
```

---

## Error Handling

```python
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI()

class AppError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 400):
        self.code = code
        self.message = message
        self.status_code = status_code

@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": exc.code, "message": exc.message, "timestamp": datetime.utcnow().isoformat()},
    )
```

---

## Security

```python
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")

async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    return await get_user(payload["sub"])
```

---

## Testing

```python
import pytest
from httpx import AsyncClient, ASGITransport

@pytest.fixture
async def client(app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

@pytest.mark.asyncio
async def test_create_user(client: AsyncClient):
    response = await client.post("/api/v1/users/", json={
        "name": "John", "email": "john@test.com", "password": "secure123"
    })
    assert response.status_code == 201
    assert response.json()["email"] == "john@test.com"
```

---

## Key Libraries

| Library | Purpose |
|---|---|
| fastapi | Web framework |
| pydantic / pydantic-settings | Validation, config |
| uvicorn | ASGI server |
| sqlalchemy[asyncio] | Async ORM |
| alembic | Migrations |
| python-jose[cryptography] | JWT |
| passlib[bcrypt] | Password hashing |
| httpx | Async test client |
| structlog | Structured logging |
