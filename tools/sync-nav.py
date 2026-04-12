#!/usr/bin/env python3
"""
sync-nav.py — Propagate the canonical Solar Mason navigation to every page.

This is the single source of truth for the site-wide nav. When the nav needs
to change (add a menu item, reorder, rename, restructure), edit it ONCE in
_templates/_nav-desktop.html or _templates/_nav-mobile.html, then run:

    python3 tools/sync-nav.py

and every HTML page with the standard navbar will have its nav block replaced
with the canonical version. The script is idempotent — running it when
nothing has changed is a no-op that exits cleanly.

WHAT IT DOES

  For every .html file under the repo root (excluding .git, node_modules,
  _templates, tools):

    1. Locate the existing <nav class="navbar" id="navbar"> ... </nav> block
    2. Locate the existing <nav class="mobile-drawer" id="mobile-drawer"> ... </nav> block
    3. If both are present and either differs from the canonical, replace them
    4. If either block is missing, skip the file (assumed to be a standalone
       page with no site chrome, like datasheets/index.html)

  It does NOT touch any other part of the page — footers, page body, <head>,
  scripts. Only the two <nav> blocks are within its scope.

WHY TWO FILES

  Desktop and mobile are separate because they have very different HTML
  structures. Desktop uses a <ul class="nav-list"> with button triggers that
  open absolutely-positioned mega menus elsewhere on the page. Mobile uses a
  fullscreen drawer with inline accordions. Keeping them as separate canonical
  templates makes each easier to edit.

ADDING A NEW PAGE

  When creating a new page from scratch, copy _templates/page-template.html
  as your starting point. It already has the canonical nav + footer + basic
  chrome baked in. After copying, run this script to pick up any nav changes
  that have happened since the template was last updated.

IDEMPOTENCY

  The script compares each file's current nav HTML against the canonical
  byte-for-byte. If they match, the file is skipped and the diff stays
  clean. Running the script multiple times in a row will only produce a
  single non-empty run.

USAGE

    python3 tools/sync-nav.py              # apply changes
    python3 tools/sync-nav.py --dry-run    # show what would change, no writes
    python3 tools/sync-nav.py --verbose    # explain every file decision

EXIT CODES

    0 — success (may have modified files, or been a no-op)
    1 — error (could not find templates, could not parse a file, etc.)
    2 — dry-run found differences that would be applied

INTEGRATION NOTES

  This script does not run in GitHub Actions. The deploy workflow
  (.github/workflows/deploy.yml) is pure GitHub Pages static hosting with
  no build step. Nav sync is a LOCAL developer workflow:

      edit _templates/_nav-desktop.html
      python3 tools/sync-nav.py
      git add -A
      git commit -m "Nav: ..."
      git push

  If you want, you could add this as a pre-commit hook so editing a
  template without running the sync becomes impossible to commit. For now
  it's a manual step documented in tools/README.md.
"""

from __future__ import annotations
import argparse
import hashlib
import os
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = REPO_ROOT / '_templates'
DESKTOP_TEMPLATE = TEMPLATES_DIR / '_nav-desktop.html'
MOBILE_TEMPLATE  = TEMPLATES_DIR / '_nav-mobile.html'

# Directories to skip entirely when walking the repo.
EXCLUDED_DIRS = {'.git', 'node_modules', '_templates', 'tools', 'datasheets'}
# Note: datasheets/ is excluded because datasheets/index.html is a standalone
# minimal equipment directory with no site nav. If you add other pages under
# /datasheets/ in the future that DO need the full nav, remove this exclusion
# and the script will handle them correctly.


def log(msg: str, *, verbose: bool = False, only_verbose: bool = False) -> None:
    if only_verbose and not verbose:
        return
    print(msg)


def short_hash(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()[:10]


def find_nav_block(html: str, nav_class: str) -> tuple[int, int] | None:
    """
    Find the byte span of a <nav class="{nav_class}" ...>...</nav> block.

    Walks the HTML looking for the opening tag, then scans forward counting
    <nav and </nav> tags to find the matching close. Returns (start, end)
    byte offsets of the full block including the outer tags, or None if the
    block is not present in this file.
    """
    m = re.search(rf'<nav class="{re.escape(nav_class)}"', html)
    if not m:
        return None

    pos = m.end()
    depth = 1
    while depth > 0:
        nxt_open  = html.find('<nav', pos)
        nxt_close = html.find('</nav>', pos)
        if nxt_close == -1:
            # Unbalanced nav tag — give up
            return None
        if nxt_open != -1 and nxt_open < nxt_close:
            depth += 1
            pos = nxt_open + 4
        else:
            depth -= 1
            pos = nxt_close + 6
    return (m.start(), pos)


def replace_nav_blocks(
    html: str,
    desktop_canonical: str,
    mobile_canonical: str,
) -> tuple[str, bool, bool]:
    """
    Replace the desktop and mobile nav blocks in an HTML string with the
    canonical versions. Returns (new_html, desktop_changed, mobile_changed).

    If a file is missing one of the nav blocks entirely, that block is left
    alone — we do not INJECT navs into pages that don't already have them.
    That would be a much more invasive change and would require knowing
    where to insert the block, which varies by page layout. Pages without
    nav blocks are assumed to be intentionally nav-less (like
    datasheets/index.html).
    """
    desktop_span = find_nav_block(html, 'navbar')
    mobile_span  = find_nav_block(html, 'mobile-drawer')

    desktop_changed = False
    mobile_changed  = False

    # Apply mobile first, then desktop. Order matters because replacing one
    # changes the byte offsets of the other. We go mobile-first because the
    # mobile drawer always appears AFTER the desktop navbar in the page
    # source, so replacing it doesn't shift the desktop span.
    if mobile_span is not None:
        existing_mobile = html[mobile_span[0]:mobile_span[1]]
        if existing_mobile != mobile_canonical:
            html = html[:mobile_span[0]] + mobile_canonical + html[mobile_span[1]:]
            mobile_changed = True
        # Re-locate desktop span in case of any offset shift (shouldn't matter
        # since mobile is after desktop, but we re-resolve to be safe)

    if desktop_span is not None:
        # Re-find desktop span in case html was modified above
        desktop_span = find_nav_block(html, 'navbar')
        if desktop_span is not None:
            existing_desktop = html[desktop_span[0]:desktop_span[1]]
            if existing_desktop != desktop_canonical:
                html = html[:desktop_span[0]] + desktop_canonical + html[desktop_span[1]:]
                desktop_changed = True

    return (html, desktop_changed, mobile_changed)


def walk_html_files(root: Path) -> list[Path]:
    """Yield every .html file under root, skipping EXCLUDED_DIRS."""
    result = []
    for dirpath, dirnames, filenames in os.walk(root):
        # Mutate dirnames in place so os.walk skips excluded dirs entirely
        dirnames[:] = [d for d in dirnames if d not in EXCLUDED_DIRS and not d.startswith('.')]
        for fn in filenames:
            if fn.endswith('.html'):
                result.append(Path(dirpath) / fn)
    return sorted(result)


def main() -> int:
    parser = argparse.ArgumentParser(
        description='Propagate the canonical nav to every page in the repo.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Report what would change without writing any files.',
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Print a decision for every file examined.',
    )
    args = parser.parse_args()

    # Load canonical templates
    if not DESKTOP_TEMPLATE.exists():
        print(f'ERROR: missing {DESKTOP_TEMPLATE}', file=sys.stderr)
        return 1
    if not MOBILE_TEMPLATE.exists():
        print(f'ERROR: missing {MOBILE_TEMPLATE}', file=sys.stderr)
        return 1

    desktop_canonical = DESKTOP_TEMPLATE.read_text().rstrip('\n')
    mobile_canonical  = MOBILE_TEMPLATE.read_text().rstrip('\n')

    log(f'Canonical desktop nav: {len(desktop_canonical)} bytes  (hash {short_hash(desktop_canonical)})')
    log(f'Canonical mobile nav:  {len(mobile_canonical)} bytes  (hash {short_hash(mobile_canonical)})')
    log('')

    # Sanity: every canonical must contain the expected Home link, otherwise
    # someone has broken the template and we refuse to propagate.
    if '<a href="/" class="nav-trigger"' not in desktop_canonical:
        print('ERROR: canonical desktop nav is missing the Home link', file=sys.stderr)
        return 1
    if '<a href="/" class="mobile-trigger"' not in mobile_canonical:
        print('ERROR: canonical mobile nav is missing the Home link', file=sys.stderr)
        return 1

    files = walk_html_files(REPO_ROOT)
    log(f'Scanning {len(files)} HTML files...')
    log('')

    changed_files: list[tuple[Path, bool, bool]] = []
    skipped_no_nav: list[Path] = []
    unchanged: list[Path] = []

    for path in files:
        rel = path.relative_to(REPO_ROOT)
        try:
            html = path.read_text()
        except UnicodeDecodeError as e:
            print(f'ERROR: could not read {rel}: {e}', file=sys.stderr)
            return 1

        has_desktop = find_nav_block(html, 'navbar') is not None
        has_mobile  = find_nav_block(html, 'mobile-drawer') is not None

        if not has_desktop and not has_mobile:
            skipped_no_nav.append(path)
            log(f'  skip (no nav):  {rel}', verbose=args.verbose, only_verbose=True)
            continue

        new_html, d_changed, m_changed = replace_nav_blocks(
            html, desktop_canonical, mobile_canonical
        )

        if not d_changed and not m_changed:
            unchanged.append(path)
            log(f'  unchanged:      {rel}', verbose=args.verbose, only_verbose=True)
            continue

        changed_files.append((path, d_changed, m_changed))
        tags = []
        if d_changed: tags.append('desktop')
        if m_changed: tags.append('mobile')
        log(f'  would change:   {rel}  [{", ".join(tags)}]' if args.dry_run
            else f'  updating:       {rel}  [{", ".join(tags)}]')

        if not args.dry_run:
            path.write_text(new_html)

    log('')
    log(f'Results:')
    log(f'  {len(files)} files scanned')
    log(f'  {len(unchanged)} already match canonical (unchanged)')
    log(f'  {len(changed_files)} {"would be" if args.dry_run else "were"} updated')
    log(f'  {len(skipped_no_nav)} skipped (no nav block present)')

    if args.dry_run:
        if len(changed_files) == 0:
            log('')
            log('Dry run: site is already in sync with canonical. No changes needed.')
            return 0
        log('')
        log(f'Dry run: {len(changed_files)} files would be updated. Re-run without --dry-run to apply.')
        return 2

    if len(changed_files) == 0:
        log('')
        log('Site is already in sync with canonical. No changes needed.')
    else:
        log('')
        log(f'Updated {len(changed_files)} files. Review with `git diff` then commit.')

    return 0


if __name__ == '__main__':
    sys.exit(main())
