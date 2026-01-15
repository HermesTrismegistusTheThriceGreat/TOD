# External AI Prompts

This directory contains prompts for external AI tools and assistants used in the development workflow.

## Directory Structure

```
prompts/
├── README.md           # This file
├── antigravity/        # Prompts for Antigravity AI
│   └── *.md           # Individual prompt files
└── [other-tool]/       # Future: prompts for other AI tools
```

## Naming Convention

Prompt files should be named descriptively:
- `component_name_feature.md` - For component-specific work
- `feature_name_implementation.md` - For feature implementations
- `bugfix_description.md` - For bug fixes

## Prompt Template

Each prompt should include:
1. **Date** - When the prompt was created
2. **Component/Target** - What file(s) will be modified
3. **Scope** - Frontend only, backend only, or full-stack
4. **Requirements** - Detailed list of what needs to be done
5. **Mock Data** - If applicable, sample data structures
6. **Styling Guidelines** - Visual/CSS requirements
7. **Testing Checklist** - How to verify the work

## Usage Notes

- These prompts are designed for AI assistants to implement features
- Backend integration is typically handled separately by Claude agents
- Include mock data when frontend work precedes backend work
