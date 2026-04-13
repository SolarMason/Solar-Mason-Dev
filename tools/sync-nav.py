#!/usr/bin/env python3
"""
sync-nav.py — Propagate the canonical Solar Mason site chrome to every page.

This is the single source of truth for the site-wide navigation AND footer.
When the nav or footer needs to change (add a menu item, reorder, rename,
restructure, update contact info, add footer links, etc.), edit the
corresponding template under _templates/, then run:

    python3 tools/sync-nav.py

and every HTML page with the standard site chrome will have its nav AND
footer blocks replaced with the canonical versions. The script is
idempotent — running it when nothing has changed is a no-op that exits
cleanly.

The name of the script is historical — originally this only handled
navigation, but it was extended to also cover the footer since the two
have identical drift problems and identical solutions. Future extensions
(shared <head> sections, global modals, etc.) can use the same pattern.

WHAT IT DOES

  For every .html file under the repo root (excluding .git, node_modules,
  _templates, tools, datasheets):

    1. Locate the existing <nav class="navbar" id="navbar"> ... </nav> block
    2. Locate the existing <nav class="mobile-drawer" id="mobile-drawer"> ... </nav> block
    3. Locate the existing <footer class="footer"> ... </footer> block
    4. For each block, if it differs from the canonical, replace it
    5. If a block is missing from a file, skip that block (assumed to be
       a standalone page with partial chrome, like datasheets/index.html
       which has no nav or footer)

  It does NOT touch any other part of the page — page body, <head>,
  scripts, styles. Only the three chrome blocks are within its scope.

THREE TEMPLATE FILES

  _templates/_nav-desktop.html  — the desktop <nav class="navbar"> block
  _templates/_nav-mobile.html   — the mobile <nav class="mobile-drawer"> block
  _templates/_footer.html       — the <footer class="footer"> block

ADDING A NEW PAGE

  When creating a new page from scratch, copy _templates/page-template.html
  as your starting point. It already has the canonical nav + footer baked
  in. After copying, run this script to pick up any nav/footer changes
  that have happened since the template was last updated.

IDEMPOTENCY

  The script compares each file's current block contents against the
  canonical byte-for-byte. If they match, the file is skipped and the
  diff stays clean. Running the script multiple times in a row will only
  produce a single non-empty run.

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
  no build step. Chrome sync is a LOCAL developer workflow:

      edit _templates/_nav-desktop.html   (or _nav-mobile, or _footer)
      python3 tools/sync-nav.py
      git add -A
      git commit -m "Nav: ..."
      git push

  See tools/README.md for details including optional pre-commit hook
  installation that auto-runs this script in --dry-run mode to block
  commits that would leave the canonical and pages out of sync.
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
FOOTER_TEMPLATE  = TEMPLATES_DIR / '_footer.html'

# Directories to skip entirely when walking the repo.
EXCLUDED_DIRS = {'.git', 'node_modules', '_templates', 'tools', 'datasheets'}
# Note: datasheets/ is excluded because datasheets/index.html is a standalone
# minimal equipment directory with no site nav AND no footer. If you add
# other pages under /datasheets/ in the future that DO need the full chrome,
# remove this exclusion and the script will handle them correctly.


def log(msg: str, *, verbose: bool = False, only_verbose: bool = False) -> None:
    if only_verbose and not verbose:
        return
    print(msg)


def short_hash(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()[:10]


def find_block_by_class(html: str, tag: str, class_name: str) -> tuple[int, int] | None:
    """
    Find the byte span of a <tag class="class_name" ...>...</tag> block.

    Generic helper for locating site-chrome regions. Walks the HTML looking
    for the opening tag, then scans forward counting <tag> and </tag>
    occurrences to find the matching close. Returns (start, end) byte
    offsets of the full block including the outer tags, or None if the
    block is not present in this file.

    Used by both nav sync (<nav class="navbar">, <nav class="mobile-drawer">)
    and footer sync (<footer class="footer">).
    """
    m = re.search(rf'<{re.escape(tag)} class="{re.escape(class_name)}"', html)
    if not m:
        return None

    open_pattern  = f'<{tag}'
    close_pattern = f'</{tag}>'
    pos = m.end()
    depth = 1
    while depth > 0:
        nxt_open  = html.find(open_pattern, pos)
        nxt_close = html.find(close_pattern, pos)
        if nxt_close == -1:
            # Unbalanced tag — give up
            return None
        if nxt_open != -1 and nxt_open < nxt_close:
            depth += 1
            pos = nxt_open + len(open_pattern)
        else:
            depth -= 1
            pos = nxt_close + len(close_pattern)
    return (m.start(), pos)


def find_nav_block(html: str, nav_class: str) -> tuple[int, int] | None:
    """Backward-compatible wrapper for find_block_by_class for <nav> blocks."""
    return find_block_by_class(html, 'nav', nav_class)


def find_footer_block(html: str) -> tuple[int, int] | None:
    """Locate the <footer class="footer"> block, if present."""
    return find_block_by_class(html, 'footer', 'footer')


def replace_chrome_blocks(
    html: str,
    desktop_canonical: str,
    mobile_canonical: str,
    footer_canonical: str,
) -> tuple[str, bool, bool, bool]:
    """
    Replace the desktop nav, mobile drawer, and footer blocks in an HTML
    string with their canonical versions. Returns
    (new_html, desktop_changed, mobile_changed, footer_changed).

    If a file is missing a block entirely, that block is left alone — we
    do not INJECT chrome into pages that don't already have it. That
    would be a much more invasive change and would require knowing
    where to insert the block, which varies by page layout. Pages
    without certain chrome blocks are assumed to be intentionally
    partial (like datasheets/index.html which has none of them).

    Replacement order matters: we replace FOOTER first, then mobile
    drawer, then desktop nav. Footer appears LAST in the document,
    mobile drawer appears in the middle, desktop nav appears first.
    Replacing later-occurring blocks first means earlier-block byte
    offsets don't shift, so we only need to re-resolve the spans once
    per step rather than once per replacement.
    """
    desktop_changed = False
    mobile_changed  = False
    footer_changed  = False

    # 1. Footer — appears last in document source, replace first
    footer_span = find_footer_block(html)
    if footer_span is not None:
        existing_footer = html[footer_span[0]:footer_span[1]]
        if existing_footer != footer_canonical:
            html = html[:footer_span[0]] + footer_canonical + html[footer_span[1]:]
            footer_changed = True

    # 2. Mobile drawer — appears after desktop navbar
    mobile_span = find_nav_block(html, 'mobile-drawer')
    if mobile_span is not None:
        existing_mobile = html[mobile_span[0]:mobile_span[1]]
        if existing_mobile != mobile_canonical:
            html = html[:mobile_span[0]] + mobile_canonical + html[mobile_span[1]:]
            mobile_changed = True

    # 3. Desktop navbar — appears first, replace last (its span is
    #    unaffected by the previous two replacements since it comes first)
    desktop_span = find_nav_block(html, 'navbar')
    if desktop_span is not None:
        existing_desktop = html[desktop_span[0]:desktop_span[1]]
        if existing_desktop != desktop_canonical:
            html = html[:desktop_span[0]] + desktop_canonical + html[desktop_span[1]:]
            desktop_changed = True

    return (html, desktop_changed, mobile_changed, footer_changed)


def walk_html_files(root: Path) -> list[Path]:
    """Yield every .html file under root, skipping EXCLUDED_DIRS."""
    result = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDED_DIRS and not d.startswith('.')]
        for fn in filenames:
            if fn.endswith('.html'):
                result.append(Path(dirpath) / fn)
    return sorted(result)


def main() -> int:
    parser = argparse.ArgumentParser(
        description='Propagate the canonical site chrome (nav + footer) to every page.',
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
    for tpl in (DESKTOP_TEMPLATE, MOBILE_TEMPLATE, FOOTER_TEMPLATE):
        if not tpl.exists():
            print(f'ERROR: missing {tpl}', file=sys.stderr)
            return 1

    desktop_canonical = DESKTOP_TEMPLATE.read_text().rstrip('\n')
    mobile_canonical  = MOBILE_TEMPLATE.read_text().rstrip('\n')
    footer_canonical  = FOOTER_TEMPLATE.read_text().rstrip('\n')

    log(f'Canonical desktop nav: {len(desktop_canonical):>6} bytes  (hash {short_hash(desktop_canonical)})')
    log(f'Canonical mobile nav:  {len(mobile_canonical):>6} bytes  (hash {short_hash(mobile_canonical)})')
    log(f'Canonical footer:      {len(footer_canonical):>6} bytes  (hash {short_hash(footer_canonical)})')
    log('')

    # Sanity: each canonical must contain its expected marker text,
    # otherwise someone has broken the template and we refuse to propagate.
    if '<a href="/" class="nav-trigger"' not in desktop_canonical:
        print('ERROR: canonical desktop nav is missing the Home link', file=sys.stderr)
        return 1
    if '<a href="/" class="mobile-trigger"' not in mobile_canonical:
        print('ERROR: canonical mobile nav is missing the Home link', file=sys.stderr)
        return 1
    if 'Solar Mason' not in footer_canonical:
        print('ERROR: canonical footer is missing the Solar Mason brand marker', file=sys.stderr)
        return 1
    if 'fc-head' not in footer_canonical:
        print('ERROR: canonical footer is missing expected fc-head structure', file=sys.stderr)
        return 1

    files = walk_html_files(REPO_ROOT)
    log(f'Scanning {len(files)} HTML files...')
    log('')

    # Per-file change tracking: (path, d_changed, m_changed, f_changed)
    changed_files: list[tuple[Path, bool, bool, bool]] = []
    skipped_no_chrome: list[Path] = []
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
        has_footer  = find_footer_block(html) is not None

        if not (has_desktop or has_mobile or has_footer):
            skipped_no_chrome.append(path)
            log(f'  skip (no chrome):  {rel}', verbose=args.verbose, only_verbose=True)
            continue

        new_html, d_changed, m_changed, f_changed = replace_chrome_blocks(
            html, desktop_canonical, mobile_canonical, footer_canonical
        )

        if not (d_changed or m_changed or f_changed):
            unchanged.append(path)
            log(f'  unchanged:         {rel}', verbose=args.verbose, only_verbose=True)
            continue

        changed_files.append((path, d_changed, m_changed, f_changed))
        tags = []
        if d_changed: tags.append('desktop')
        if m_changed: tags.append('mobile')
        if f_changed: tags.append('footer')
        action_prefix = '  would change:   ' if args.dry_run else '  updating:       '
        log(f'{action_prefix}{rel}  [{", ".join(tags)}]')

        if not args.dry_run:
            path.write_text(new_html)

    # Tally which block types changed
    n_desktop = sum(1 for _, d, _, _ in changed_files if d)
    n_mobile  = sum(1 for _, _, m, _ in changed_files if m)
    n_footer  = sum(1 for _, _, _, f in changed_files if f)

    log('')
    log(f'Results:')
    log(f'  {len(files)} files scanned')
    log(f'  {len(unchanged)} already match canonical (unchanged)')
    log(f'  {len(changed_files)} {"would be" if args.dry_run else "were"} updated')
    log(f'    desktop nav: {n_desktop}')
    log(f'    mobile nav:  {n_mobile}')
    log(f'    footer:      {n_footer}')
    log(f'  {len(skipped_no_chrome)} skipped (no chrome blocks present)')

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
