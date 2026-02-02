# Design Standards for Orchestrator Frontend

A comprehensive guide to the visual design system powering the Vue 3.4.x orchestrator dashboard application. These standards ensure consistency, maintainability, and professional polish across all components while maintaining excellent performance on both desktop and mobile devices.

## Color System

The orchestrator interface employs a carefully calibrated dark-first color palette optimized for extended viewing sessions during trading and system monitoring. The system uses CSS custom properties to enable potential future theme switching and maintain consistent color application across the entire codebase.

### Primary Palette

The foundation consists of four background tones that create subtle depth hierarchy without overwhelming the interface. Background colors start with near-black (`#0a0a0a`) for the primary canvas, progressing through layered grays (`#1a1a1a`, `#2a2a2a`, `#1e1e1e`) to establish visual relationships between containers, cards, and surfaces. This graduated approach ensures that components naturally separate themselves without requiring heavy borders or excessive shadows.

```css
--bg-primary: #0a0a0a;      /* Main canvas background */
--bg-secondary: #1a1a1a;    /* Card/panel backgrounds */
--bg-tertiary: #2a2a2a;     /* Nested containers, code blocks */
--bg-quaternary: #1e1e1e;   /* Alternate surfaces, hover states */
```

Text hierarchy leverages four levels of opacity-controlled whites and grays. Primary text uses pure white (`#ffffff`) for maximum contrast on headings and critical information. Secondary text (`#b0b0b0`) handles body content and labels. Muted text (`#6b7280`) provides subtle context for timestamps and metadata. Dim text (`#4b5563`) marks the lowest-priority information like placeholders and disabled states.

```css
--text-primary: #ffffff;    /* Headings, critical content */
--text-secondary: #b0b0b0;  /* Body text, labels */
--text-muted: #6b7280;      /* Timestamps, metadata */
--text-dim: #4b5563;        /* Placeholders, disabled text */
```

### Accent Colors

Cyan (`#06b6d4`) serves as the primary brand color, appearing in interactive elements, links, and primary buttons. Its complementary teal (`#14b8a6`) provides variation in secondary accents and badges. The hover state darkens to `#0891b2`, creating tactile feedback without relying solely on shadows or transforms. These colors were selected for their excellent visibility against dark backgrounds and their association with technology and precision.

```css
--accent-primary: #06b6d4;   /* Primary actions, links, highlights */
--accent-secondary: #14b8a6; /* Secondary badges, alternates */
--accent-hover: #0891b2;     /* Interactive hover state */
```

The agent sidebar introduces a distinctive purple tint (`#2d1b4e`) to visually separate agent management from the main content area. Purple was chosen to complement the cyan accents while providing clear spatial distinction. Active agent selection uses vibrant purple (`#a855f7`) to ensure the current selection is immediately identifiable.

```css
--agent-bg: #2d1b4e;         /* Agent sidebar background */
--agent-hover: #3d2b5e;      /* Agent card hover state */
--agent-active: #a855f7;     /* Selected agent highlight */
```

### Semantic Status Colors

Status indicators follow industry-standard color associations to leverage user expectations. Success states use emerald green (`#10b981`), errors display in red (`#ef4444`), warnings appear in amber (`#f59e0b`), informational messages use blue (`#3b82f6`), and debug indicators employ purple (`#8b5cf6`). These colors maintain sufficient contrast ratios to meet WCAG AA accessibility standards.

```css
--status-success: #10b981;   /* Successful operations, profit indicators */
--status-error: #ef4444;     /* Errors, loss indicators, critical alerts */
--status-warning: #f59e0b;   /* Warnings, neutral alerts */
--status-info: #3b82f6;      /* Informational messages */
--status-debug: #8b5cf6;     /* Debug logs, thinking indicators */
```

### Border and Shadow System

Borders use restrained grays (`#333333`, `#404040`) to define component boundaries without creating harsh lines. Shadows employ black with varying alpha values to create depth without adding color pollution. Three shadow levels provide subtle elevation cues: small shadows (`0 1px 2px rgba(0,0,0,0.3)`) for buttons, medium shadows (`0 4px 6px rgba(0,0,0,0.4)`) for cards, and large shadows (`0 10px 15px rgba(0,0,0,0.5)`) for modals and overlays.

```css
--border-color: #333333;     /* Standard borders */
--border-light: #404040;     /* Hover/focus borders */
--shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.3);
--shadow-md: 0 4px 6px rgba(0, 0, 0, 0.4);
--shadow-lg: 0 10px 15px rgba(0, 0, 0, 0.5);
```

## Typography

The type system balances technical precision with readability, using system fonts for body content and monospace families for code, numbers, and data display.

### Font Families

Sans-serif text leverages the system font stack (`-apple-system, BlinkMacSystemFont, "Segoe UI", "Roboto"...`) to ensure native rendering performance and familiar letterforms across platforms. Monospace content employs developer-focused fonts (`"JetBrains Mono", "Fira Code"`) that provide excellent character distinction for code snippets, option symbols, and numerical data.

```css
--font-sans: -apple-system, BlinkMacSystemFont, "Segoe UI", "Roboto", "Oxygen",
             "Ubuntu", "Cantarell", "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif;
--font-mono: "JetBrains Mono", "Fira Code", "Courier New", monospace;
```

### Type Scale

The modular scale creates clear information hierarchy without excessive size variation. Base body text sits at `1rem` (16px), with smaller utility sizes (`0.75rem`, `0.875rem`) for labels and metadata. Headings progress from `1.125rem` through `1.75rem`, using weight variation (600-700) alongside size to establish hierarchy. All font sizes respond to mobile breakpoints, reducing by approximately 15% below 650px to maintain comfortable reading on smaller screens.

```css
/* Desktop Scale */
h1: 1.75rem (28px), weight 600
h2: 1.5rem (24px), weight 600
h3: 1.25rem (20px), weight 600
body: 1rem (16px), line-height 1.6
small: 0.875rem (14px)
caption: 0.75rem (12px)

/* Mobile Scale (<650px) */
h1: 1.25rem (20px)
h2: 1.125rem (18px)
h3: 1rem (16px)
body: 0.875rem (14px)
```

### Financial Data Rendering

Price displays and P/L calculations use `font-variant-numeric: tabular-nums` to ensure consistent digit widths, preventing layout shifts when values update. This is critical for real-time price streams where numbers change hundreds of times per second. Monospace fonts combined with tabular figures create stable, scannable columns of numerical data.

```css
.price-display {
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;  /* Prevents layout shift */
}
```

## Spacing System

A consistent spacing scale built on 4px increments ensures predictable visual rhythm and simplifies responsive adjustments. The scale follows an exponential progression that creates natural grouping.

```css
--spacing-xs: 0.25rem;  /* 4px - Tight spacing between related elements */
--spacing-sm: 0.5rem;   /* 8px - Standard gaps in compound components */
--spacing-md: 1rem;     /* 16px - Default component padding */
--spacing-lg: 1.5rem;   /* 24px - Section spacing */
--spacing-xl: 2rem;     /* 32px - Major layout divisions */
```

On mobile devices below 650px, the spacing scale compresses by approximately 30% to maximize content density while maintaining touch targets. The mobile scale adjusts to `--spacing-xs: 0.2rem`, `--spacing-sm: 0.35rem`, `--spacing-md: 0.65rem`, ensuring comfortable information density on smaller screens.

## Component Design Standards

### Buttons

Primary buttons use cyan backgrounds with white text, providing maximum contrast for primary actions. Secondary buttons employ dark backgrounds with subtle borders, creating hierarchy without color competition. All buttons include `:disabled` states with 50% opacity and disabled cursors. Hover states add shadow elevation and subtle background darkening, creating tactile feedback without motion.

```css
/* Primary Button */
.btn-primary {
  background: var(--accent-primary);
  color: white;
  padding: 0.625rem 1.25rem;  /* 10px 20px */
  border-radius: 6px;
  font-weight: 500;
  font-size: 0.875rem;
  transition: all 0.2s ease;
}

.btn-primary:hover:not(:disabled) {
  background: var(--accent-hover);
  box-shadow: var(--shadow-md);
}

/* Secondary Button */
.btn-secondary {
  background: var(--bg-tertiary);
  color: var(--text-primary);
  border: 1px solid var(--border-color);
  padding: 0.625rem 1.25rem;
  border-radius: 6px;
}

.btn-secondary:hover:not(:disabled) {
  background: var(--bg-quaternary);
  border-color: var(--border-light);
}
```

Mobile buttons require minimum 44×44px touch targets to meet iOS and Android accessibility guidelines. Button padding increases to `0.75rem 1.25rem` and font-size increases to prevent accidental taps.

### Cards and Containers

Cards use `--bg-secondary` backgrounds with subtle borders (`--border-color`) and 12px border radius for modern, approachable aesthetics. Header sections within cards employ darker backgrounds (`--bg-darker`) to create internal hierarchy. The position card pattern demonstrates advanced card design with statistics sidebars, data tables, and real-time updating content.

```css
.card {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  padding: 20px;
  box-shadow: var(--shadow-sm);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
  padding-bottom: 16px;
  border-bottom: 1px solid var(--border-color);
}
```

### Form Inputs

Input fields use dark backgrounds (`--chat-input-bg: #1a1a1a`) with subtle borders that brighten on focus. Focus states employ cyan accent borders with a 3px soft shadow (`0 0 0 3px rgba(6,182,212,0.1)`) to create a glowing effect that signals interactivity. Placeholder text uses `--text-muted` for adequate contrast while maintaining visual hierarchy.

```css
input, textarea {
  background: var(--chat-input-bg);
  border: 1px solid var(--border-color);
  color: var(--text-primary);
  padding: 0.625rem;
  border-radius: 6px;
  font-size: 1rem;  /* Prevents iOS zoom on focus */
  transition: all 0.2s ease;
}

input:focus, textarea:focus {
  border-color: var(--accent-primary);
  box-shadow: 0 0 0 3px rgba(6, 182, 212, 0.1);
  outline: none;
}
```

On mobile, all inputs enforce 16px minimum font size to prevent iOS automatic zoom on focus, which disrupts the user experience.

### Badges and Tags

Status badges combine translucent backgrounds with solid text colors and matching borders to create depth. Badge colors follow semantic patterns: success (green), error (red), warning (amber), info (blue), debug (purple). Pill-shaped badges (`border-radius: 9999px`) distinguish ephemeral states from permanent labels.

```css
.badge {
  display: inline-flex;
  align-items: center;
  padding: 0.25rem 0.625rem;
  border-radius: 9999px;
  font-size: 0.75rem;
  font-weight: 600;
  letter-spacing: 0.025em;
}

.badge-success {
  background: rgba(16, 185, 129, 0.2);
  color: var(--status-success);
  border: 1px solid rgba(16, 185, 129, 0.3);
}
```

The custom tag system for option positions uses distinct color-coding: amber for Short positions, emerald for Long, blue for Calls, rose for Puts. This creates instant visual recognition of complex option strategies.

### Data Tables

Tables employ alternating row backgrounds (`rgba(255,255,255,0.02)`) for scannable rows, header backgrounds that distinguish column labels, and hover states that highlight interactive rows. Column alignment follows financial convention: left-align text labels, right-align numbers, center-align actions. The Element Plus table integration demonstrates proper CSS variable overrides to maintain design consistency.

```css
.data-table {
  --el-table-bg-color: transparent;
  --el-table-header-bg-color: rgba(255, 255, 255, 0.02);
  --el-table-border-color: var(--border-color);
  --el-table-row-hover-bg-color: rgba(255, 255, 255, 0.04);
  border-radius: 8px;
  border: 1px solid var(--border-color);
}

.data-table th {
  font-weight: 600;
  color: var(--accent-primary);
  text-transform: uppercase;
  font-size: 0.75rem;
  letter-spacing: 0.05em;
}
```

## Animation and Transitions

Animations enhance usability by providing feedback and guiding attention, but must remain subtle to avoid distraction during intensive monitoring sessions.

### Timing Functions

All transitions use `ease` or `cubic-bezier(0.4, 0, 0.2, 1)` easing for natural, organic motion. Durations range from 150ms for micro-interactions to 300ms for layout changes. Longer durations (2s) apply only to ambient animations like pulse effects that indicate background activity.

```css
/* Standard Transition */
transition: all 0.2s ease;

/* Layout Transitions */
transition: grid-template-columns 0.3s cubic-bezier(0.4, 0, 0.2, 1);

/* Micro-interactions */
transition: opacity 0.15s ease;
```

### Animation Patterns

The fade-in animation (`fadeIn`) provides elegant content entrance with vertical translation, creating a sense of content emerging into view. The pulse animation signals ongoing activity (thinking, processing, updating) with subtle opacity oscillation. Loading spinners use linear rotation for consistent mechanical motion.

```css
@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

/* Usage */
.fade-in { animation: fadeIn 0.3s ease-out; }
.pulse { animation: pulse 2s ease-in-out infinite; }
```

### Performance Considerations

High-frequency updates (price streams, WebSocket events) leverage RAF (RequestAnimationFrame) batching to prevent UI thread blocking. The `RafBatcher` utility ensures that thousands of updates per second coalesce into smooth 60fps rendering without freezing the interface. CSS containment (`contain: layout style`) prevents expensive recalculations from propagating across the component tree.

## Responsive Design

The responsive strategy employs a mobile-first philosophy with strategic breakpoints that accommodate real-world device categories.

### Breakpoint System

Three primary breakpoints handle the vast majority of devices. The mobile breakpoint (768px) transforms the desktop 3-column grid into a vertical stack. The tablet breakpoint (650px) triggers touch-optimized spacing and typography. Desktop variations (1024px, 1200px, 1400px, 1600px) adjust grid column widths to prevent cramped layouts on smaller monitors or excessive whitespace on larger displays.

```css
/* Mobile: <768px - Vertical stack */
@media (max-width: 768px) {
  .app-main {
    display: flex !important;
    flex-direction: column;
  }
}

/* Touch optimization: <650px */
@media (max-width: 650px) {
  button, .agent-card, .message-bubble {
    min-height: 44px;
    min-width: 44px;
  }
}

/* Desktop progressive enhancement */
@media (min-width: 1600px) { /* Expand chat width */ }
@media (min-width: 1400px) { /* Standard desktop */ }
@media (min-width: 1200px) { /* Compact desktop */ }
```

### Grid to Flex Transformation

Desktop uses CSS Grid (`grid-template-columns: 280px 1fr 418px`) for precise column control. Mobile abandons grid for flexbox column layout, allowing content to stack naturally with appropriate ordering. The EventStream content appears first, OrchestratorChat second, and AgentList last (or collapsed) to prioritize mission-critical content on small screens.

### Touch Optimization

Touch targets expand to 44×44px minimum on mobile, exceeding Apple's 44pt and Android's 48dp recommendations to prevent accidental activation. Input fields increase font size to 16px to prevent iOS zoom. Tap highlight colors (`-webkit-tap-highlight-color: rgba(6,182,212,0.2)`) provide visual feedback on tap. Scrollbars reduce to 4px width to maximize content area. Safe area insets (`env(safe-area-inset-bottom)`) ensure content remains accessible on notched devices.

```css
@media (max-width: 650px) {
  button {
    min-height: 44px;
    min-width: 44px;
  }

  input, textarea {
    font-size: 1rem;  /* Prevents iOS zoom */
    min-height: 44px;
  }

  -webkit-tap-highlight-color: rgba(6, 182, 212, 0.2);
}

/* Safe area support */
@supports (padding: env(safe-area-inset-bottom)) {
  .input-area {
    padding-bottom: max(0.75rem, env(safe-area-inset-bottom));
  }
}
```

## Visual Effects

### Elevation and Shadows

The three-tier shadow system creates depth without excessive decoration. Small shadows elevate buttons slightly above the surface, medium shadows lift cards and panels, and large shadows separate modals and overlays from the main interface. Shadows remain subtle to maintain the dark aesthetic without creating muddy contrast.

### Glassmorphism

While not currently implemented, research indicates glassmorphism (backdrop-filter: blur() with rgba transparency) could enhance modal overlays and dropdown menus. This technique creates depth through layered transparency rather than solid borders. Implementation would use `backdrop-filter: blur(10px)` with `background: rgba(26,26,26,0.8)` for frosted glass effects.

```css
/* Future glassmorphism pattern */
.glass-panel {
  background: rgba(26, 26, 26, 0.8);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.1);
}
```

### Scrollbar Styling

Custom scrollbars maintain aesthetic consistency with thin tracks (8px wide) using `--bg-secondary` backgrounds and `--border-color` thumbs. Hover states brighten to `--border-light` for discoverability. Mobile reduces scrollbar width to 4px to maximize touch-scrolling area.

```css
::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}

::-webkit-scrollbar-track {
  background: var(--bg-secondary);
}

::-webkit-scrollbar-thumb {
  background: var(--border-color);
  border-radius: 4px;
}

::-webkit-scrollbar-thumb:hover {
  background: var(--border-light);
}
```

## Markdown Content Styling

Chat messages and thinking blocks render rich markdown with syntax highlighting. Headings use cyan accents to maintain brand consistency, code blocks employ dark backgrounds with cyan highlights for inline code, blockquotes feature left-border accents with subtle background tinting, and tables receive alternating row backgrounds for scanability. Strong text receives both bold weight and cyan color with subtle text-shadow glow to draw attention.

```css
.message-content h1 {
  color: var(--accent-primary);
  border-bottom: 2px solid var(--border-color);
  font-size: 1.5rem;
  font-weight: 700;
}

.message-content code {
  background: rgba(6, 182, 212, 0.1);
  color: var(--accent-primary);
  border: 1px solid rgba(6, 182, 212, 0.2);
  padding: 0.2em 0.4em;
  border-radius: 3px;
}

.message-content strong {
  color: var(--accent-primary);
  text-shadow: 0 0 10px rgba(6, 182, 212, 0.3);
  font-weight: 700;
}
```

## Implementation Guidelines

### CSS Variable Usage

Always reference CSS variables rather than hard-coded values to maintain theme consistency and enable future theming capabilities. Use semantic naming (`--status-success` vs `--green`) to communicate intent.

### Mobile-First Development

Write base styles for mobile, then progressively enhance for larger screens. This ensures the mobile experience receives primary consideration and reduces CSS complexity.

### Performance Budget

Target 60fps animations on mid-range mobile devices. Use CSS containment (`contain: layout style`) on performance-critical components. Leverage `will-change` sparingly and only on actively animating elements. Batch high-frequency updates using RAF.

### Accessibility Requirements

Maintain WCAG AA contrast ratios (4.5:1 for normal text, 3:1 for large text). Ensure 44px minimum touch targets on mobile. Provide focus indicators distinct from hover states. Support keyboard navigation throughout the interface.

### Component Isolation

Use scoped styles in Vue SFC components to prevent style leakage. When global styles are necessary (Element Plus overrides), use high-specificity selectors or `:deep()` pseudo-selectors.

---

**Version**: 1.0
**Last Updated**: 2026-02-02
**Applies To**: Orchestrator Frontend Vue 3.4.x
