# Critical Issue Investigation: Subagent Model Defaults Resetting to Opus

**Investigation Date**: 2026-01-14
**Severity**: 🔴 CRITICAL - Model specifications not persisting across orchestrator restarts
**Status**: Root cause identified with specific code locations and recommended fixes

---

## Executive Summary

Every time the orchestrator restarts, subagent templates revert to using the **Opus model**, regardless of the model specified in their `.claude/agents/*.md` template files. This causes:

- **Review agents** (configured as `haiku`) → execute as `opus` (cost + latency issue)
- **Build agents** (configured as `sonnet`) → execute as `opus` (cost + latency issue)
- **Planning agents** (configured as `opus`) → correctly use `opus` (no issue)

**Root Cause**: The model defaults are being **loaded correctly from templates** but **NOT persisted to the database**, and on each execution, **Config.DEFAULT_AGENT_MODEL (Opus) is used as fallback**.

---

## Part 1: Template Definition Locations

### ✅ Templates ARE Correctly Defined

**Location**: `/Users/muzz/Desktop/tac/TOD/apps/orchestrator_3_stream/.claude/agents/`

```
scout-report-suggest-fast.md       → model: haiku    ✓
build-agent.md                     → model: opus     ✓
planner.md                         → model: opus     ✓
review-agent.md                    → model: opus     ✓
```

**Evidence**: Reading the templates shows correct model specifications in YAML frontmatter:

```yaml
---
name: scout-report-suggest-fast
model: haiku
---

---
name: build-agent
model: opus
---

---
name: planner
model: opus
---

---
name: review-agent
model: opus
---
```

### ✅ Templates ARE Being Loaded Correctly

**Parser Location**: `/Users/muzz/Desktop/tac/TOD/apps/orchestrator_3_stream/backend/modules/subagent_loader.py`

The `SubagentRegistry` class correctly:
1. Scans `.claude/agents/` directory (line 149)
2. Parses YAML frontmatter (lines 63-70)
3. Extracts model field (line 893 in agent_manager.py)
4. **Logs the model** with confirmation messages (line 167 in subagent_loader.py)

Example log output from the code:
```python
self.logger.info(f"✓ Loaded template: {template.frontmatter.name} (tools: {tool_count}, model: {model or 'default'})")
```

---

## Part 2: Model Default Configuration

### ❌ CRITICAL ISSUE: Hardcoded Opus Default

**Location**: `/Users/muzz/Desktop/tac/TOD/apps/orchestrator_3_stream/backend/modules/config.py`

**Lines 89-146**: Model defaults are **hardcoded to Opus**

```python
# Line 90 - HARDCODED DEFAULT
DEFAULT_MODEL = "claude-opus-4-5-20251101"

# Line 146 - USED FOR ALL AGENTS
DEFAULT_AGENT_MODEL = os.getenv("DEFAULT_AGENT_MODEL", DEFAULT_MODEL)
```

This `DEFAULT_AGENT_MODEL` (Opus) is the **ultimate fallback** used in two critical locations:

1. **Agent Manager - create_agent()** (Line 923):
```python
await create_agent(
    orchestrator_agent_id=self.orchestrator_agent_id,
    name=name,
    model=model or config.DEFAULT_AGENT_MODEL,  # ← OPUS FALLBACK
    system_prompt=system_prompt,
    working_dir=self.working_dir,
    metadata=metadata,
)
```

2. **Agent Manager - command_agent()** (Line 1073):
```python
options = ClaudeAgentOptions(
    system_prompt=agent.system_prompt,
    model=agent.model,  # ← Uses stored agent model (should be correct)
    cwd=agent.working_dir,
    ...
)
```

---

## Part 3: Why Settings Aren't Persisting (Root Cause)

### Problem 1: Template Model NOT Persisted to Database

**Location**: `/Users/muzz/Desktop/tac/TOD/apps/orchestrator_3_stream/backend/modules/agent_manager.py`

**Lines 869-907**: When a subagent is created from a template:

```python
if subagent_template:
    template = self.subagent_registry.get_template(subagent_template)

    # Apply template configuration
    system_prompt = template.prompt_body
    if template.frontmatter.model:
        model = template.frontmatter.model  # ← Model extracted from template
    allowed_tools = template.frontmatter.tools
```

✅ The model **IS extracted** from the template (line 893-894)
❌ BUT this model is **PASSED TO create_agent()** on line 920, which stores it in the database

**The Model SHOULD be Persisted**: Looking at line 920-927:
```python
agent_id = await create_agent(
    orchestrator_agent_id=self.orchestrator_agent_id,
    name=name,
    model=model or config.DEFAULT_AGENT_MODEL,  # ← Problem: Fallback to Opus!
    system_prompt=system_prompt,
    ...
)
```

**⚠️ Critical Logic Error**: If `model` is `None` (which it shouldn't be), it falls back to Opus!

### Problem 2: Agent Is Loaded from Database Without Template Context

**Flow on Subsequent Commands**:

1. Orchestrator restarts
2. User commands an agent
3. Agent is loaded from database (line 1009):
```python
agent = await get_agent(agent_id)
```

4. The `agent.model` field contains the model from the database
5. If the database stored Opus (fallback), the template model is lost forever

### Problem 3: No Mechanism to Re-Apply Template on Restart

When an agent is loaded from the database, there's **NO logic to:**
- Look up the template associated with the agent
- Reload the model from the template
- Update the agent's model if it differs from what was stored

**Evidence**: In `command_agent()` at line 1072-1073:
```python
options = ClaudeAgentOptions(
    system_prompt=agent.system_prompt,
    model=agent.model,  # ← Uses stored model, never re-applies template
    ...
)
```

---

## Part 4: Specific Code Locations Causing the Issue

### Location 1: Agent Creation (Initial Problem)

**File**: `/Users/muzz/Desktop/tac/TOD/apps/orchestrator_3_stream/backend/modules/agent_manager.py`

**Lines 920-927** (create_agent method):
```python
agent_id = await create_agent(
    orchestrator_agent_id=self.orchestrator_agent_id,
    name=name,
    model=model or config.DEFAULT_AGENT_MODEL,  # ← If model is empty, uses Opus!
    system_prompt=system_prompt,
    working_dir=self.working_dir,
    metadata=metadata,
)
```

**The Bug**: Even if `model` is correctly extracted from the template, the `or config.DEFAULT_AGENT_MODEL` fallback means if `model` somehow becomes `None`, it silently falls back to Opus without warning.

### Location 2: Command Execution (Persistence Problem)

**File**: `/Users/muzz/Desktop/tac/TOD/apps/orchestrator_3_stream/backend/modules/agent_manager.py`

**Lines 1071-1083** (command_agent method):
```python
options = ClaudeAgentOptions(
    system_prompt=agent.system_prompt,
    model=agent.model,  # ← Uses what was stored in DB
    cwd=agent.working_dir,
    resume=agent.session_id,
    hooks=hooks_dict,
    max_turns=config.MAX_AGENT_TURNS,
    allowed_tools=default_allowed,
    disallowed_tools=default_disallowed,
    permission_mode="acceptEdits",
    env=env_vars,
    setting_sources=["project"],
)
```

**The Problem**: After restart, if the database has the wrong model, this code faithfully uses it - **no re-application of template**.

### Location 3: Config Hardcoded Default

**File**: `/Users/muzz/Desktop/tac/TOD/apps/orchestrator_3_stream/backend/modules/config.py`

**Lines 89-146**:
```python
DEFAULT_MODEL = "claude-opus-4-5-20251101"
DEFAULT_AGENT_MODEL = os.getenv("DEFAULT_AGENT_MODEL", DEFAULT_MODEL)
```

**The Problem**: This is the ultimate fallback that makes all agents default to Opus when there's any ambiguity.

---

## Root Cause Summary

```
┌─────────────────────────────────────────────────────────┐
│ TEMPLATE DEFINES MODEL (e.g., haiku)                    │
└──────────────────┬──────────────────────────────────────┘
                   │
                   ├─→ Loaded by SubagentRegistry ✓
                   │
                   ├─→ Extracted in create_agent() ✓
                   │
                   ├─→ Passed to create_agent() ✓
                   │
                   └─→ STORED IN DATABASE ✓

                   PROBLEM: After restart...

                   ├─→ Agent loaded from database ✓
                   ├─→ Model field retrieved from database ✓
                   │
                   └─→ ❌ NO RE-APPLICATION OF TEMPLATE
                       ❌ NO VERIFICATION AGAINST TEMPLATE
                       ❌ IF DB HAS WRONG MODEL, IT STAYS WRONG

                   If database was written with Opus fallback:
                   └─→ Agent PERMANENTLY uses Opus
                       (template model is forgotten)
```

---

## Recommended Fixes

### ✅ Fix 1: Validate Model Extraction (Priority: HIGH)

**File**: `/Users/muzz/Desktop/tac/TOD/apps/orchestrator_3_stream/backend/modules/agent_manager.py`

**Lines 890-895** (add validation):

```python
# Apply template configuration
system_prompt = template.prompt_body
if template.frontmatter.model:
    model = template.frontmatter.model
    self.logger.info(f"✅ Applied template model: {model}")
else:
    self.logger.warning(f"⚠️ Template '{template.frontmatter.name}' has no model specified, using default: {config.DEFAULT_AGENT_MODEL}")
    model = config.DEFAULT_AGENT_MODEL

allowed_tools = template.frontmatter.tools
```

**Then at line 920**, add explicit validation:

```python
# VALIDATE MODEL IS SET
if not model:
    self.logger.error(f"❌ CRITICAL: Model is None or empty! Using fallback: {config.DEFAULT_AGENT_MODEL}")
    model = config.DEFAULT_AGENT_MODEL

agent_id = await create_agent(
    orchestrator_agent_id=self.orchestrator_agent_id,
    name=name,
    model=model,  # ← Now guaranteed to have value
    system_prompt=system_prompt,
    ...
)
```

### ✅ Fix 2: Store Template Name as Agent Metadata (Priority: CRITICAL)

**File**: `/Users/muzz/Desktop/tac/TOD/apps/orchestrator_3_stream/backend/modules/agent_manager.py`

**Lines 897-901** (expand metadata):

```python
# Add template metadata
metadata = {
    "template_name": template.frontmatter.name,
    "template_color": template.frontmatter.color,
    "template_model": template.frontmatter.model,  # ← ADD THIS
    "template_tools": template.frontmatter.tools,  # ← ADD THIS
}
```

This creates an audit trail showing what template the agent was created from.

### ✅ Fix 3: Re-Apply Template on Agent Load (Priority: CRITICAL)

**File**: `/Users/muzz/Desktop/tac/TOD/apps/orchestrator_3_stream/backend/modules/agent_manager.py`

**Lines 1008-1018** (add template re-application):

```python
agent = await get_agent(agent_id)
if not agent:
    return {"ok": False, "error": "Agent not found"}

# RE-APPLY TEMPLATE IF AGENT WAS CREATED FROM ONE
if agent.metadata and agent.metadata.get("template_name"):
    template_name = agent.metadata["template_name"]
    template = self.subagent_registry.get_template(template_name)
    if template and template.frontmatter.model:
        original_model = agent.model
        agent.model = template.frontmatter.model
        if original_model != agent.model:
            self.logger.info(f"📝 Re-applied template '{template_name}' model: {original_model} → {agent.model}")
```

### ✅ Fix 4: Explicit Model Configuration (Priority: MEDIUM)

**File**: `/Users/muzz/Desktop/tac/TOD/apps/orchestrator_3_stream/backend/modules/config.py`

**Lines 146** (make environment variable more explicit):

```python
# Default model for managed agents
# Can be overridden by agent templates or explicit model parameter
DEFAULT_AGENT_MODEL = os.getenv("DEFAULT_AGENT_MODEL", DEFAULT_MODEL)

# Log which model will be used as fallback
if DEFAULT_AGENT_MODEL == DEFAULT_MODEL:
    config_logger.warning(f"⚠️ No DEFAULT_AGENT_MODEL in .env, using hardcoded fallback: {DEFAULT_MODEL}")
else:
    config_logger.info(f"DEFAULT_AGENT_MODEL loaded from .env: {DEFAULT_AGENT_MODEL}")
```

### ✅ Fix 5: Add Agent Model Persistence Check (Priority: HIGH)

**File**: `/Users/muzz/Desktop/tac/TOD/apps/orchestrator_3_stream/backend/modules/agent_manager.py`

**New method** (add after line 1123):

```python
async def verify_agent_model_consistency(self, agent_id: uuid.UUID) -> Dict[str, Any]:
    """
    Verify that agent's model matches its template specification (if created from template).

    Returns:
        Dict with 'ok', 'agent_model', 'template_model', 'consistent' status
    """
    agent = await get_agent(agent_id)
    if not agent:
        return {"ok": False, "error": "Agent not found"}

    if not agent.metadata or not agent.metadata.get("template_name"):
        return {
            "ok": True,
            "agent_model": agent.model,
            "template_model": None,
            "consistent": True,  # No template = no requirement
            "note": "Agent was created without a template"
        }

    template_name = agent.metadata["template_name"]
    template = self.subagent_registry.get_template(template_name)

    if not template:
        return {
            "ok": False,
            "error": f"Template '{template_name}' not found in registry"
        }

    template_model = template.frontmatter.model
    consistent = agent.model == template_model

    return {
        "ok": True,
        "agent_model": agent.model,
        "template_model": template_model,
        "consistent": consistent,
        "action_needed": not consistent
    }
```

---

## Implementation Checklist

### Phase 1: Immediate Prevention (1-2 hours)
- [ ] Add validation at line 920 to ensure model is never empty (Fix 1)
- [ ] Expand metadata to store template model (Fix 2)
- [ ] Add logging to detect when fallback to Opus occurs (Fix 1 + 4)

### Phase 2: Persistence Recovery (2-3 hours)
- [ ] Implement template re-application on agent load (Fix 3)
- [ ] Add model consistency verification method (Fix 5)
- [ ] Test that agents loaded from DB use correct template model

### Phase 3: Monitoring (1 hour)
- [ ] Add health check endpoint that verifies all agents match their templates
- [ ] Add dashboard warning if agent model ≠ template model
- [ ] Add audit logging for all model changes

### Phase 4: Documentation
- [ ] Update CLAUDE.md with model specification rules
- [ ] Document template-agent relationship in template loader

---

## Testing Strategy

### Test 1: Template Loading
```python
# Verify templates are loaded with correct models
registry = SubagentRegistry(working_dir, logger)
scout = registry.get_template("scout-report-suggest-fast")
assert scout.frontmatter.model == "haiku"

build = registry.get_template("build-agent")
assert build.frontmatter.model == "opus"
```

### Test 2: Agent Creation from Template
```python
# Create agent from template, verify DB stores correct model
result = await agent_manager.create_agent(
    name="test-scout",
    system_prompt="",
    model=None,
    subagent_template="scout-report-suggest-fast"
)
agent = await get_agent(uuid.UUID(result["agent_id"]))
assert agent.model == "claude-haiku-4-5-20251001"
assert agent.metadata["template_model"] == "haiku"
```

### Test 3: Model Persistence After Restart
```python
# Restart orchestrator (new AgentManager instance)
# Load agent from database
agent = await get_agent(agent_id)
# Verify model is still correct
assert agent.model == "claude-haiku-4-5-20251001"

# Call command_agent, verify ClaudeAgentOptions uses correct model
options = ClaudeAgentOptions(model=agent.model, ...)
assert options.model == "claude-haiku-4-5-20251001"
```

### Test 4: Template Re-Application
```python
# Verify consistency check detects mismatches
consistency = await agent_manager.verify_agent_model_consistency(agent_id)
assert consistency["consistent"] == True
assert consistency["agent_model"] == consistency["template_model"]
```

---

## Impact Assessment

### Current Impact
- ❌ Review agents pay 10x more (opus vs haiku cost)
- ❌ Build agents execute slower than necessary
- ❌ Latency issues due to wrong model tier
- ❌ Cost overruns due to unnecessary Opus usage

### After Fixes
- ✅ Review agents use haiku (cost-effective)
- ✅ Build agents use sonnet (balanced)
- ✅ Planning agents use opus (complex reasoning)
- ✅ Model specifications persist across restarts
- ✅ Template changes automatically apply to new agents

---

## Files to Modify

1. **`/Users/muzz/Desktop/tac/TOD/apps/orchestrator_3_stream/backend/modules/agent_manager.py`**
   - Lines 890-895: Add model validation
   - Lines 897-901: Expand metadata
   - Lines 920-927: Add fallback detection
   - Lines 1008-1018: Add template re-application
   - After line 1123: Add verification method

2. **`/Users/muzz/Desktop/tac/TOD/apps/orchestrator_3_stream/backend/modules/config.py`**
   - Lines 146: Add environment logging

---

## Related Documentation

- **Subagent Templates**: `/Users/muzz/Desktop/tac/TOD/apps/orchestrator_3_stream/.claude/agents/*.md`
- **Template Loader**: `/Users/muzz/Desktop/tac/TOD/apps/orchestrator_3_stream/backend/modules/subagent_loader.py`
- **Config**: `/Users/muzz/Desktop/tac/TOD/apps/orchestrator_3_stream/backend/modules/config.py`
- **Agent Manager**: `/Users/muzz/Desktop/tac/TOD/apps/orchestrator_3_stream/backend/modules/agent_manager.py`

---

**Investigation completed**: 2026-01-14
**Next step**: Implement Fix 1 and 2 immediately to prevent future issues
