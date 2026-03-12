"""Serialize DB data to JSON formats for the two tree views."""


def _acyclic_edges(raw_edges: list[tuple]) -> list[tuple]:
    """
    Filter parent-child edges to remove any that would create a cycle.
    Uses DFS reachability: skip edge (parent→child) if child can already
    reach parent through previously accepted edges.
    """
    children_of: dict = {}

    def reachable(start, target, visited):
        if start == target:
            return True
        if start in visited:
            return False
        visited.add(start)
        return any(reachable(c, target, visited) for c in children_of.get(start, []))

    good = []
    for (parent_id, child_id) in raw_edges:
        if not reachable(child_id, parent_id, set()):
            good.append((parent_id, child_id))
            children_of.setdefault(parent_id, []).append(child_id)
        # else: silently skip — would create a cycle
    return good


def build_family_chart_data(db) -> list:
    """
    Convert DB data to the family-chart library format:
    [{id, data: {first name, birthday, gender, avatar}, rels: {spouses, children, parents}}]
    IDs must be strings. Circular parent-child edges are silently dropped.
    """
    cols = [d[1] for d in db.execute("PRAGMA table_info(persons)")]
    persons = [dict(zip(cols, r)) for r in db.execute("SELECT * FROM persons")]

    children_of = {p["id"]: [] for p in persons}
    parents_of  = {p["id"]: [] for p in persons}
    spouses_of  = {p["id"]: [] for p in persons}

    # Collect raw parent-child edges then strip cycles
    raw_pc = []
    for row in db.execute("SELECT person_a_id, person_b_id, rel_type FROM relationships"):
        a_id, b_id, rel_type = row[0], row[1], row[2]
        if rel_type == "parent_child":
            raw_pc.append((a_id, b_id))
        elif rel_type == "spouse":
            if a_id in spouses_of and b_id not in spouses_of[a_id]:
                spouses_of[a_id].append(b_id)
            if b_id in spouses_of and a_id not in spouses_of[b_id]:
                spouses_of[b_id].append(a_id)

    for (parent_id, child_id) in _acyclic_edges(raw_pc):
        if parent_id in children_of:
            children_of[parent_id].append(child_id)
        if child_id in parents_of:
            parents_of[child_id].append(parent_id)

    gender_map = {"male": "M", "female": "F"}

    return [
        {
            "id": str(p["id"]),
            "data": {
                "first name": p["name"],
                "last name": "",
                "birthday": p.get("birth_date") or "",
                "death year": p.get("death_date") or "",
                "gender": gender_map.get(p.get("gender") or "", ""),
                "avatar": ("/" + p["photo_path"]) if p.get("photo_path") else "",
            },
            "rels": {
                "spouses":  [str(i) for i in spouses_of.get(p["id"], [])],
                "children": [str(i) for i in children_of.get(p["id"], [])],
                "parents":  [str(i) for i in parents_of.get(p["id"], [])],
            },
        }
        for p in persons
    ]


def build_tree_json(db) -> dict:
    cols = [d[1] for d in db.execute("PRAGMA table_info(persons)")]
    persons = [dict(zip(cols, r)) for r in db.execute("SELECT * FROM persons")]

    rel_cols = [d[1] for d in db.execute("PRAGMA table_info(relationships)")]
    rels = [dict(zip(rel_cols, r)) for r in db.execute("SELECT * FROM relationships")]

    nodes = [
        {
            "id": p["id"],
            "name": p["name"],
            "gender": p["gender"] or "unknown",
            "birth_date": p["birth_date"] or "",
            "death_date": p["death_date"] or "",
            "photo_path": p["photo_path"] or "",
        }
        for p in persons
    ]

    links = [
        {
            "source": r["person_a_id"],
            "target": r["person_b_id"],
            "type": r["rel_type"],
        }
        for r in rels
    ]

    return {"nodes": nodes, "links": links}
