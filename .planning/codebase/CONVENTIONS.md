# Code Conventions

## Style
- Python: PEP 8 with type hints, async-first
- TypeScript: Strict mode, explicit types
- Rich console output for logging

## Naming
- Files: snake_case (Python), PascalCase (Vue)
- Classes: PascalCase
- Functions: snake_case (Python), camelCase (TypeScript)
- Constants: UPPER_SNAKE_CASE

## Patterns Used
- **Async/Await**: All I/O operations
- **Connection Pooling**: asyncpg with context managers
- **Pydantic Models**: Type-safe data validation
- **WebSocket Broadcasting**: Centralized manager
- **Composables**: Reusable Vue logic

## Error Handling
- Never silently fail - always log and re-raise
- Use specific exception types
- Context managers for cleanup

## Code Examples

### Async Database
```python
@asynccontextmanager
async def get_connection():
    pool = get_pool()
    async with pool.acquire() as conn:
        yield conn
```

### Vue Composable
```typescript
export function useAgentPulse() {
  const isPulsing = ref<Set<string>>(new Set())
  function triggerPulse(agentId: string): void { ... }
  return { isPulsing, triggerPulse }
}
```
