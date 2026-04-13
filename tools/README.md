# tools/

Developer utilities for maintaining the Solar Mason website.

## sync-nav.py

Single source of truth for the site-wide navigation **and footer**.
Propagates the canonical site chrome from `_templates/_nav-desktop.html`,
`_templates/_nav-mobile.html`, and `_templates/_footer.html` into every
HTML page in the repo.

(The script is named `sync-nav.py` for historical reasons — originally
it only handled the nav. It was extended to also handle the footer
since the two have identical drift problems and identical solutions.
Renaming would churn every reference in the repo and CI configs
without meaningful benefit.)

### When to run it

Run this whenever you change anything about the site chrome:

**Navigation**
- Adding, removing, renaming, or reordering a top-level nav item
- Editing a mega-menu dropdown (the grouped link lists inside each nav item)
- Changing the logo image, link target, or ALT text
- Restructuring the mobile drawer
- Updating login/register buttons in the mobile drawer footer
- Editing contact info in the mobile drawer footer
- Any other nav-level change

**Footer**
- Adding, removing, or renaming footer link columns (Engineering,
  Procurement, Construction, Incentives, Shop, Calculators, Company)
- Editing the links inside any footer column
- Updating the featured Bill Analyzer / Engineering Program links
- Changing brand text, address, phone, or social media links
- Updating the referral program URL
- Editing the legal / copyright line at the bottom
- Any other footer-level change

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

## Pre-commit hook (recommended)

A versioned pre-commit hook is shipped with the repo at
`.githooks/pre-commit`. It automatically runs `sync-nav.py --dry-run`
before every commit. If the hook detects that `_templates/` has drifted
from what's in the pages (someone edited a template but forgot to run
the sync), the commit is **blocked** with an explanation of how to fix
it. This catches the entire class of bug where a template edit lands
without its corresponding page-level propagation.

### Installing the hook

One-time per clone:

```bash
git config core.hooksPath .githooks
```

That's it. From now on, every `git commit` runs the check automatically.
The hook lives in the versioned `.githooks/` directory so every clone
that runs the command above gets the same enforcement.

### What it does on each commit

- **If everything is in sync:** silent, commit proceeds normally
- **If drift is detected:** commit is blocked with a banner explaining
  which files would be updated and telling you exactly how to fix it:

  ```
  ══════════════════════════════════════════════════════════════
    PRE-COMMIT BLOCKED: site chrome is out of sync with canonical
  ══════════════════════════════════════════════════════════════

  [...sync-nav.py --dry-run output listing drifted files...]

  To fix: run the sync script, review the diff, and commit everything:

      python3 tools/sync-nav.py
      git add -A
      git commit     # re-run your original commit command

  To bypass this check (not recommended):

      git commit --no-verify
  ```

- **If sync-nav.py itself errors** (missing template, broken canonical,
  Python not installed): the hook blocks with the error message so you
  can fix the underlying problem before committing.

### Graceful degradation

The hook does **not** hard-fail if `python3` or `tools/sync-nav.py` is
missing — it logs a warning to stderr and allows the commit through.
This prevents "broken clone" situations on machines without Python 3 or
on branches that don't yet have the sync script.

### Bypassing the hook

If you need to commit without running the check (e.g., committing a
WIP on an unrelated branch while the template is intentionally broken):

```bash
git commit --no-verify -m "WIP: broken template, will fix next commit"
```

Use this sparingly. The hook exists to catch real bugs.

### Verifying the hook is installed

```bash
git config --get core.hooksPath      # should print: .githooks
ls -l .githooks/pre-commit           # should show an executable file
```

### Why the hook runs against the working tree, not the index

The hook runs `sync-nav.py --dry-run` against the entire working tree,
not just the files staged for commit. This catches drift from unrelated
files too — if someone edited a template three commits ago and never
ran the sync, the hook blocks the NEXT commit regardless of what that
commit is for. This feels slightly aggressive but is the right behavior:
you want to know about drift as soon as possible, not when you
eventually happen to touch a template again.

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
