# Standard Python Service Project Structure

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
├── conftest.py              # see conftest-template.py
├── unit/
└── integration/
pyproject.toml
```

## Layer responsibilities

| Layer | Responsibility |
|-------|---------------|
| `api/` | HTTP routing — thin; validates input, calls service, formats response |
| `domain/` | Pure business entities and exceptions — no I/O |
| `services/` | Orchestration — calls repositories, applies business logic |
| `repositories/` | Data access — all DB queries here; nothing else |
| `infra/` | External infrastructure wiring (DB engine, cache pool) |
| `dependencies.py` | FastAPI `Depends()` factories — session scoping, auth injection |
