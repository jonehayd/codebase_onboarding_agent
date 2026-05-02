---
name: Technical Precision
colors:
  surface: "#141313"
  surface-dim: "#141313"
  surface-bright: "#3a3939"
  surface-container-lowest: "#0e0e0e"
  surface-container-low: "#1c1b1b"
  surface-container: "#201f1f"
  surface-container-high: "#2a2a2a"
  surface-container-highest: "#353434"
  on-surface: "#e5e2e1"
  on-surface-variant: "#c4c7c8"
  inverse-surface: "#e5e2e1"
  inverse-on-surface: "#313030"
  outline: "#8e9192"
  outline-variant: "#444748"
  surface-tint: "#c6c6c7"
  primary: "#ffffff"
  on-primary: "#2f3131"
  primary-container: "#e2e2e2"
  on-primary-container: "#636565"
  inverse-primary: "#5d5f5f"
  secondary: "#c6c6cf"
  on-secondary: "#2f3037"
  secondary-container: "#45464e"
  on-secondary-container: "#b4b4bd"
  tertiary: "#ffffff"
  on-tertiary: "#2f3131"
  tertiary-container: "#e2e2e2"
  on-tertiary-container: "#636565"
  error: "#ffb4ab"
  on-error: "#690005"
  error-container: "#93000a"
  on-error-container: "#ffdad6"
  primary-fixed: "#e2e2e2"
  primary-fixed-dim: "#c6c6c7"
  on-primary-fixed: "#1a1c1c"
  on-primary-fixed-variant: "#454747"
  secondary-fixed: "#e2e1eb"
  secondary-fixed-dim: "#c6c6cf"
  on-secondary-fixed: "#1a1b22"
  on-secondary-fixed-variant: "#45464e"
  tertiary-fixed: "#e2e2e2"
  tertiary-fixed-dim: "#c6c6c7"
  on-tertiary-fixed: "#1a1c1c"
  on-tertiary-fixed-variant: "#454747"
  background: "#141313"
  on-background: "#e5e2e1"
  surface-variant: "#353434"
typography:
  display:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: "600"
    lineHeight: 32px
    letterSpacing: -0.02em
  header-md:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: "500"
    lineHeight: 24px
    letterSpacing: -0.01em
  body-base:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: "400"
    lineHeight: 20px
  body-muted:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: "400"
    lineHeight: 20px
  code-sm:
    fontFamily: monospace
    fontSize: 13px
    fontWeight: "400"
    lineHeight: 18px
  label-caps:
    fontFamily: Inter
    fontSize: 11px
    fontWeight: "600"
    lineHeight: 16px
    letterSpacing: 0.05em
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  unit: 4px
  xs: 0.25rem
  sm: 0.5rem
  md: 1rem
  lg: 1.5rem
  xl: 2rem
  gutter: 1.5rem
  container-max: 1200px
---

## Brand & Style

The design system is engineered for developers who value speed, clarity, and terminal-like efficiency. The brand personality is clinical and unobtrusive, positioning the tool as a high-performance utility rather than a lifestyle application. It evokes a sense of "Flow State"—minimizing cognitive load through extreme visual reduction.

The aesthetic follows a **High-Contrast Minimalism** approach. It utilizes a "Darkroom" philosophy where the interface recedes into the background, allowing code and architectural data to remain the primary focus. There are no decorative elements; every line, gap, and character serves a functional purpose.

## Colors

The palette is strictly monochromatic with functional semantic accents.

- **Base Surfaces:** Use `#000000` for the deepest layout foundations and `#09090b` for secondary containers or cards.
- **Borders:** A consistent `#27272a` creates a hairline distinction between sections without adding visual weight.
- **Typography:** Headlines must use pure white (`#ffffff`) for maximum legibility. Body text uses a muted zinc/gray to establish hierarchy and reduce eye strain during long sessions.
- **Accents:** Color is reserved exclusively for state and status. Green indicates a synchronized or completed state, Amber indicates active processing or indexing, and Red indicates a configuration or connection failure.

## Typography

This design system uses a dual-type approach. **Inter** handles all UI labels, navigation, and instructional text, providing a neutral, highly readable sans-serif foundation. For repository names, file paths, and code snippets, a **Monospace** stack (JetBrains Mono or system monospace) is mandatory to maintain the developer-centric feel.

Information density is controlled through rigid line-heights. Use `label-caps` for metadata headers and `body-muted` for descriptions to ensure clear vertical scanning.

## Layout & Spacing

The layout philosophy is based on a **Fixed Grid** with generous whitespace. Elements are aligned to a 4px baseline grid to ensure mathematical precision.

- **Structure:** Use a 12-column grid for main dashboards, but prioritize centered, narrow-column layouts (600px-800px) for onboarding flows to maintain focus.
- **Rhythm:** Use `1.5rem` (24px) for major section gaps and `0.5rem` (8px) for internal component spacing.
- **Density:** The design should feel "airy" but purposeful. Do not crowd elements; let the dark background act as a separator.

## Elevation & Depth

This design system avoids traditional shadows to maintain a flat, fast-feeling interface. Depth is communicated via **Tonal Layering** and **Low-Contrast Outlines**.

- **Level 0 (Base):** `#000000` for the page background.
- **Level 1 (Surface):** `#09090b` for cards, modals, or sidebars, outlined with a 1px solid border of `#27272a`.
- **Level 2 (Interaction):** Active or hovered states are indicated by a slight brightening of the border or a very subtle background shift to `#18181b`.
- **Focus:** No blurs or glows. Use sharp 1px white or blue rings for keyboard navigation focus states.

## Shapes

The design system utilizes **Soft** geometry. To mirror the precision of a code editor, all UI components use a 4px to 6px border radius.

- **Components:** Buttons, input fields, and status badges use the base `rounded` (4px) setting.
- **Large Containers:** Modals or large cards may use `rounded-lg` (8px) for a slightly softer feel, though sharp edges are preferred for more technical views.
- **Checkboxes:** Strictly 4px or sharp corners to distinguish from more "consumer-facing" rounded patterns.

## Components

### Status Badges

Badges are compact, using a subtle background tint and high-contrast text.

- **Processing:** Amber text on a very dark amber wash (or just amber text with a 1px amber border).
- **Completed:** Green text with a simple leading dot icon.
- **Failed:** Red text, used sparingly for immediate attention.

### Input Fields

Inputs are minimal:

- **Default:** Transparent background with a 1px `#27272a` border.
- **Focus:** Border changes to white or a subtle primary accent; no outer glow.
- **Placeholder:** Muted gray text (`#52525b`), using the monospace font for repo URL inputs.

### Buttons

- **Primary:** Solid white background with black text. No gradients.
- **Secondary:** Transparent background with a white border.
- **Ghost:** No border, text-only until hover.

### Code Blocks & Repository Lists

List items should feature a high-contrast title (white), a monospace sub-label (muted gray), and a right-aligned status badge. Hover states on list items should change the background to `#09090b` and the border to `#3f3f46`.
