# Design System Document

## 1. Overview & Creative North Star: "The Synthetic Atelier"
This design system moves beyond the "utilitarian dark mode" of standard IDEs to create a high-end, editorial environment for focused technical work. The Creative North Star is **The Synthetic Atelier**—a digital workshop that feels bespoke, precision-engineered, and atmospheric.

While inspired by the structural efficiency of Discord and VS Code, we reject the "boxy" look of standard frameworks. Instead, we embrace **intentional asymmetry**, **tonal layering**, and **optical breathing room**. By prioritizing depth over lines and atmosphere over flat gray, we create an interface that feels like a premium physical tool rather than just another web app.

---

## 2. Colors & Surface Philosophy
The palette is rooted in deep obsidian tones, punctuated by high-performance teals and organic greens.

### The "No-Line" Rule
Standard 1px borders are prohibited for sectioning. Structural boundaries must be defined solely through background color shifts or subtle tonal transitions. For example, a sidebar should sit as `surface-container-low` against a `surface` background. This creates a more immersive, "infinite" feel.

### Surface Hierarchy & Nesting
Treat the UI as a series of physical layers. We use a "stacking" logic to denote importance:
- **Base Layer:** `surface` (#111317) – The canvas.
- **Structural Sections:** `surface-container-low` (#1a1c1f) – Sidebars, activity bars.
- **Primary Content Area:** `surface-container` (#1e2023) – Main editor or dashboard.
- **Interactive Elements:** `surface-container-high` (#282a2e) – Hover states and modals.
- **Top-Level Popovers:** `surface-container-highest` (#333539) – Tooltips and menus.

### The "Glass & Gradient" Rule
To elevate the "Run" actions and primary states:
- **Signature CTAs:** Use a subtle linear gradient for `primary` elements (transitioning from `primary` #6cdba4 to `primary-container` #3caf7c).
- **Glassmorphism:** Floating panels (like command palettes) must use `surface-container-highest` at 80% opacity with a `20px` backdrop-blur. This integrates the component into the environment rather than making it feel "pasted on."

---

## 3. Typography: Editorial Precision
We utilize **Inter** to bridge the gap between technical readability and high-end aesthetic.

- **Display & Headlines:** Use `display-sm` for hero titles. Tighten letter-spacing (-0.02em) to create an authoritative, editorial feel.
- **Hierarchy of Focus:** Use `title-md` for section headers, but keep them low-contrast (`on-surface-variant`) until they are active, at which point they transition to `on-surface` and `secondary` (#55d8e1) underlines.
- **Monospace Integration:** While the primary font is Inter, code-adjacent labels should use `label-sm` with increased tracking (+0.05em) to maintain a "technical blueprint" aesthetic.

---

## 4. Elevation & Depth
We replace traditional shadows and borders with **Tonal Layering**.

- **The Layering Principle:** Place a `surface-container-lowest` card on a `surface-container-low` section to create a soft, natural "recessed" lift. No shadow required.
- **Ambient Shadows:** For floating modals, use an extra-diffused shadow: `0px 24px 48px rgba(0, 0, 0, 0.4)`. The shadow must never be pure black; it should be a deep tint of the background color to mimic natural light dispersion.
- **The "Ghost Border" Fallback:** If a border is required for extreme accessibility cases, use the `outline-variant` (#3c494a) at **15% opacity**. This provides a "suggestion" of a boundary without breaking the tonal flow.

---

## 5. Components

### Buttons
- **Primary ('Run'):** High-contrast `primary` (#6cdba4) background. No border. Subtle 4px corner radius (`md`). Use `on-primary` for text.
- **Secondary (Action):** `surface-container-highest` background with `secondary` (#55d8e1) text.
- **Tertiary (Ghost):** No background. Text uses `on-surface-variant`. On hover, the background shifts to `surface-container-low`.

### Input Fields & Dropdowns
- **The Obsidian Input:** Use `surface-container-lowest` for the input track. This creates a "carved out" look.
- **Focus State:** Instead of a thick border, use a 1px `secondary` (#55d8e1) bottom-border (underline) and a subtle `surface-bright` glow.
- **Selection Chips:** Use `secondary-container` with `on-secondary-container` text. Corners should be `full` (pill-shaped) to contrast with the angular layout.

### Cards & Lists
- **Layout:** Forbid divider lines. Use `1.75rem` (8) of vertical space from the Spacing Scale to separate list groups.
- **Interaction:** List items should use a `0.4rem` (2) padding-x and transition to `surface-container-high` on hover with a `secondary` vertical "active indicator" (2px wide) on the far left.

### Contextual Components
- **The Activity Bar:** A slim vertical rail using `surface-container-lowest`. Icons use `on-surface-variant`, switching to `secondary` when active.
- **Status Pills:** Small, high-saturation indicators using `tertiary` (#ffb68d) for warnings and `primary` for success, placed with precision in the bottom right of containers.

---

## 6. Do’s and Don’ts

### Do:
- **Use Asymmetry:** Place metadata (labels) in `label-sm` aligned to the right, while primary content is on the left, to create a sophisticated balance.
- **Embrace Negative Space:** Use `2.25rem` (10) margins between major functional blocks. Let the UI breathe.
- **Layer by Luminance:** Always move from darkest (base) to lightest (interactive elements) as you move "up" in the Z-index.

### Don’t:
- **Don’t use 100% white:** Never use `#ffffff` for text. Use `on-surface` (#e2e2e7) to reduce eye strain and maintain the atmospheric mood.
- **Don’t use structural lines:** If you feel the need to draw a line, try using a `0.2rem` (1) gap or a background color shift instead.
- **Don’t use standard "Drop Shadows":** Avoid high-opacity, tight shadows. They make the UI look "cheap" and dated.