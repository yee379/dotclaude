## SQL Injection

Always use parameterised queries or ORM. Never concatenate user input into SQL.

```python
# BAD
query = f"SELECT * FROM users WHERE email = '{email}'"
await db.execute(query)

# GOOD: ORM or parameterised
user = await db.execute(select(User).where(User.email == email))
# or raw SQL with params
await db.execute(text("SELECT * FROM users WHERE email = :email"), {"email": email})
```

## Command Injection

Never use `shell=True` with user-controlled input.

```python
# BAD
import subprocess
result = subprocess.run(f"convert {filename} output.jpg", shell=True)

# GOOD: no shell=True, explicit args
result = subprocess.run(["convert", filename, "output.jpg"], shell=False, check=True)
```

## Path Traversal

Strip directory components and verify resolved path stays inside base dir.

```python
from pathlib import Path

BASE_DIR = Path("/app/uploads")

def safe_upload_path(filename: str) -> Path:
    safe_name = Path(filename).name
    path = BASE_DIR / safe_name
    path.resolve().relative_to(BASE_DIR.resolve())
    return path
```

## Input Validation with Pydantic

```python
from pydantic import BaseModel, EmailStr, Field, field_validator

class CreateUserRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    role: UserRole
    age: int = Field(ge=0, le=150)

    @field_validator("name")
    @classmethod
    def name_no_html(cls, v: str) -> str:
        if "<" in v or ">" in v:
            raise ValueError("Name must not contain HTML")
        return v.strip()
```

## Checklist

- [ ] All user inputs validated with schema (Pydantic, marshmallow, etc.)
- [ ] No SQL string concatenation — ORM or parameterised queries only
- [ ] No `shell=True` with user-controlled input
- [ ] File paths sanitised — no directory traversal
- [ ] File uploads validated: size limit, MIME type, extension allowlist
- [ ] HTML/template output escaped — no raw user content rendered as HTML
