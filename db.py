from fastlite import database


def setup_db(path: str = "familyview.db"):
    db = database(path)
    db.execute("PRAGMA foreign_keys = ON")
    db.execute("""
        CREATE TABLE IF NOT EXISTS persons (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT    NOT NULL,
            birth_date  TEXT,
            death_date  TEXT,
            gender      TEXT,
            bio         TEXT,
            photo_path  TEXT,
            created_at  TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at  TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
    db.execute("""
        CREATE TABLE IF NOT EXISTS relationships (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            person_a_id INTEGER NOT NULL REFERENCES persons(id) ON DELETE CASCADE,
            person_b_id INTEGER NOT NULL REFERENCES persons(id) ON DELETE CASCADE,
            rel_type    TEXT    NOT NULL,
            UNIQUE(person_a_id, person_b_id, rel_type)
        )
    """)
    db.execute("CREATE INDEX IF NOT EXISTS idx_rel_a ON relationships(person_a_id)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_rel_b ON relationships(person_b_id)")

    persons = db.t.persons
    rels = db.t.relationships
    return db, persons, rels


def get_person(persons, person_id: int) -> dict | None:
    rows = list(persons.rows_where("id = ?", [person_id]))
    return rows[0] if rows else None


def get_parents(db, person_id: int) -> list[dict]:
    rows = list(db.execute(
        "SELECT p.* FROM persons p "
        "JOIN relationships r ON r.person_a_id = p.id "
        "WHERE r.person_b_id = ? AND r.rel_type = 'parent_child'",
        [person_id]
    ))
    cols = [d[1] for d in db.execute("PRAGMA table_info(persons)")]
    return [dict(zip(cols, r)) for r in rows]


def get_children(db, person_id: int) -> list[dict]:
    rows = list(db.execute(
        "SELECT p.* FROM persons p "
        "JOIN relationships r ON r.person_b_id = p.id "
        "WHERE r.person_a_id = ? AND r.rel_type = 'parent_child'",
        [person_id]
    ))
    cols = [d[1] for d in db.execute("PRAGMA table_info(persons)")]
    return [dict(zip(cols, r)) for r in rows]


def get_spouses(db, person_id: int) -> list[dict]:
    rows = list(db.execute(
        "SELECT p.* FROM persons p "
        "JOIN relationships r ON (r.person_a_id = p.id OR r.person_b_id = p.id) "
        "WHERE (r.person_a_id = ? OR r.person_b_id = ?) "
        "  AND r.rel_type = 'spouse' AND p.id != ?",
        [person_id, person_id, person_id]
    ))
    cols = [d[1] for d in db.execute("PRAGMA table_info(persons)")]
    return [dict(zip(cols, r)) for r in rows]


def get_siblings(db, person_id: int) -> list[dict]:
    parents = get_parents(db, person_id)
    if not parents:
        return []
    parent_ids = [p["id"] for p in parents]
    placeholders = ",".join("?" * len(parent_ids))
    rows = list(db.execute(
        f"SELECT DISTINCT p.* FROM persons p "
        f"JOIN relationships r ON r.person_b_id = p.id "
        f"WHERE r.person_a_id IN ({placeholders}) AND r.rel_type = 'parent_child' AND p.id != ?",
        parent_ids + [person_id]
    ))
    cols = [d[1] for d in db.execute("PRAGMA table_info(persons)")]
    return [dict(zip(cols, r)) for r in rows]


def search_persons(persons, q: str) -> list[dict]:
    if not q:
        return list(persons.rows_where(order_by="name"))
    return list(persons.rows_where(
        "name LIKE ? OR bio LIKE ?",
        [f"%{q}%", f"%{q}%"],
        order_by="name"
    ))


def get_all_relationships(db, person_id: int) -> dict:
    return {
        "parents": get_parents(db, person_id),
        "children": get_children(db, person_id),
        "spouses": get_spouses(db, person_id),
        "siblings": get_siblings(db, person_id),
    }


def get_relationship_row(rels, rel_id: int) -> dict | None:
    rows = list(rels.rows_where("id = ?", [rel_id]))
    return rows[0] if rows else None
