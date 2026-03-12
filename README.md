# FamilyView

A local family registry and tree viewer built with Python, FastHTML, and SQLite. Store personal information for family members, manage relationships, and explore your family tree interactively — all from a local web app.

## Features

- **Member registry** — store name, birth/death dates, gender, biography, and profile photo for each person
- **Relationship tracking** — link parents, children, and spouses/partners
- **Computed relationships** — automatically derives extended family labels (uncle, aunt, nephew, niece, 1st/2nd/3rd cousin, once/twice removed, great-grandparent, etc.)
- **Relationship search** — search by name or relationship label (e.g. "first cousin", "uncle", "cousin once removed")
- **Interactive family tree** — force-directed D3.js graph with zoom, pan, and drag; click any node to view that person's detail page

## Setup & Usage

```bash
python3 cli.py setup   # install dependencies
python3 cli.py start   # start the server → http://localhost:5001
python3 cli.py start --open  # start and open browser automatically
python3 cli.py close   # stop the server
python3 cli.py open    # open the browser (server already running)
```

## Usage

1. **Add members** — click "+ Add Member" in the nav bar
2. **Link relationships** — open a member's detail page and use the Relationships panel to add parents, children, or spouses
3. **View relatives** — the "All Relatives" section on each detail page lists every computed relationship
4. **Search** — use the search bar to find members by name or biography text
5. **Family tree** — click "Family Tree" in the nav to view the interactive D3 graph

## Stack

- [FastHTML](https://docs.fastht.ml/) — Python web framework with HTMX built in
- SQLite — local database (`familyview.db`, created automatically on first run)
- [Tailwind CSS](https://tailwindcss.com/) — styling via CDN
- [D3.js v7](https://d3js.org/) — family tree visualization via CDN

## Project Structure

```
cli.py          — setup and launch CLI
main.py         — routes and app entry point
db.py           — database schema and query helpers
relations.py    — relationship inference engine (LCA graph traversal)
components.py   — reusable HTML components
tree.py         — serializes DB data to D3-compatible JSON
static/tree.js  — D3 force-directed graph
static/photos/  — uploaded profile photos (not tracked by git)
familyview.db   — SQLite database (not tracked by git)
```

## Data & Privacy

All data is stored locally in `familyview.db`. Nothing is sent to any server. Photos are stored in `static/photos/`. Both are excluded from git by `.gitignore`.
