# Design tokens

The UI uses the Pipenzo "Flow look" tokens in `architecture_explorer/static/tokens.css`: black page in dark, alpha-style layers, one accent (Pipenzo yellow `#FECE02`), red only for danger. The accent rules below take precedence over the header comment of `tokens.css`.

## Source and resync

- Source: `jortega0033/clip-to-reel-studio`, `extension/sidepanel/tokens.css` at commit `a13378ce73e5b27213c9a200fc960ec93afef054` (2026-11-21).
- Resync: copy that file over `architecture_explorer/static/tokens.css`. Nothing else. Never edit the copy.
- The server lists `tokens.css` in `STATIC_FILES` (`architecture_explorer/server.py`); `index.html` loads it before `app.css`.
- The header comment of `tokens.css` says yellow is used only on the primary button, the current-step node and a few other marks. That text is narrower than the rules below and is out of date. This document takes precedence. The copy must stay identical to the source, so the comment is not edited here.

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
- Accent (D1, UI rule 8): yellow is used for the primary action, the current-step marker and the current selection. Owner decision, 2026-11-23. How a selection is drawn (recommended by the orchestrator, adopted under the owner's delegation of the same day): a solid `--primary` fill with `--on-primary` text, not only a yellow border (a yellow border has about 1.5:1 against white on light), plus a second sign that is not colour (weight, icon or text) and the existing `aria` attribute (for example `aria-selected` or `aria-current`). Never a tint with a same-hue border, and never a thick one-sided border.
- Focus ring (D2): `--focus` is a focus indicator and is exempt from the accent limit, including where it is yellow in dark. A ticket that says the focus style stays unchanged means the rule on `main` after the token pull request. Recommended by the orchestrator, adopted under the owner's delegation of 2026-11-23.
- Themes (D3): contrast and no-colour-alone checks cover both the light block and the dark block of `tokens.css`. Recommended by the orchestrator, adopted under the owner's delegation of 2026-11-23.
- Text never sits on a bare alpha layer; use the opaque surface tokens.
- Canvas or inline colours read a token with `getComputedStyle(document.documentElement).getPropertyValue('--token')`. The app has none today.

## Current state of the page

Some selections in the page are still marked in a neutral colour. The page follows these rules in ticket work. That work is not done yet.

## Light and dark

`:root` holds the light theme. A block inside the operating system colour scheme media query for dark overrides it. The page follows the OS setting (`color-scheme: light dark`); there is no manual switch. Dark is the primary design.
