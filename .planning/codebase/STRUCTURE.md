# Directory Structure

## Root Layout
```
/
├── apps/                    # Application monorepo
│   ├── orchestrator_3_stream/  # Main orchestrator
│   ├── orchestrator_db/        # Database models/migrations
│   ├── pomodoro_timer/         # CLI timer
│   └── nile/                   # Shopping demo
├── adws/                    # AI Developer Workflows
│   ├── adw_modules/            # Core infrastructure
│   ├── adw_workflows/          # Workflow implementations
│   └── adw_triggers/           # Spawning mechanisms
├── .claude/                 # Claude Code config
│   ├── agents/                 # Subagent definitions
│   ├── commands/               # Slash commands
│   └── skills/                 # Reusable skills
├── ai_docs/                 # AI documentation
├── specs/                   # System specifications
└── .planning/               # Architecture docs
```

## Key Locations
- **Backend Modules**: `/apps/orchestrator_3_stream/backend/modules/`
- **Frontend Components**: `/apps/orchestrator_3_stream/frontend/src/components/`
- **Database Models**: `/apps/orchestrator_db/models.py`
- **Migrations**: `/apps/orchestrator_db/migrations/`

## Naming Conventions
- Python: snake_case (`orchestrator_service.py`)
- Vue: PascalCase (`AgentList.vue`)
- Composables: use prefix (`useAgentPulse.ts`)
- Tests: `test_*.py`
