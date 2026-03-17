#!/usr/bin/env python3
"""
Auto-sync documentation with codebase structure.

Extracts API endpoints, models, pages, and components from the actual code
and regenerates the corresponding sections in README.md and CLAUDE.md.

Sections are delimited by marker comments:
  <!-- AUTO:SECTION_NAME:START -->
  ...auto-generated content...
  <!-- AUTO:SECTION_NAME:END -->

Run: python scripts/sync-docs.py
CI:  runs on every PR via .github/workflows/sync-docs.yml
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"


# ---------------------------------------------------------------------------
# Extraction helpers
# ---------------------------------------------------------------------------

def extract_route_prefix_map() -> dict[str, str]:
    """Parse main.py to build {module_name: prefix} map."""
    main_py = BACKEND / "app" / "main.py"
    text = main_py.read_text()
    mapping = {}
    for m in re.finditer(
        r'app\.include_router\(\s*(\w+)\.router\s*,\s*prefix="([^"]+)"', text
    ):
        mapping[m.group(1)] = m.group(2)

    # Top-level routes defined directly on `app` — extract with docstrings
    app_pattern = re.compile(
        r'@app\.(get|post|put|patch|delete)\("([^"]+)".*?\)\s*\n'
        r'(?:async\s+)?def\s+\w+\(.*?\).*?:\s*\n'
        r'(?:\s*"""(.*?)""")?',
        re.DOTALL,
    )
    for m in app_pattern.finditer(text):
        mapping.setdefault("__app__", [])
        method = m.group(1).upper()
        path = m.group(2)
        docstring = m.group(3)
        desc = docstring.strip().split("\n")[0] if docstring else path.strip("/").capitalize() or "Root"
        mapping["__app__"].append((method, path, desc))
    return mapping


def extract_endpoints() -> dict[str, list[tuple[str, str, str]]]:
    """Return {tag: [(METHOD, full_path, description), ...]}."""
    prefix_map = extract_route_prefix_map()
    api_dir = BACKEND / "app" / "api"
    tag_order = [
        "auth", "users", "leagues", "competitions", "invite",
        "picks", "leaderboards", "admin", "bug_reports", "health", "ws",
    ]
    tag_display = {
        "auth": "Authentication",
        "users": "Users",
        "leagues": "Leagues",
        "competitions": "Competitions",
        "invite": "Invites",
        "picks": "Picks",
        "leaderboards": "Leaderboards",
        "admin": "Admin",
        "bug_reports": "Bug Reports",
        "health": "Health & Monitoring",
        "ws": "WebSocket",
    }

    endpoints: dict[str, list[tuple[str, str, str]]] = {}
    for tag in tag_order:
        endpoints[tag_display.get(tag, tag)] = []

    for py_file in sorted(api_dir.glob("*.py")):
        if py_file.name == "__init__.py":
            continue
        module = py_file.stem
        prefix = prefix_map.get(module, "")
        display_tag = tag_display.get(module, module)
        text = py_file.read_text()

        # Match decorator + function def + docstring
        pattern = re.compile(
            r'@router\.(get|post|put|patch|delete|websocket)\("([^"]*)".*?\)\s*\n'
            r'(?:@[^\n]*\n)*'  # skip additional decorators
            r'(?:async\s+)?def\s+(\w+)\(.*?\).*?:\s*\n'
            r'(?:\s*"""(.*?)""")?',
            re.DOTALL,
        )
        for m in pattern.finditer(text):
            method = m.group(1).upper()
            path = m.group(2)
            func_name = m.group(3)
            docstring = m.group(4)

            if method == "WEBSOCKET":
                method = "WS"

            full_path = prefix + path
            # Use first line of docstring, or generate from function name
            if docstring:
                desc = docstring.strip().split("\n")[0].strip().rstrip(".")
            else:
                desc = func_name.replace("_", " ").capitalize()

            if display_tag not in endpoints:
                endpoints[display_tag] = []
            endpoints[display_tag].append((method, full_path, desc))

    # Add top-level app routes
    app_routes = prefix_map.get("__app__", [])
    if app_routes:
        if "Health & Monitoring" not in endpoints:
            endpoints["Health & Monitoring"] = []
        for method, path, desc in app_routes:
            endpoints["Health & Monitoring"].insert(0, (method, path, desc))

    # Remove empty sections
    return {k: v for k, v in endpoints.items() if v}


def extract_models() -> list[tuple[str, str]]:
    """Return [(ClassName, description), ...] from model files."""
    models_dir = BACKEND / "app" / "models"
    # Map of class name -> short description (derived from class or docstring)
    descriptions = {
        "User": "Authentication and user management",
        "Competition": "Represents a competition (Daily Picks or Fixed Teams)",
        "League": "Sports leagues (NFL, NBA, etc.)",
        "Team": "Teams within leagues",
        "Game": "Individual games/matches",
        "Pick": "Daily picks for games",
        "FixedTeamSelection": "Pre-season team/golfer selections",
        "Golfer": "PGA golfers within a league",
        "BugReport": "User-submitted bug reports",
        "Participant": "User participation in competitions",
        "JoinRequest": "Join requests for private competitions",
        "InviteLink": "Shareable invite links for competitions",
        "AuditLog": "Immutable audit trail of admin actions",
    }
    results = []
    for py_file in sorted(models_dir.glob("*.py")):
        if py_file.name == "__init__.py":
            continue
        text = py_file.read_text()
        for m in re.finditer(r"class (\w+)\(Base\):", text):
            name = m.group(1)
            # Try to extract docstring
            after = text[m.end():]
            doc_match = re.match(r'\s*"""(.*?)"""', after, re.DOTALL)
            if doc_match:
                desc = doc_match.group(1).strip().split("\n")[0]
            elif name in descriptions:
                desc = descriptions[name]
            else:
                desc = name.replace("_", " ")
            results.append((name, desc))
    return results


def extract_frontend_files(subdir: str) -> list[str]:
    """Return sorted list of .tsx component/page names (excluding tests)."""
    d = FRONTEND / "src" / subdir
    if not d.exists():
        return []
    return sorted(
        f.stem
        for f in d.glob("*.tsx")
        if not f.name.endswith(".test.tsx")
    )


def extract_service_files() -> list[str]:
    """Return sorted list of backend service module names."""
    d = BACKEND / "app" / "services"
    if not d.exists():
        return []
    return sorted(
        f.stem
        for f in d.glob("*.py")
        if f.name != "__init__.py"
    )


def extract_api_modules() -> list[str]:
    """Return sorted list of backend API route module names."""
    d = BACKEND / "app" / "api"
    if not d.exists():
        return []
    return sorted(
        f.stem
        for f in d.glob("*.py")
        if f.name != "__init__.py"
    )


# ---------------------------------------------------------------------------
# Markdown generation
# ---------------------------------------------------------------------------

def generate_endpoints_md() -> str:
    """Generate the API Endpoints markdown section."""
    sections = extract_endpoints()
    lines = []
    for tag, eps in sections.items():
        lines.append(f"### {tag}")
        for method, path, desc in eps:
            lines.append(f"- `{method} {path}` - {desc}")
        lines.append("")
    lines.append(
        "Full API documentation available at `/docs` when the backend is running."
    )
    return "\n".join(lines)


def generate_models_md() -> str:
    """Generate the Database Schema markdown section."""
    models = extract_models()
    lines = ["Key models:"]
    for name, desc in models:
        lines.append(f"- **{name}**: {desc}")
    return "\n".join(lines)


def generate_claude_pages() -> str:
    """Generate the pages line for CLAUDE.md project layout."""
    pages = extract_frontend_files("pages")
    return ", ".join(pages)


def generate_claude_components() -> str:
    """Generate the components line for CLAUDE.md project layout."""
    return ", ".join(extract_frontend_files("components"))


def generate_claude_api_modules() -> str:
    """Generate the api modules line for CLAUDE.md project layout."""
    return ", ".join(extract_api_modules())


# ---------------------------------------------------------------------------
# File updating
# ---------------------------------------------------------------------------

def replace_section(text: str, section_name: str, new_content: str) -> str:
    """Replace content between AUTO markers."""
    pattern = re.compile(
        rf"(<!-- AUTO:{section_name}:START -->\n).*?(<!-- AUTO:{section_name}:END -->)",
        re.DOTALL,
    )
    replacement = rf"\g<1>{new_content}\n\2"
    new_text, count = pattern.subn(replacement, text)
    if count == 0:
        print(f"  WARNING: marker AUTO:{section_name} not found", file=sys.stderr)
    return new_text


def sync_readme():
    """Update README.md auto-generated sections."""
    readme = ROOT / "README.md"
    text = readme.read_text()
    original = text

    text = replace_section(text, "ENDPOINTS", generate_endpoints_md())
    text = replace_section(text, "MODELS", generate_models_md())

    if text != original:
        readme.write_text(text)
        print("  README.md updated")
    else:
        print("  README.md already up to date")


def sync_claude_md():
    """Update CLAUDE.md auto-generated sections."""
    claude_md = ROOT / "CLAUDE.md"
    text = claude_md.read_text()
    original = text

    pages = generate_claude_pages()
    components = generate_claude_components()
    api_mods = generate_claude_api_modules()

    text = replace_section(
        text, "PAGES",
        f"    pages/        # Route components ({pages})",
    )
    text = replace_section(
        text, "COMPONENTS",
        f"    components/   # {components}",
    )
    text = replace_section(
        text, "API_MODULES",
        f"    api/          # Route handlers ({api_mods})",
    )

    if text != original:
        claude_md.write_text(text)
        print("  CLAUDE.md updated")
    else:
        print("  CLAUDE.md already up to date")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("Syncing documentation with codebase...")
    sync_readme()
    sync_claude_md()
    print("Done.")


if __name__ == "__main__":
    main()
