# Testing

## Framework
- **pytest** with pytest-asyncio
- **Configuration**: `pytest.ini`

## Test Structure
- Backend: `/apps/orchestrator_3_stream/backend/tests/`
- Files: `test_database.py`, `test_agent_events.py`

## Mocking Approach
- **NO Mocking** of databases or Claude SDK (per CLAUDE.md)
- Use real connections with ephemeral data
- Integration tests marked with `@pytest.mark.integration`

## Running Tests
```bash
# All tests
uv run pytest tests/ -v

# Specific file
uv run pytest tests/test_database.py -v

# Integration tests
uv run pytest tests/ -v --integration
```

## Key Patterns
- Ephemeral test data (setup → test → teardown)
- Session-scoped fixtures for expensive setup
- Real database connections
