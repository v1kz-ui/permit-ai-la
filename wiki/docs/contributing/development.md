---
sidebar_position: 1
title: Development Guide
---

# Development Guide

## Code Style

### Python (Backend)
- **Formatter:** Ruff (`ruff format`)
- **Linter:** Ruff (`ruff check`) + mypy for type checking
- **Style:** PEP 8, type hints on all public functions
- **Async:** Use `async/await` throughout -- no blocking I/O

```bash
make lint       # Check formatting and types
make lint-fix   # Auto-fix issues
```

### TypeScript (Dashboard / Mobile)
- **Framework:** Next.js 14 App Router conventions
- **Styling:** Tailwind CSS utility classes
- **Components:** Functional components with hooks
- **Types:** Shared type definitions in `shared/types.ts`

## Testing

### Backend Tests

```bash
make test
```

Runs pytest with:
- `pytest-asyncio` for async test support
- Factory Boy for test data generation
- Coverage reporting (XML + terminal)

Test files are in `backend/tests/`.

### Load Testing

Locust load tests are available for performance testing under realistic conditions.

## Project Structure Conventions

- **Services** contain business logic (not route handlers)
- **Schemas** define request/response shapes (Pydantic models)
- **Models** define database structure (SQLAlchemy ORM)
- **Routes** handle HTTP concerns only (validation, auth, response formatting)
- **AI modules** are isolated and independently testable

## Database Changes

1. Modify the SQLAlchemy model in `backend/app/models/`
2. Generate a migration:
   ```bash
   make migration msg="describe your change"
   ```
3. Review the generated migration in `backend/alembic/versions/`
4. Apply:
   ```bash
   make migrate
   ```

## Adding a New Feature

1. Define schemas in `backend/app/schemas/`
2. Create/update models in `backend/app/models/`
3. Implement business logic in `backend/app/services/`
4. Add route handlers in `backend/app/api/v1/`
5. Register routes in `backend/app/api/v1/__init__.py`
6. Add frontend components in `dashboard/src/`
7. Update shared types in `shared/types.ts`
8. Write tests

## Environment Setup

See [Quickstart](/getting-started/quickstart) for full setup instructions.
