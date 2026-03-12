"""
Relationship inference engine.

Computes named relationships (uncle, first cousin, etc.) between any two
people using Lowest Common Ancestor (LCA) graph traversal on the parent-child
edge set stored in SQLite.

Convention: in the `relationships` table, for rel_type='parent_child',
  person_a_id = PARENT, person_b_id = CHILD.
"""

from collections import deque


# ---------------------------------------------------------------------------
# Graph construction
# ---------------------------------------------------------------------------

def build_graph(db) -> tuple[dict, dict]:
    """
    Returns (parents_of, children_of) where each is a dict mapping
    person_id -> set of related person_ids.
    """
    parents_of: dict[int, set] = {}
    children_of: dict[int, set] = {}

    for row in db.execute(
        "SELECT person_a_id, person_b_id FROM relationships WHERE rel_type = 'parent_child'"
    ):
        parent_id, child_id = row[0], row[1]
        parents_of.setdefault(child_id, set()).add(parent_id)
        children_of.setdefault(parent_id, set()).add(child_id)

    return parents_of, children_of


def get_all_person_ids(db) -> list[int]:
    return [r[0] for r in db.execute("SELECT id FROM persons")]


# ---------------------------------------------------------------------------
# Ancestor BFS
# ---------------------------------------------------------------------------

def ancestors_with_depth(person_id: int, parents_of: dict) -> dict[int, int]:
    """
    BFS upward from person_id following parent edges.
    Returns {ancestor_id: depth} with depth=0 meaning self.
    """
    visited: dict[int, int] = {person_id: 0}
    queue = deque([(person_id, 0)])
    while queue:
        current, depth = queue.popleft()
        for parent in parents_of.get(current, set()):
            if parent not in visited:
                visited[parent] = depth + 1
                queue.append((parent, depth + 1))
    return visited


# ---------------------------------------------------------------------------
# LCA
# ---------------------------------------------------------------------------

def find_lca(
    a_id: int, b_id: int, parents_of: dict
) -> tuple[int, int, int] | None:
    """
    Returns (depth_from_a, depth_from_b, lca_id) for the closest common
    ancestor, or None if the two people share no ancestor.
    """
    ancestors_a = ancestors_with_depth(a_id, parents_of)
    ancestors_b = ancestors_with_depth(b_id, parents_of)

    common = set(ancestors_a) & set(ancestors_b)
    if not common:
        return None

    # Pick the LCA with lowest combined depth
    best = min(common, key=lambda anc: ancestors_a[anc] + ancestors_b[anc])
    return ancestors_a[best], ancestors_b[best], best


# ---------------------------------------------------------------------------
# Relationship label mapping
# ---------------------------------------------------------------------------

ORDINALS = ["", "first", "second", "third", "fourth", "fifth",
            "sixth", "seventh", "eighth", "ninth", "tenth"]

REMOVES = ["", "once", "twice", "three times", "four times", "five times"]


def _ordinal(n: int) -> str:
    if n < len(ORDINALS):
        return ORDINALS[n]
    return f"{n}th"


def _removed(m: int) -> str:
    if m < len(REMOVES):
        return REMOVES[m]
    return f"{m} times"


def consanguinity_to_label(
    depth_a: int, depth_b: int, target_gender: str | None
) -> str:
    """
    Maps (depth from A to LCA, depth from B to LCA) to a relationship label
    describing who B is relative to A.

    depth_a=0 means A IS the LCA (B descends from A).
    depth_b=0 means B IS the LCA (A descends from B).
    """
    g = (target_gender or "unknown").lower()
    is_male = g == "male"
    is_female = g == "female"

    # --- Linear: one person is direct ancestor/descendant of the other ---
    if depth_a == 0:
        # B descends from A; B is A's descendant
        if depth_b == 1:
            return "child"
        if depth_b == 2:
            return "grandchild"
        greats = "great-" * (depth_b - 2)
        return f"{greats}grandchild"

    if depth_b == 0:
        # A descends from B; B is A's ancestor
        if depth_a == 1:
            if is_male:
                return "father"
            if is_female:
                return "mother"
            return "parent"
        if depth_a == 2:
            if is_male:
                return "grandfather"
            if is_female:
                return "grandmother"
            return "grandparent"
        greats = "great-" * (depth_a - 2)
        if is_male:
            return f"{greats}grandfather"
        if is_female:
            return f"{greats}grandmother"
        return f"{greats}grandparent"

    # --- Sibling ---
    if depth_a == 1 and depth_b == 1:
        if is_male:
            return "brother"
        if is_female:
            return "sister"
        return "sibling"

    # --- Uncle/Aunt (A's parent's sibling = depth_a=2, depth_b=1) ---
    if depth_a == 2 and depth_b == 1:
        if is_male:
            return "uncle"
        if is_female:
            return "aunt"
        return "uncle/aunt"

    # --- Nephew/Niece (sibling's child = depth_a=1, depth_b=2) ---
    if depth_a == 1 and depth_b == 2:
        if is_male:
            return "nephew"
        if is_female:
            return "niece"
        return "nephew/niece"

    # --- Great-uncle/aunt (depth_a=3, depth_b=1) ---
    if depth_b == 1 and depth_a >= 3:
        greats = "great-" * (depth_a - 2)
        if is_male:
            return f"{greats}uncle"
        if is_female:
            return f"{greats}aunt"
        return f"{greats}uncle/aunt"

    # --- Grand-nephew/niece (depth_a=1, depth_b=3+) ---
    if depth_a == 1 and depth_b >= 3:
        greats = "great-" * (depth_b - 2)
        if is_male:
            return f"{greats}nephew"
        if is_female:
            return f"{greats}niece"
        return f"{greats}nephew/niece"

    # --- Cousins ---
    # N = min(depth_a, depth_b) - 1
    # M = abs(depth_a - depth_b) (times removed)
    n = min(depth_a, depth_b) - 1
    m = abs(depth_a - depth_b)

    if n < 1:
        # Shouldn't happen if above cases are exhaustive, but fallback
        return "relative"

    nth = _ordinal(n)
    if m == 0:
        return f"{nth} cousin"
    removed = _removed(m)
    return f"{nth} cousin {removed} removed"


# ---------------------------------------------------------------------------
# High-level API
# ---------------------------------------------------------------------------

def _person_cols(db):
    return [d[1] for d in db.execute("PRAGMA table_info(persons)")]


def _row_to_dict(row, cols):
    return dict(zip(cols, row))


def get_all_relatives(person_id: int, db) -> list[dict]:
    """
    Returns a list of dicts:
      {"person": {...}, "label": "first cousin", "category": "cousins"}

    Includes spouses (looked up directly from relationships table).
    Excludes self.
    """
    parents_of, _ = build_graph(db)
    cols = _person_cols(db)
    all_person_rows = list(db.execute("SELECT * FROM persons WHERE id != ?", [person_id]))
    all_persons = [_row_to_dict(r, cols) for r in all_person_rows]

    # Get spouses via direct DB lookup (not graph traversal)
    spouse_ids = set(
        r[0] for r in db.execute(
            "SELECT CASE WHEN person_a_id = ? THEN person_b_id ELSE person_a_id END "
            "FROM relationships "
            "WHERE (person_a_id = ? OR person_b_id = ?) AND rel_type = 'spouse'",
            [person_id, person_id, person_id]
        )
    )

    result = []

    for person in all_persons:
        pid = person["id"]

        if pid in spouse_ids:
            result.append({
                "person": person,
                "label": "spouse",
                "category": "direct",
            })
            continue

        lca_result = find_lca(person_id, pid, parents_of)
        if lca_result is None:
            continue

        depth_a, depth_b, _ = lca_result
        label = consanguinity_to_label(depth_a, depth_b, person.get("gender"))

        # Categorize
        if depth_a <= 1 or depth_b <= 1:
            category = "direct"
        elif depth_a <= 2 and depth_b <= 2:
            category = "extended"
        elif "cousin" in label:
            category = "cousins"
        else:
            category = "extended"

        result.append({
            "person": person,
            "label": label,
            "category": category,
        })

    return result


def search_relatives_by_label(person_id: int, query: str, db) -> list[dict]:
    """
    Returns all relatives of person_id whose relationship label fuzzy-matches
    the query string. Case-insensitive substring match.

    e.g. query="cousin" matches "first cousin", "second cousin once removed", etc.
    """
    q = query.strip().lower()
    return [
        r for r in get_all_relatives(person_id, db)
        if q in r["label"].lower()
    ]
