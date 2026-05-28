# Style Guide

This guide keeps the Agentic Underwriting app visually consistent as the product grows.

## Design Goal

The app should feel like a high-scale technical underwriting workstation: light, calm, dense, trustworthy, and operational. It should look closer to a modern risk platform than a marketing website.

Use the UI to help underwriters scan, compare, retrieve, decide, and document work quickly.

## Visual Tone

- Professional and technical.
- Light background with strong information hierarchy.
- Clear separation between navigation, chat, and underwriting surfaces.
- Quiet color, strong spacing, and crisp borders.
- Minimal decoration. Information is the design.

Avoid:

- Heavy dark-blue screens.
- Purple/blue gradient-heavy themes.
- Large marketing hero compositions inside the app.
- Decorative blobs, glow effects, or purely atmospheric visuals.
- Oversized cards where compact operational tables or panels work better.

## Core Colors

Use the existing CSS variables in `public/styles.css` as the main palette.

```css
--bg: #f4f7fb;
--left: #24344d;
--left-soft: #2f405b;
--panel: #ffffff;
--surface: #f6f8fb;
--ink: #111827;
--muted: #667085;
--line: #d8e0ea;
--accent: #2563eb;
--accent-dark: #1d4ed8;
--accent-soft: #eaf1ff;
--cyan-soft: #e8f7ff;
--amber: #b7791f;
--red-soft: #fff4f2;
```

Use colors this way:

- `--bg`: page background.
- `--left` and `--left-soft`: left panel and user chat bubble family.
- `--panel`: primary white panels.
- `--surface`: subtle secondary surfaces.
- `--ink`: primary readable text.
- `--muted`: secondary labels and metadata.
- `--line`: borders, separators, table lines.
- `--accent`: primary action, active tab, chart highlight.
- `--accent-soft`: selected or active pale background.
- `--red-soft`: overdue, warning, or required-attention surfaces.
- Green selected-state highlight should be used sparingly for agent-selected surfaces only.

## Typography

- Use the existing system sans stack.
- Keep letter spacing at `0`.
- Avoid viewport-scaled body text.
- Use compact headings inside panels.
- Reserve large type for page-level titles only.
- Metadata labels should be smaller, muted, and scannable.

Recommended hierarchy:

- Page title: 28-36px.
- Section title: 18-24px.
- Card title: 14-16px.
- Body: 13-15px.
- Metadata and chips: 11-13px.

## Layout

Main workbench:

- Left panel: chat history, documents, file selection, upload.
- Center: key information, messages, composer.
- Right panel: Details, Analytics, Tasks, Note.
- Expanded pages: use the available width, show a clear title, and provide `Back to Chat` on the top right.

Search page:

- Search remains centered.
- Top-right utilities contain Dev, Business Demo, and Login/user menu.
- Add Submission lives under Search a Submission.
- Submission examples stay compact under the search bar.

Dev page:

- Keep it diagnostic and data-rich.
- Prefer clear sections, tables, workflow diagrams, and contract cards.
- Show data sources, schemas, tool contracts, traces, and support data in separate tabs.

## Components

Buttons:

- Primary action: solid accent or existing `send-button`.
- Secondary action: `ghost-button`.
- Small operational action: `selection-action`.
- Icon-only actions should use a familiar symbol and an accessible label.
- Destructive actions should be visually restrained until confirmation, then clearly warn in the modal/browser prompt.

Cards:

- Use cards for repeated items, modals, tools, and compact data blocks.
- Do not nest full cards inside cards.
- Keep border radius at or below 8px unless an existing component requires otherwise.
- Use borders and subtle shadows only when they improve separation.

Tabs:

- Use tabs for switching surfaces in the right panel and Dev console.
- Active tab should be obvious but not loud.
- Expanded pages should hide unrelated top tabs when they become distracting.

Tables:

- Use tables for broker, claim, analytics DB, and operational data.
- Keep rows compact.
- Use muted labels for secondary fields.
- Preserve source identifiers such as submission id, company id, broker id, and claim id.

Charts:

- Analytics should show model output with understandable drivers.
- Waterfall features should be sorted by true marginal contribution.
- Positive/negative colors should intensify with contribution magnitude.
- Tooltips or hover titles should explain feature names and definitions.

## Interaction Patterns

Chat:

- Show process steps when the agent retrieves information, selects documents, writes notes/guides/tasks, or routes to analytics.
- Show citations below answers.
- Add copy buttons beside generated email drafts or reusable text.
- Preserve Enter to send and Shift+Enter for a line break.

Documents:

- Auto is the default file-selection mode.
- In Auto mode, agent-selected files can be checked and highlighted.
- Outside Auto mode, the agent should not override manual selection.
- File cards should stay compact and stable.
- File delete action belongs inside the file card, bottom right, without creating a separate boxed control.

Tasks:

- Tasks stay editable after creation.
- Calendar should support years from 2000 through 2100.
- Dates with tasks should use a subtle light red shade.
- Clicking a date filters task details below the calendar.

Stages:

- Stage submission locks only checked stages.
- Submission requires a warning confirmation.
- Locked stages should be visibly locked and not editable.

Guide:

- Guides influence system prompt behavior.
- UI should support add, edit, delete.
- Existing guide boxes show `Guide 1`, `Guide 2`, etc.

Notes:

- Notes are ground-truth context but not system prompt instructions.
- UI should support add, edit, delete using the same pattern as Guide.

## Content Rules

- Use underwriting language: submission, account, insured, broker, evidence, claims, quote readiness, referral, bind readiness, controls, subjectivity, appetite.
- Do not use vague labels when a specific workflow label exists.
- Use `Tasks` instead of `Follow Up` because tasks may include many to-do types.
- Use `Analytics` instead of `Risk Analytics`.
- Keep explanatory text concise in the app. Put deeper explanation in README, Dev, or Business Demo pages.

## Accessibility

- Keep contrast strong enough for primary text and controls.
- Use semantic buttons for actions.
- Add accessible labels for icon-only controls.
- Keep visible focus states.
- Do not rely only on color to convey selected, warning, or locked states.

## Responsive Behavior

- Main workbench should preserve functional zones on desktop.
- On narrower screens, panels may stack or scroll, but controls must remain usable.
- Text must not overflow buttons, cards, tabs, or data blocks.
- Long metadata values should truncate cleanly and expose full values through title attributes, details rows, or expanded views.

## When Adding New UI

Before finishing, check:

- Does it use existing variables and component classes?
- Does it match the technical light theme?
- Is the data coming from an API or structured local store rather than hard-coded UI values?
- Are empty, loading, error, and selected states handled?
- Does it work with login/permission state if protected?
- Does the README or Dev page need an update?
