# FamilyView

Local-only family tree viewer and editor built with Python FastHTML + SQLite.

## Running

```bash
python3 cli.py setup          # install deps + create static dirs
python3 cli.py start          # start the server (http://localhost:5001)
python3 cli.py start --open   # start + auto-open browser
python3 cli.py close          # stop the running server (SIGTERM on port 5001)
python3 cli.py open           # open browser (server already running)
```

Direct start (bypasses CLI):
```bash
python3 main.py
```

## Stack

| Layer | Tool |
|-------|------|
| Web framework | [python-fasthtml](https://docs.fastht.ml/) 0.12+ |
| Database ORM | fastlite (bundled with fasthtml) |
| Database | SQLite (`familyview.db`, created at runtime) |
| Styling | Tailwind CSS via CDN |
| Dynamic updates | HTMX (bundled with fasthtml) |
| Tree visualization | D3.js v7 via CDN |

## File Map

```
cli.py          — Setup and launch CLI (setup / start / close / open)
main.py         — App entry point + all route handlers
db.py           — Schema DDL, PRAGMA setup, raw query helpers
relations.py    — Relationship inference engine (LCA graph traversal)
components.py   — Reusable FT component functions (HTML generators)
tree.py         — Serializes DB → D3-compatible JSON
static/tree.js  — D3 force-directed graph (fetch, simulate, render)
static/photos/  — Uploaded profile photos (gitignored)
familyview.db   — SQLite database (gitignored, auto-created)
```

## Database Schema

### `persons`
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | auto-increment |
| name | TEXT | required |
| birth_date | TEXT | ISO-8601: "1942-05-23" |
| death_date | TEXT | NULL = living |
| gender | TEXT | "male" / "female" / "other" / "unknown" |
| bio | TEXT | free-form notes |
| photo_path | TEXT | e.g. "static/photos/uuid.jpg" |
| created_at | TEXT | set by SQLite default |
| updated_at | TEXT | updated manually on edit |

### `relationships`
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | auto-increment |
| person_a_id | INTEGER FK | **PARENT** for parent_child type |
| person_b_id | INTEGER FK | **CHILD** for parent_child type |
| rel_type | TEXT | "parent_child" or "spouse" |

**Important:** `PRAGMA foreign_keys = ON` is set on every connection so `ON DELETE CASCADE` works — deleting a person automatically removes all their relationship rows.

## FastHTML Patterns

- **Full pages** return `page_shell(...)` which wraps content in nav + layout.
- **HTMX partials** return bare FT components (FastHTML detects HTMX requests and omits `<html>` wrapper automatically).
- **Routes** use `@rt('/path')` with function names `get`, `post`, or `delete` to match HTTP methods.
- **Redirects** use `RedirectResponse(url, status_code=303)`.

## Relationship Inference (`relations.py`)

The engine computes any named American family relationship using **Lowest Common Ancestor (LCA)** traversal:

1. **Build graph** — `build_graph(db)` returns `(parents_of, children_of)` dicts from the DB.
2. **BFS upward** — `ancestors_with_depth(person_id, parents_of)` returns all ancestors with their depth.
3. **Find LCA** — `find_lca(a_id, b_id, parents_of)` returns `(depth_from_a, depth_from_b, lca_id)`.
4. **Label** — `consanguinity_to_label(depth_a, depth_b, gender)` maps depths to a string.

**Cousin formula:**
- `N`th cousin: `N = min(depth_a, depth_b) - 1`, both depths equal
- `N`th cousin `M` times removed: `M = abs(depth_a - depth_b)`

**Adding a new relationship label:** Edit `consanguinity_to_label()` in `relations.py` and add a new `if` branch for the desired `(depth_a, depth_b)` combination.

## Photo Uploads

POST to `/members/{id}/photo` with `multipart/form-data`, file field named `photo`.

Photos are saved to `static/photos/<uuid>.<ext>` and served by FastHTML's static file handler. The path is stored in `persons.photo_path`.

## Search Behavior

The dashboard search bar (HTMX, 300ms debounce) hits `GET /members?q=...` and searches `name` and `bio` columns via SQL `LIKE`.

The relatives panel on each member's detail page computes all relationships dynamically. The `GET /search?q=...&person_id=...` endpoint filters those computed relatives by the query string (substring match on the label, e.g. "cousin" matches all cousin variants).

## Common Queries

```python
# In db.py
get_parents(db, person_id)   # → list of person dicts
get_children(db, person_id)  # → list of person dicts
get_spouses(db, person_id)   # → list of person dicts
get_siblings(db, person_id)  # → list of person dicts

# In relations.py
get_all_relatives(person_id, db)              # → [{person, label, category}]
search_relatives_by_label(person_id, q, db)  # → [{person, label, category}]
```

## Dev Tips

- `live=True` in `fast_app()` enables hot reload on file save.
- SQLite `familyview.db` is created automatically on first run.
- The tree page uses a D3 force simulation — nodes are draggable.
- Click any tree node to navigate to that person's detail page.
