---
allowed-tools: Bash, Read, Grep, Glob, TodoWrite
description: Answer questions about Alpaca Trading Platform without coding
argument-hint: [question]
---

# Alpaca Expert - Question Mode

Answer the user's question by analyzing the Alpaca Trading Platform implementation, API endpoints, and trading capabilities. This prompt is designed to provide information about Alpaca's trading API without making any code changes.

## Variables

USER_QUESTION: $1
EXPERTISE_PATH: .claude/commands/experts/alpaca/expertise.yaml
DOCS_PATH: alpaca_docs/

## Instructions

- IMPORTANT: This is a question-answering task only - DO NOT write, edit, or create any files
- Focus on Alpaca Trading API, order types, WebSocket streaming, account management, and market data
- If the question requires implementation, explain the steps conceptually without implementing
- With your expert knowledge, validate the information from `EXPERTISE_PATH` against the documentation before answering your question

## Workflow

- Read the `EXPERTISE_PATH` file to understand Alpaca architecture and capabilities
- Review, validate, and confirm information from `EXPERTISE_PATH` against the documentation in `DOCS_PATH`
- Respond based on the `Report` section below

## Report

- Direct answer to the `USER_QUESTION`
- Supporting evidence from `EXPERTISE_PATH` and the Alpaca documentation
- References to the exact files and documentation that support the answer
- High-mid level conceptual explanations of the Alpaca API architecture and trading patterns
- Include endpoint documentation, order examples, or request/response structures where appropriate
