---
name: agent-browser
description: Automates browser interactions for web testing, form filling, screenshots, and data extraction. Use when the user needs to navigate websites, interact with web pages, fill forms, take screenshots, test web applications, or extract information from web pages.
allowed-tools: Bash(agent-browser:*),Bash(AGENT_BROWSER_SESSION=*),Bash(lsof:*),Bash(./start_be.sh:*),Bash(./start_fe.sh:*),Bash(cd apps/orchestrator_3_stream:*),Bash(sleep:*),Bash(curl:*)
---

# Browser Automation with agent-browser

## ⚠️ CRITICAL: Required Setup (READ FIRST)

### 1. Session Environment Variable is REQUIRED

**Every `agent-browser` command MUST use the `AGENT_BROWSER_SESSION` environment variable.**

Without it, you will get: `✗ Browser not launched. Call launch first.`

```bash
# ❌ WRONG - Will fail with "Browser not launched"
agent-browser open http://localhost:5175

# ✅ CORRECT - Always use AGENT_BROWSER_SESSION
AGENT_BROWSER_SESSION=test1 agent-browser open http://localhost:5175
AGENT_BROWSER_SESSION=test1 agent-browser snapshot -i
AGENT_BROWSER_SESSION=test1 agent-browser click @e1
```

### 2. First-Time Setup: Install Chromium

On first use, you must install the browser:

```bash
agent-browser install
```

This only needs to be run once. If you get errors about missing browser, run this command.

### 3. Commands That DON'T Exist (Don't Try These)

These commands do NOT exist - don't waste turns trying them:
- ❌ `agent-browser launch` - No such command
- ❌ `agent-browser new` - No such command
- ❌ `agent-browser state new` - No such command
- ❌ `agent-browser start` - No such command
- ❌ `agent-browser connect` (without CDP port) - Requires running Chrome with remote debugging

## CRITICAL: Local Server Prerequisite

**Before navigating to any localhost URL, you MUST ensure the development server is running.**

### Checking if Orchestrator is Running

```bash
# Check if frontend (port 5175) is running
lsof -ti:5175 >/dev/null 2>&1 && echo "Frontend running" || echo "Frontend NOT running"

# Check if backend (port 8002 or 9403) is running
lsof -ti:9403 >/dev/null 2>&1 && echo "Backend running on 9403" || echo "Backend NOT running"
```

### Starting the Orchestrator (if not running)

If localhost:5175 returns connection refused, start the servers:

```bash
# Start backend in background
cd /Users/muzz/Desktop/tac/TOD/apps/orchestrator_3_stream && ./start_be.sh &

# Wait for backend to initialize
sleep 3

# Start frontend in background
cd /Users/muzz/Desktop/tac/TOD/apps/orchestrator_3_stream && ./start_fe.sh &

# Wait for frontend to compile and serve
sleep 5
```

### Complete Pre-flight Workflow for localhost:5175

**ALWAYS run this workflow before browser automation on localhost:5175:**

1. **Check if servers are running:**
   ```bash
   lsof -ti:5175 >/dev/null 2>&1 && lsof -ti:9403 >/dev/null 2>&1 && echo "Both servers running" || echo "Need to start servers"
   ```

2. **If not running, start them:**
   ```bash
   cd /Users/muzz/Desktop/tac/TOD/apps/orchestrator_3_stream && ./start_be.sh &
   sleep 3
   cd /Users/muzz/Desktop/tac/TOD/apps/orchestrator_3_stream && ./start_fe.sh &
   sleep 5
   ```

3. **Then proceed with browser automation (WITH SESSION!):**
   ```bash
   AGENT_BROWSER_SESSION=test1 agent-browser open http://localhost:5175
   ```

## Quick start

**Remember: Always use `AGENT_BROWSER_SESSION=<name>` prefix!**

```bash
# Set session name (use same name for all commands in a workflow)
export AGENT_BROWSER_SESSION=test1

# Or prefix each command:
AGENT_BROWSER_SESSION=test1 agent-browser open <url>        # Navigate to page
AGENT_BROWSER_SESSION=test1 agent-browser snapshot -i       # Get interactive elements with refs
AGENT_BROWSER_SESSION=test1 agent-browser click @e1         # Click element by ref
AGENT_BROWSER_SESSION=test1 agent-browser fill @e2 "text"   # Fill input by ref
AGENT_BROWSER_SESSION=test1 agent-browser close             # Close browser
```

## Core workflow

1. **Set session**: `export AGENT_BROWSER_SESSION=test1` (or prefix each command)
2. **Navigate**: `AGENT_BROWSER_SESSION=test1 agent-browser open <url>`
3. **Snapshot**: `AGENT_BROWSER_SESSION=test1 agent-browser snapshot -i` (returns elements with refs like `@e1`, `@e2`)
4. **Interact** using refs from the snapshot
5. **Re-snapshot** after navigation or significant DOM changes

## Commands

### Navigation
```bash
agent-browser open <url>      # Navigate to URL
agent-browser back            # Go back
agent-browser forward         # Go forward
agent-browser reload          # Reload page
agent-browser close           # Close browser
```

### Snapshot (page analysis)
```bash
agent-browser snapshot            # Full accessibility tree
agent-browser snapshot -i         # Interactive elements only (recommended)
agent-browser snapshot -c         # Compact output
agent-browser snapshot -d 3       # Limit depth to 3
agent-browser snapshot -s "#main" # Scope to CSS selector
```

### Interactions (use @refs from snapshot)
```bash
agent-browser click @e1           # Click
agent-browser dblclick @e1        # Double-click
agent-browser focus @e1           # Focus element
agent-browser fill @e2 "text"     # Clear and type
agent-browser type @e2 "text"     # Type without clearing
agent-browser press Enter         # Press key
agent-browser press Control+a     # Key combination
agent-browser keydown Shift       # Hold key down
agent-browser keyup Shift         # Release key
agent-browser hover @e1           # Hover
agent-browser check @e1           # Check checkbox
agent-browser uncheck @e1         # Uncheck checkbox
agent-browser select @e1 "value"  # Select dropdown
agent-browser scroll down 500     # Scroll page
agent-browser scrollintoview @e1  # Scroll element into view
agent-browser drag @e1 @e2        # Drag and drop
agent-browser upload @e1 file.pdf # Upload files
```

### Get information
```bash
agent-browser get text @e1        # Get element text
agent-browser get html @e1        # Get innerHTML
agent-browser get value @e1       # Get input value
agent-browser get attr @e1 href   # Get attribute
agent-browser get title           # Get page title
agent-browser get url             # Get current URL
agent-browser get count ".item"   # Count matching elements
agent-browser get box @e1         # Get bounding box
```

### Check state
```bash
agent-browser is visible @e1      # Check if visible
agent-browser is enabled @e1      # Check if enabled
agent-browser is checked @e1      # Check if checked
```

### Screenshots & PDF
```bash
agent-browser screenshot          # Screenshot to stdout
agent-browser screenshot path.png # Save to file
agent-browser screenshot --full   # Full page
agent-browser pdf output.pdf      # Save as PDF
```

### Video recording
```bash
agent-browser record start ./demo.webm    # Start recording (uses current URL + state)
agent-browser click @e1                   # Perform actions
agent-browser record stop                 # Stop and save video
agent-browser record restart ./take2.webm # Stop current + start new recording
```
Recording creates a fresh context but preserves cookies/storage from your session. If no URL is provided, it automatically returns to your current page. For smooth demos, explore first, then start recording.

### Wait
```bash
agent-browser wait @e1                     # Wait for element
agent-browser wait 2000                    # Wait milliseconds
agent-browser wait --text "Success"        # Wait for text
agent-browser wait --url "**/dashboard"    # Wait for URL pattern
agent-browser wait --load networkidle      # Wait for network idle
agent-browser wait --fn "window.ready"     # Wait for JS condition
```

### Mouse control
```bash
agent-browser mouse move 100 200      # Move mouse
agent-browser mouse down left         # Press button
agent-browser mouse up left           # Release button
agent-browser mouse wheel 100         # Scroll wheel
```

### Semantic locators (alternative to refs)
```bash
agent-browser find role button click --name "Submit"
agent-browser find text "Sign In" click
agent-browser find label "Email" fill "user@test.com"
agent-browser find first ".item" click
agent-browser find nth 2 "a" text
```

### Browser settings
```bash
agent-browser set viewport 1920 1080      # Set viewport size
agent-browser set device "iPhone 14"      # Emulate device
agent-browser set geo 37.7749 -122.4194   # Set geolocation
agent-browser set offline on              # Toggle offline mode
agent-browser set headers '{"X-Key":"v"}' # Extra HTTP headers
agent-browser set credentials user pass   # HTTP basic auth
agent-browser set media dark              # Emulate color scheme
```

### Cookies & Storage
```bash
agent-browser cookies                     # Get all cookies
agent-browser cookies set name value      # Set cookie
agent-browser cookies clear               # Clear cookies
agent-browser storage local               # Get all localStorage
agent-browser storage local key           # Get specific key
agent-browser storage local set k v       # Set value
agent-browser storage local clear         # Clear all
```

### Network
```bash
agent-browser network route <url>              # Intercept requests
agent-browser network route <url> --abort      # Block requests
agent-browser network route <url> --body '{}'  # Mock response
agent-browser network unroute [url]            # Remove routes
agent-browser network requests                 # View tracked requests
agent-browser network requests --filter api    # Filter requests
```

### Tabs & Windows
```bash
agent-browser tab                 # List tabs
agent-browser tab new [url]       # New tab
agent-browser tab 2               # Switch to tab
agent-browser tab close           # Close tab
agent-browser window new          # New window
```

### Frames
```bash
agent-browser frame "#iframe"     # Switch to iframe
agent-browser frame main          # Back to main frame
```

### Dialogs
```bash
agent-browser dialog accept [text]  # Accept dialog
agent-browser dialog dismiss        # Dismiss dialog
```

### JavaScript
```bash
agent-browser eval "document.title"   # Run JavaScript
```

## Example: Form submission

```bash
# Always set session first
export AGENT_BROWSER_SESSION=form_test

AGENT_BROWSER_SESSION=form_test agent-browser open https://example.com/form
AGENT_BROWSER_SESSION=form_test agent-browser snapshot -i
# Output shows: textbox "Email" [ref=e1], textbox "Password" [ref=e2], button "Submit" [ref=e3]

AGENT_BROWSER_SESSION=form_test agent-browser fill @e1 "user@example.com"
AGENT_BROWSER_SESSION=form_test agent-browser fill @e2 "password123"
AGENT_BROWSER_SESSION=form_test agent-browser click @e3
AGENT_BROWSER_SESSION=form_test agent-browser wait --load networkidle
AGENT_BROWSER_SESSION=form_test agent-browser snapshot -i  # Check result
```

## Example: Authentication with saved state

```bash
# Login once
AGENT_BROWSER_SESSION=auth agent-browser open https://app.example.com/login
AGENT_BROWSER_SESSION=auth agent-browser snapshot -i
AGENT_BROWSER_SESSION=auth agent-browser fill @e1 "username"
AGENT_BROWSER_SESSION=auth agent-browser fill @e2 "password"
AGENT_BROWSER_SESSION=auth agent-browser click @e3
AGENT_BROWSER_SESSION=auth agent-browser wait --url "**/dashboard"
AGENT_BROWSER_SESSION=auth agent-browser state save auth.json

# Later sessions: load saved state
AGENT_BROWSER_SESSION=auth agent-browser state load auth.json
AGENT_BROWSER_SESSION=auth agent-browser open https://app.example.com/dashboard
```

## Sessions (parallel browsers)

Use different session names to run multiple browser instances:

```bash
AGENT_BROWSER_SESSION=test1 agent-browser open site-a.com
AGENT_BROWSER_SESSION=test2 agent-browser open site-b.com
agent-browser session list
```

## JSON output (for parsing)

Add `--json` for machine-readable output:
```bash
agent-browser snapshot -i --json
agent-browser get text @e1 --json
```

## Debugging

```bash
agent-browser open example.com --headed              # Show browser window
agent-browser console                                # View console messages
agent-browser errors                                 # View page errors
agent-browser record start ./debug.webm   # Record from current page
agent-browser record stop                            # Save recording
agent-browser open example.com --headed  # Show browser window
agent-browser --cdp 9222 snapshot        # Connect via CDP
agent-browser console                    # View console messages
agent-browser console --clear            # Clear console
agent-browser errors                     # View page errors
agent-browser errors --clear             # Clear errors
agent-browser highlight @e1              # Highlight element
agent-browser trace start                # Start recording trace
agent-browser trace stop trace.zip       # Stop and save trace
```
