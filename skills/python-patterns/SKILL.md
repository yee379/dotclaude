---
name: python-patterns
description: Pythonic idioms, type hints, async patterns, project structure, testing with pytest, dependency management with uv/pyproject.toml, and best practices for building robust backend Python applications.
license: MIT
compatibility: opencode
---

# Python Patterns

Idiomatic Python for backend services — type safety, async, clean project layout, and testing discipline.

## When to Use

- Writing new Python code or reviewing existing code
- Setting up a new Python project or service
- Adding type hints, async patterns, or error handling
- Structuring packages, imports, or configuration
- Writing or improving tests with pytest

---

## Core Idioms

### Type hints everywhere

```python
# Python 3.10+ — use built-in generics, | for Union
from collections.abc import Sequence, Iterator
from pathlib import Path

def get_active_users(users: list[User]) -> list[User]:
    return [u for u in users if u.is_active]

def find_user(user_id: str) -> User | None:
    return db.users.get(user_id)

def process_file(path: Path) -> Iterator[str]:
    with path.open() as f:
        yield from (line.strip() for line in f)
```

### Dataclasses and Pydantic models

```python
from dataclasses import dataclass, field
from datetime import datetime, timezone

# Internal data containers — use dataclasses
@dataclass
class UserEvent:
    user_id: str
    event_type: str
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, str] = field(default_factory=dict)

# API input/output — use Pydantic
from pydantic import BaseModel, EmailStr, Field

class CreateUserRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    role: UserRole = UserRole.MEMBER

class UserResponse(BaseModel):
    id: str
    name: str
    email: str
    role: UserRole
    created_at: datetime

    model_config = {"from_attributes": True}  # ORM mode
```

### Exception hierarchy

```python
class AppError(Exception):
    """Base for all application errors."""

class NotFoundError(AppError):
    def __init__(self, resource: str, id: str) -> None:
        super().__init__(f"{resource} not found: {id}")
        self.resource = resource
        self.id = id

class ValidationError(AppError):
    def __init__(self, field: str, message: str) -> None:
        super().__init__(f"{field}: {message}")
        self.field = field

class UnauthorizedError(AppError):
    pass

# Usage — chain exceptions to preserve traceback
def get_user(user_id: str) -> User:
    try:
        return db.users.get(user_id)
    except DatabaseError as e:
        raise NotFoundError("User", user_id) from e
```

### Context managers for resource cleanup

```python
from contextlib import asynccontextmanager, contextmanager

@contextmanager
def db_transaction(conn):
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise

@asynccontextmanager
async def managed_client(url: str):
    client = await create_client(url)
    try:
        yield client
    finally:
        await client.close()
```

---

## Async Patterns

### FastAPI service structure

```python
from fastapi import FastAPI, Depends, HTTPException, status
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await db.connect()
    await cache.connect()
    yield
    # Shutdown
    await db.disconnect()
    await cache.disconnect()

app = FastAPI(lifespan=lifespan)

# Dependency injection
async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    user = await auth_service.verify_token(token)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    return user

@app.post("/users", response_model=UserResponse, status_code=201)
async def create_user(
    body: CreateUserRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    if current_user.role != Role.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    user = await user_service.create(db, body)
    return UserResponse.model_validate(user)
```

### Concurrent async operations

```python
import asyncio

# Run independent coroutines concurrently
async def enrich_order(order_id: str) -> EnrichedOrder:
    order, user, items = await asyncio.gather(
        order_repo.get(order_id),
        user_repo.get_by_order(order_id),
        item_repo.list_by_order(order_id),
    )
    return EnrichedOrder(order=order, user=user, items=items)

# Bounded concurrency — avoid overwhelming downstream services
async def process_batch(ids: list[str], concurrency: int = 10) -> list[Result]:
    semaphore = asyncio.Semaphore(concurrency)

    async def process_one(id: str) -> Result:
        async with semaphore:
            return await process(id)

    return await asyncio.gather(*(process_one(id) for id in ids))
```

### Background tasks

```python
# FastAPI BackgroundTasks (lightweight, in-process)
from fastapi import BackgroundTasks

@app.post("/orders")
async def create_order(body: CreateOrderRequest, bg: BackgroundTasks) -> OrderResponse:
    order = await order_service.create(body)
    bg.add_task(send_confirmation_email, order.id)
    bg.add_task(notify_warehouse, order.id)
    return OrderResponse.model_validate(order)

# Celery / ARQ for durable background jobs (prefer for prod)
from arq import create_pool

async def send_email_task(ctx, order_id: str) -> None:
    await email_service.send_confirmation(order_id)
```

---

## Project Structure

```
src/
└── myservice/
    ├── __init__.py
    ├── main.py              # FastAPI app + lifespan
    ├── config.py            # Settings via pydantic-settings
    ├── dependencies.py      # FastAPI Depends() factories
    ├── api/
    │   ├── __init__.py
    │   ├── users.py         # router per resource
    │   ├── orders.py
    │   └── health.py
    ├── domain/
    │   ├── __init__.py
    │   ├── models.py        # domain entities (dataclasses)
    │   └── exceptions.py
    ├── services/
    │   ├── __init__.py
    │   ├── user_service.py
    │   └── order_service.py
    ├── repositories/
    │   ├── __init__.py
    │   ├── user_repo.py
    │   └── order_repo.py
    └── infra/
        ├── __init__.py
        ├── database.py
        └── cache.py
tests/
├── conftest.py
├── unit/
└── integration/
pyproject.toml
```

### Configuration with pydantic-settings

```python
# config.py
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import PostgresDsn, RedisDsn

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    database_url: PostgresDsn
    redis_url: RedisDsn
    secret_key: str
    environment: str = "development"
    log_level: str = "INFO"
    allowed_origins: list[str] = []

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

# Singleton — validated at import time, fails fast
settings = Settings()
```

---

## Testing with pytest

### conftest.py patterns

```python
# tests/conftest.py
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"

@pytest_asyncio.fixture(scope="function")
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with AsyncSession(engine) as session:
        yield session
    await engine.dispose()

@pytest_asyncio.fixture
async def client(db_session):
    app.dependency_overrides[get_db] = lambda: db_session
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()

@pytest.fixture
def user_factory(db_session):
    async def _create(**kwargs):
        defaults = {"name": "Test User", "email": "test@example.com", "role": Role.MEMBER}
        user = User(**{**defaults, **kwargs})
        db_session.add(user)
        await db_session.commit()
        return user
    return _create
```

### Test patterns

```python
# tests/unit/test_user_service.py
import pytest

@pytest.mark.asyncio
async def test_create_user_returns_user(db_session, user_factory):
    request = CreateUserRequest(name="Alice", email="alice@example.com", role=Role.ADMIN)
    user = await user_service.create(db_session, request)
    assert user.id is not None
    assert user.email == "alice@example.com"

@pytest.mark.asyncio
async def test_create_user_duplicate_email_raises(db_session, user_factory):
    await user_factory(email="alice@example.com")
    with pytest.raises(ValidationError, match="email"):
        await user_service.create(db_session, CreateUserRequest(
            name="Alice 2", email="alice@example.com", role=Role.MEMBER
        ))

# tests/integration/test_users_api.py
@pytest.mark.asyncio
async def test_create_user_requires_admin(client, user_factory):
    member = await user_factory(role=Role.MEMBER)
    response = await client.post(
        "/users",
        json={"name": "Bob", "email": "bob@example.com", "role": "MEMBER"},
        headers={"Authorization": f"Bearer {make_token(member)}"},
    )
    assert response.status_code == 403

@pytest.mark.asyncio
async def test_create_user_success(client, user_factory):
    admin = await user_factory(role=Role.ADMIN)
    response = await client.post(
        "/users",
        json={"name": "Bob", "email": "bob@example.com", "role": "MEMBER"},
        headers={"Authorization": f"Bearer {make_token(admin)}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "bob@example.com"
```

---

## Tooling

### pyproject.toml

```toml
[project]
name = "myservice"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.110",
    "uvicorn[standard]>=0.29",
    "pydantic>=2.6",
    "pydantic-settings>=2.2",
    "sqlalchemy[asyncio]>=2.0",
    "asyncpg>=0.29",
]

[project.optional-dependencies]
dev = [
    "pytest>=8",
    "pytest-asyncio>=0.23",
    "pytest-cov>=5",
    "httpx>=0.27",
    "aiosqlite>=0.20",
    "ruff>=0.4",
    "mypy>=1.9",
]

[tool.ruff]
line-length = 100
target-version = "py311"
select = ["E", "F", "I", "N", "UP", "B", "SIM", "ANN"]
ignore = ["ANN101", "ANN102"]

[tool.mypy]
python_version = "3.11"
strict = true
ignore_missing_imports = true

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
addopts = "--cov=src --cov-report=term-missing --cov-fail-under=80"
```

### Essential commands

```bash
# Package management (uv is fastest)
uv sync                    # install all deps
uv add fastapi             # add dependency
uv add --dev pytest        # add dev dependency

# Code quality
ruff check . --fix         # lint + auto-fix
ruff format .              # format
mypy src/                  # type check

# Testing
pytest                     # run all tests
pytest tests/unit/         # unit only
pytest -k "test_create"    # filter by name
pytest --cov=src --cov-report=html

# Run service
uvicorn myservice.main:app --reload --port 8000
```

---

## Anti-Patterns to Avoid

```python
# BAD: mutable default argument
def add_tag(item, tags=[]):
    tags.append(item)
    return tags       # shares list across calls!

# GOOD
def add_tag(item, tags: list[str] | None = None) -> list[str]:
    if tags is None:
        tags = []
    tags.append(item)
    return tags

# BAD: bare except
try:
    result = risky()
except:
    pass              # swallows KeyboardInterrupt, SystemExit

# GOOD
try:
    result = risky()
except SpecificError as e:
    logger.error("Operation failed: %s", e)
    raise

# BAD: string formatting in logging (evaluated even if not logged)
logger.debug("Processing user: " + str(user))

# GOOD: lazy formatting
logger.debug("Processing user: %s", user)

# BAD: type() for isinstance checks
if type(value) == list:
    ...

# GOOD
if isinstance(value, list):
    ...

# BAD: synchronous code in async function
async def get_data():
    time.sleep(1)    # blocks the event loop!
    return fetch()

# GOOD
async def get_data():
    await asyncio.sleep(1)
    return await fetch()
```
