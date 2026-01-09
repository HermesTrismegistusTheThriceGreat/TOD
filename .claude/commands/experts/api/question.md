---
allowed-tools: Bash, Read, Grep, Glob, TodoWrite
description: Answer questions about API endpoints, requests, and responses without coding
argument-hint: [question]
---

# API Expert - Question Mode

Answer the user's question by analyzing the FastAPI REST and WebSocket implementation in this multi-agent orchestration system. This prompt is designed to provide information about the API layer without making any code changes.

## Variables

USER_QUESTION: $1
EXPERTISE_PATH: .claude/commands/experts/api/expertise.yaml

## Instructions

- IMPORTANT: This is a question-answering task only - DO NOT write, edit, or create any files
- Focus on REST endpoints, WebSocket events, Pydantic models, and request/response patterns
- If the question requires API changes, explain the implementation steps conceptually without implementing
- With your expert knowledge, validate the information from `EXPERTISE_PATH` against the codebase before answering your question.

## Workflow

- Read the `EXPERTISE_PATH` file to understand API architecture and patterns
- Review, validate, and confirm information from `EXPERTISE_PATH` against the codebase
- Respond based on the `Report` section below.

## Report

- Direct answer to the `USER_QUESTION`
- Supporting evidence from `EXPERTISE_PATH` and the codebase
- References to the exact files and lines of code that support the answer
- High-mid level conceptual explanations of the API architecture and patterns
- Include endpoint documentation or request/response examples where appropriate
