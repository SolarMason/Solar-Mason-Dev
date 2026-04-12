# tools/

Developer utilities for maintaining the Solar Mason website.

## sync-nav.py

Single source of truth for the site-wide navigation. Propagates the canonical
nav HTML from `_templates/_nav-desktop.html` and `_templates/_nav-mobile.html`
into every HTML page in the repo that uses the standard site chrome.

### When to run it

Run this whenever you change anything about the navigation:

- Adding, removing, renaming, or reordering a top-level nav item
- Editing a mega-menu dropdown (the grouped link lists inside each nav item)
- Changing the logo image, link target, or ALT text
- Restructuring the mobile drawer
- Updating login/register buttons in the mobile drawer footer
- Editing contact info in the mobile drawer footer
- Any other nav-level change

### How to run it

```bash
# Check what would change (safe, no writes)
python3 tools/sync-nav.py --dry-run

# Apply the canonical nav to every page
python3 tools/sync-nav.py

# Show a decision for every file examined
python3 tools/sync-nav.py --verbose
```

### Typical workflow

1. Edit `_templates/_nav-desktop.html` (and/or `_templates/_nav-mobile.html`)
   with your nav changes. These are real HTML snippets — just the `<nav>` block
   by itself, not a full page. You can open them in any editor.
2. Run `python3 tools/sync-nav.py --dry-run` to see what would change.
   The script should report exactly one file updated per variant if your
   edit is a net change, or zero if you only changed whitespace.
3. Run `python3 tools/sync-nav.py` (no flags) to apply the changes.
4. Review with `git diff` to confirm the changes look right.
5. Commit the whole thing — both the template edits AND the propagated
   page changes — in one commit. This keeps the template and the rendered
   pages in lockstep in the git history.
6. Push.

### How it works

The script walks every `.html` file in the repo (skipping `.git`,
`node_modules`, `_templates`, `tools`, and `datasheets/` — see the
`EXCLUDED_DIRS` constant in the script for the full list). For each file:

1. It locates the existing `<nav class="navbar" id="navbar"> ... </nav>`
   block by walking the HTML and counting `<nav>` / `</nav>` tags to find
   the matching close (robust against nested nav elements, though we
   don't have any).
2. It locates the existing `<nav class="mobile-drawer" id="mobile-drawer">
   ... </nav>` block the same way.
3. If both exist and either differs from the canonical, it replaces them
   with the canonical versions byte-for-byte. Mobile is replaced first
   because it appears later in the page source, so the replacement doesn't
   shift the desktop block's byte offsets.
4. If a page is missing one or both nav blocks entirely, the script skips
   that file. Currently this only applies to `datasheets/index.html`, which
   is a standalone minimal equipment directory with no site chrome.

### Idempotency

The script is **idempotent**. If the canonical already matches what's in
every page, running the script produces zero changes and exits cleanly.
This means you can safely run it as many times as you want — you don't
need to track whether it's "already been run."

### Safety

The script does not modify anything outside the two `<nav>` blocks. It
will not touch your page content, your styles, your scripts, your
footers, or your `<head>` tags. If something outside those two blocks
changes, the bug is elsewhere.

The script uses byte-exact matching to find the nav regions. If someone
hand-edits a page's nav in a way that breaks the opening-tag anchor
(`<nav class="navbar" ...>`), the script will fail to find the block on
that page and skip it with a warning. This is the right behavior — you
probably want to know if a page has drifted outside the canonical.

### Why this exists

Solar Mason is deployed as static HTML on GitHub Pages. There is no build
step, no templating engine, and no server-side includes. Every page is a
fully self-contained HTML file with the nav inlined. This is great for
serving (zero build time, infinite CDN caching) but terrible for nav
maintenance — without this script, any nav change would require editing
every page by hand, which is how drift happens.

This script gives us a **single source of truth** (the files in
`_templates/`) that gets **propagated** into every page on demand. It's
the middle ground between "build a real templating engine" (overkill for
this site) and "hand-edit every page" (obviously unsustainable).

---

## Adding a new page

When creating a new HTML page from scratch, use
`_templates/page-template.html` as your starting point. It's a fully-formed
empty page with:

- The canonical `<nav>` blocks already inlined (both desktop and mobile)
- The canonical footer already inlined
- A blank `<main>` region where your page content goes
- A `<title>` placeholder you should edit

After copying the template and filling in your content, run
`python3 tools/sync-nav.py` once to make sure your new page picks up any
nav changes that have landed since the template was last synced. The
script will report "unchanged" if the template was freshly synced, or
"updated" if the template was stale.
