# Plan: Test Better Auth Flow with Playwright

## Task Description
Test the Better Auth authentication flow using Playwright browser automation via the `playwright-validate-cli-instance` command. The auth stack is running with Auth Service (port 9404), Backend (port 9403), and Frontend (port 5175). Tests will validate signup, login, session persistence, and logout functionality.

## Objective
Validate the complete Better Auth integration works correctly by automating browser tests that:
1. Create a new user account via signup
2. Verify redirect to home after signup
3. Log out and verify redirect to login
4. Log back in with created credentials
5. Verify authenticated state persists

## Problem Statement
The Better Auth integration was just built and configured. Before considering it production-ready, we need end-to-end validation that:
- Forms render correctly and accept input
- Auth service correctly creates users and sessions
- Session cookies are properly set and validated
- Router guards work (redirect authenticated users from login/signup)
- Error states are handled gracefully

## Solution Approach
Use the `playwright-validate-cli-instance.md` command to spawn a Claude Code subprocess with Playwright MCP tools. This subprocess will:
1. Navigate to auth pages and interact with forms
2. Fill in test credentials and submit
3. Verify page transitions and content changes
4. Take screenshots for validation evidence
5. Report pass/fail status for each test step

## Relevant Files

**Auth Flow Components:**
- `apps/orchestrator_3_stream/frontend/src/views/SignupView.vue` - Signup page wrapper
- `apps/orchestrator_3_stream/frontend/src/views/LoginView.vue` - Login page wrapper
- `apps/orchestrator_3_stream/frontend/src/views/HomeView.vue` - Post-auth landing page
- `apps/orchestrator_3_stream/frontend/src/components/auth/SignupForm.vue` - Signup form (name, email, password fields)
- `apps/orchestrator_3_stream/frontend/src/components/auth/LoginForm.vue` - Login form (email, password fields)
- `apps/orchestrator_3_stream/frontend/src/router/index.ts` - Vue Router with auth guards
- `apps/orchestrator_3_stream/frontend/src/stores/authStore.ts` - Pinia auth state management
- `apps/orchestrator_3_stream/frontend/src/services/authClient.ts` - Better Auth client

**Playwright Configuration:**
- `.mcp.json.playwright` - MCP config for Playwright tools (headless, 1920x1080 viewport)
- `.claude/commands/playwright-validate-cli-instance.md` - Command template for spawning Playwright subprocess

## Implementation Phases

### Phase 1: Environment Setup
- Verify all services are running (auth:9404, backend:9403, frontend:5175)
- Ensure Playwright MCP configuration is correct
- Generate unique test credentials to avoid conflicts

### Phase 2: Core Test Execution
- Run signup flow test
- Run login flow test
- Run session persistence test
- Run logout flow test

### Phase 3: Validation & Reporting
- Collect screenshots from each step
- Compile pass/fail results
- Report any errors or unexpected behavior

## Step by Step Tasks

### 1. Verify Services Are Running
- Check auth service is responding on port 9404
- Check backend is responding on port 9403
- Check frontend is responding on port 5175
- Commands:
  ```bash
  curl -s http://127.0.0.1:9404/api/auth/session || echo "Auth service not responding"
  curl -s http://127.0.0.1:9403/health || echo "Backend not responding"
  curl -s http://127.0.0.1:5175 || echo "Frontend not responding"
  ```

### 2. Generate Test Credentials
- Create unique test user credentials for this test run
- Use timestamp-based email to ensure uniqueness
- Test credentials format:
  - Name: `Test User`
  - Email: `test-{timestamp}@example.com`
  - Password: `TestPassword123!`

### 3. Run Signup Flow Test via Playwright
Execute the playwright-validate-cli-instance command with these instructions:

```
Test the signup flow at http://127.0.0.1:5175/signup:

1. Navigate to http://127.0.0.1:5175/signup
2. Take a screenshot of the signup page
3. Verify the page contains:
   - "Create Account" heading
   - Name input field (id="name")
   - Email input field (id="email")
   - Password input field (id="password")
   - "Sign Up" button
4. Fill the form:
   - Name: "Test User"
   - Email: "test-{timestamp}@example.com"
   - Password: "TestPassword123!"
5. Click the "Sign Up" button
6. Wait for navigation (should redirect to "/" on success)
7. Take a screenshot of the result
8. Verify we're on the home page with "Welcome to Orchestrator" text
9. Report: PASS if all steps succeed, FAIL with details if any step fails
```

### 4. Run Logout Flow Test via Playwright
Execute with these instructions:

```
Test the logout flow:

1. Verify we're on the home page (http://127.0.0.1:5175/)
2. Look for a logout button or link (if implemented)
3. If no logout UI exists, manually clear cookies/session
4. Navigate to http://127.0.0.1:5175/login
5. Verify we can access the login page (not redirected away)
6. Take a screenshot
7. Report: PASS if login page is accessible, FAIL otherwise
```

### 5. Run Login Flow Test via Playwright
Execute with these instructions:

```
Test the login flow at http://127.0.0.1:5175/login:

1. Navigate to http://127.0.0.1:5175/login
2. Take a screenshot of the login page
3. Verify the page contains:
   - "Sign In" heading
   - Email input field (id="email")
   - Password input field (id="password")
   - "Sign In" button
4. Fill the form:
   - Email: "test-{timestamp}@example.com" (same as signup)
   - Password: "TestPassword123!"
5. Click the "Sign In" button
6. Wait for navigation (should redirect to "/" on success)
7. Take a screenshot of the result
8. Verify we're on the home page with "Welcome to Orchestrator" text
9. Report: PASS if all steps succeed, FAIL with details if any step fails
```

### 6. Run Session Persistence Test via Playwright
Execute with these instructions:

```
Test session persistence:

1. From the home page, refresh the browser
2. Verify we're still on the home page (not redirected to login)
3. Take a screenshot
4. Navigate directly to http://127.0.0.1:5175/login
5. Verify we're redirected to home (authenticated users can't access login)
6. Take a screenshot showing redirect happened
7. Report: PASS if session persists and guards work, FAIL otherwise
```

### 7. Compile Test Results
- Gather all screenshots taken
- Compile pass/fail status for each test phase
- Document any errors or unexpected behavior
- Provide summary report

## Testing Strategy

**Test Data:**
- Use unique email per test run (timestamp-based) to avoid duplicate user conflicts
- Use strong password that meets requirements (8+ chars)

**Test Isolation:**
- Each Playwright subprocess runs in headless mode
- Tests run sequentially to maintain session state between tests

**Error Handling:**
- If signup fails, skip login test (depends on created user)
- Capture screenshots on both success and failure
- Report detailed error messages from any failed steps

**Expected UI Elements:**
| Page | Key Elements |
|------|-------------|
| /signup | h2 "Create Account", inputs: #name, #email, #password, button "Sign Up" |
| /login | h2 "Sign In", inputs: #email, #password, button "Sign In" |
| / (Home) | h1 "Welcome to Orchestrator" |

## Acceptance Criteria

- [ ] Signup form renders with all required fields
- [ ] New user can be created successfully
- [ ] User is redirected to home page after signup
- [ ] Login form renders with all required fields
- [ ] Created user can log in successfully
- [ ] User is redirected to home page after login
- [ ] Session persists across page refresh
- [ ] Authenticated users are redirected away from /login and /signup
- [ ] Screenshots captured for each test step as evidence

## Validation Commands

Execute these commands to run the full test suite:

```bash
# 1. Verify services are running
curl -s http://127.0.0.1:5175 > /dev/null && echo "Frontend OK" || echo "Frontend FAIL"
curl -s http://127.0.0.1:9403/health > /dev/null && echo "Backend OK" || echo "Backend FAIL"
curl -s http://127.0.0.1:9404/api/auth/session > /dev/null && echo "Auth OK" || echo "Auth FAIL"

# 2. Run Playwright tests via CLI (from project root)
claude --mcp-config .mcp.json.playwright --model haiku --dangerously-skip-permissions -p "
Navigate to http://127.0.0.1:5175/signup and:
1. Take screenshot
2. Fill form: name='Test User', email='playwright-test-$(date +%s)@example.com', password='TestPassword123!'
3. Click Sign Up button
4. Wait for navigation to home page
5. Take screenshot
6. Report results
"
```

## Notes

- The `playwright-validate-cli-instance.md` command uses Haiku model to minimize cost
- Playwright runs in headless mode with 1920x1080 viewport per `.mcp.json.playwright`
- Test user emails use timestamps to ensure uniqueness across test runs
- The router currently has `requiresAuth: false` on home route - tests should still work but guards won't redirect unauthenticated users from home
- If auth service is slow to start, tests may need retry logic
