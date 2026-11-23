# Design tokens

The UI uses the Pipenzo "Flow look" tokens in `architecture_explorer/static/tokens.css`: black page in dark, alpha-style layers, one accent (Pipenzo yellow `#FECE02`), red only for danger.

## Source and resync

- Source: `jortega0033/clip-to-reel-studio`, `extension/sidepanel/tokens.css` at commit `a13378ce73e5b27213c9a200fc960ec93afef054` (2026-11-21).
- Resync: copy that file over `architecture_explorer/static/tokens.css`. Nothing else. Never edit the copy.
- The server lists `tokens.css` in `STATIC_FILES` (`architecture_explorer/server.py`); `index.html` loads it before `app.css`.

## Token names by role

- Surfaces: `--bg` (page), `--surface` (cards, panels), `--bg-raised` (inputs), `--bg-sunken` (wells, chips, secondary buttons), `--hero-bg`, `--ink` (dark block).
- Text: `--fg`, `--muted`, `--faint`, `--on-ink`, `--on-ink-muted`, `--on-hero`, `--on-hero-muted`, `--on-primary`.
- Lines: `--border`, `--hairline`, `--control-border`, `--input-border`, `--ink-border`, `--hero-border`.
- Accent: `--primary`, `--primary-press`, `--primary-edge`, `--focus`, `--ring-accent`.
- Status: `--danger`, `--danger-bg`, `--ok`, `--ok-bg`, `--warn-fg`, `--warn-bg`, `--success`, `--info`.
- State layers: `--state-hover`, `--state-selected`, `--btn-secondary`, `--btn-secondary-border`, `--ink-hover`.
- Shape, type, motion: `--radius-*`, `--space-1`, `--font`, `--font-display`, `--mono`, `--shadow-*`, `--dur-1`, `--ease-*`.

## Rules

- New UI uses these tokens. No new colour literals in CSS, JavaScript or HTML.
- Yellow only on the primary action and the current-step marker. Text never sits on a bare alpha layer; use the opaque surface tokens.
- Canvas or inline colours read a token with `getComputedStyle(document.documentElement).getPropertyValue('--token')`. The app has none today.

## Light and dark

`:root` holds the light theme. A block inside the operating system colour scheme media query for dark overrides it. The page follows the OS setting (`color-scheme: light dark`); there is no manual switch. Dark is the primary design.
