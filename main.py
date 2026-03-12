import json
import os
import uuid

from fasthtml.common import *
from starlette.datastructures import UploadFile

import db as db_module
from components import (
    member_list, member_card, person_form, photo_widget,
    relationship_widget, relatives_panel, page_shell, nav_bar
)
from tree import build_tree_json, build_family_chart_data

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

tailwind = Script(src="https://cdn.tailwindcss.com")
app, rt = fast_app(
    hdrs=(tailwind,),
    pico=False,
    live=True,
    static_path="static",
)

database, persons_tbl, rels_tbl = db_module.setup_db("familyview.db")
os.makedirs("static/photos", exist_ok=True)


def _count():
    return list(database.execute("SELECT COUNT(*) FROM persons"))[0][0]


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@rt("/")
def get(q: str = ""):
    persons = db_module.search_persons(persons_tbl, q)
    count = _count()
    return page_shell(
        Div(
            Div(
                H1("Family Registry", cls="text-3xl font-bold text-gray-900"),
                P("Your family, organized.", cls="text-gray-500 mt-1"),
                cls="mb-6"
            ),
            Div(
                *[member_card(p) for p in persons] if persons else [
                    Div(
                        P("No family members yet.",
                          cls="text-gray-400 text-lg text-center py-16"),
                        cls="col-span-full"
                    )
                ],
                id="member-list",
                cls="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4"
            ),
        ),
        title="FamilyView — Home",
        member_count=count
    )


# ---------------------------------------------------------------------------
# Member list (HTMX partial for search)
# ---------------------------------------------------------------------------

@rt("/members")
def get(q: str = ""):
    persons = db_module.search_persons(persons_tbl, q)
    if not persons:
        return Div(
            P("No members match your search.", cls="text-gray-400 text-center py-12"),
            id="member-list",
            cls="col-span-full"
        )
    return Div(
        *[member_card(p) for p in persons],
        id="member-list",
        cls="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4"
    )


# ---------------------------------------------------------------------------
# Add member
# ---------------------------------------------------------------------------

@rt("/members/new")
def get():
    return page_shell(
        Div(
            A("← Back", href="/", cls="text-sm text-gray-500 hover:text-gray-700 mb-4 inline-block"),
            H2("Add Family Member", cls="text-2xl font-bold text-gray-900 mb-6"),
            person_form(action="/members/new"),
        ),
        title="Add Member — FamilyView",
        member_count=_count()
    )


@rt("/members/new")
def post(name: str, birth_date: str = "", death_date: str = "",
         gender: str = "", bio: str = ""):
    person = dict(
        name=name.strip(),
        birth_date=birth_date or None,
        death_date=death_date or None,
        gender=gender or None,
        bio=bio.strip() or None,
    )
    row = persons_tbl.insert(person)
    return RedirectResponse(f"/members/{row['id']}", status_code=303)


# ---------------------------------------------------------------------------
# Member detail
# ---------------------------------------------------------------------------

@rt("/members/{id}")
def get(id: int):
    person = db_module.get_person(persons_tbl, id)
    if not person:
        return page_shell(
            P("Member not found.", cls="text-red-500 text-center py-16"),
            title="Not Found — FamilyView",
            member_count=_count()
        )

    birth = person.get("birth_date", "") or ""
    death = person.get("death_date", "") or ""
    gender = (person.get("gender") or "unknown").capitalize()
    bio = person.get("bio") or ""

    date_str = birth
    if death:
        date_str = f"{birth} – {death}" if birth else f"d. {death}"

    return page_shell(
        Div(
            A("← All Members", href="/",
              cls="text-sm text-gray-500 hover:text-gray-700 mb-6 inline-block"),
            Div(
                # Left column: photo + basic info
                Div(
                    photo_widget(person),
                    Div(
                        H2(person["name"],
                           cls="text-2xl font-bold text-gray-900 mt-4 text-center"),
                        P(date_str, cls="text-gray-500 text-center text-sm"),
                        P(gender, cls="text-gray-400 text-center text-sm"),
                        cls=""
                    ),
                    Div(
                        A("Edit", href=f"/members/{id}/edit",
                          cls="flex-1 text-center bg-emerald-600 text-white py-2 rounded-lg "
                              "text-sm font-semibold hover:bg-emerald-700 transition-colors"),
                        Button(
                            "Delete",
                            hx_delete=f"/members/{id}",
                            hx_target="body",
                            hx_push_url="/",
                            hx_confirm=f"Delete {person['name']}? This cannot be undone.",
                            cls="flex-1 text-center bg-red-50 text-red-600 py-2 rounded-lg "
                                "text-sm font-semibold hover:bg-red-100 transition-colors "
                                "cursor-pointer border-none"
                        ),
                        cls="flex gap-3 mt-5"
                    ),
                    cls="bg-white rounded-xl shadow-sm border border-gray-200 p-6 flex flex-col items-center"
                ),
                # Right column: bio + relationships + relatives
                Div(
                    # Bio
                    Div(
                        H3("Biography / Notes", cls="font-semibold text-gray-900 mb-3"),
                        P(bio if bio else "No biography added yet.",
                          cls="text-gray-600 text-sm leading-relaxed" + (" italic text-gray-400" if not bio else "")),
                        cls="bg-white rounded-xl shadow-sm border border-gray-200 p-5 mb-4"
                    ),
                    # Relationship management
                    relationship_widget(id, database, persons_tbl),
                    # Computed relatives
                    Div(
                        relatives_panel(id, database),
                        cls="mt-4"
                    ),
                    cls="flex flex-col gap-0"
                ),
                cls="grid grid-cols-1 lg:grid-cols-3 gap-6 lg:[&>*:first-child]:col-span-1 lg:[&>*:last-child]:col-span-2"
            ),
        ),
        title=f"{person['name']} — FamilyView",
        member_count=_count()
    )


# ---------------------------------------------------------------------------
# Edit member
# ---------------------------------------------------------------------------

@rt("/members/{id}/edit")
def get(id: int):
    person = db_module.get_person(persons_tbl, id)
    if not person:
        return RedirectResponse("/", status_code=303)
    return page_shell(
        Div(
            A(f"← Back to {person['name']}",
              href=f"/members/{id}",
              cls="text-sm text-gray-500 hover:text-gray-700 mb-4 inline-block"),
            H2(f"Edit: {person['name']}",
               cls="text-2xl font-bold text-gray-900 mb-6"),
            person_form(person, action=f"/members/{id}/edit"),
        ),
        title=f"Edit {person['name']} — FamilyView",
        member_count=_count()
    )


@rt("/members/{id}/edit")
def post(id: int, name: str, birth_date: str = "", death_date: str = "",
         gender: str = "", bio: str = ""):
    database.execute(
        "UPDATE persons SET name=?, birth_date=?, death_date=?, gender=?, bio=?, "
        "updated_at=datetime('now') WHERE id=?",
        [name.strip(), birth_date or None, death_date or None,
         gender or None, bio.strip() or None, id]
    )
    return RedirectResponse(f"/members/{id}", status_code=303)


# ---------------------------------------------------------------------------
# Delete member
# ---------------------------------------------------------------------------

@rt("/members/{id}")
def delete(id: int):
    database.execute("PRAGMA foreign_keys = ON")
    database.execute("DELETE FROM persons WHERE id = ?", [id])
    persons = list(persons_tbl.rows_where(order_by="name"))
    return Div(
        *[member_card(p) for p in persons],
        id="member-list",
        cls="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4"
    )


# ---------------------------------------------------------------------------
# Photo upload
# ---------------------------------------------------------------------------

@rt("/members/{id}/photo")
async def post(id: int, request: Request):
    form = await request.form()
    photo = form.get("photo")

    if not photo or not hasattr(photo, "filename") or not photo.filename:
        return RedirectResponse(f"/members/{id}", status_code=303)

    ext = photo.filename.rsplit(".", 1)[-1].lower()
    if ext not in {"jpg", "jpeg", "png", "gif", "webp"}:
        return P("Invalid file type.", cls="text-red-500 text-sm")

    # Delete old photo
    person = db_module.get_person(persons_tbl, id)
    if person and person.get("photo_path") and os.path.exists(person["photo_path"]):
        try:
            os.remove(person["photo_path"])
        except OSError:
            pass

    filename = f"{uuid.uuid4()}.{ext}"
    save_path = f"static/photos/{filename}"
    content = await photo.read()
    with open(save_path, "wb") as f:
        f.write(content)

    database.execute("UPDATE persons SET photo_path=? WHERE id=?", [save_path, id])
    updated = db_module.get_person(persons_tbl, id)
    return photo_widget(updated)


# ---------------------------------------------------------------------------
# Relationships
# ---------------------------------------------------------------------------

@rt("/relationships")
def post(person_id: int, other_id: int, rel_type: str, a_is_person: str = "1"):
    if not other_id:
        return RedirectResponse(f"/members/{person_id}", status_code=303)

    a_is = a_is_person == "1"
    if rel_type == "parent_child":
        # a_is_person=True means current person is PARENT of other_id
        parent_id = person_id if a_is else other_id
        child_id = other_id if a_is else person_id
        try:
            rels_tbl.insert(dict(
                person_a_id=parent_id,
                person_b_id=child_id,
                rel_type="parent_child"
            ))
        except Exception:
            pass  # UNIQUE constraint violation — already exists
    elif rel_type == "spouse":
        try:
            rels_tbl.insert(dict(
                person_a_id=person_id,
                person_b_id=other_id,
                rel_type="spouse"
            ))
        except Exception:
            pass

    return relationship_widget(person_id, database, persons_tbl)


@rt("/relationships/{id}")
def delete(id: int):
    rel = db_module.get_relationship_row(rels_tbl, id)
    if not rel:
        return ""

    database.execute("DELETE FROM relationships WHERE id = ?", [id])

    # Figure out which person's widget to refresh (prefer person_a as "current")
    person_id = rel["person_a_id"]
    return relationship_widget(person_id, database, persons_tbl)


# ---------------------------------------------------------------------------
# Relatives (computed, HTMX partial)
# ---------------------------------------------------------------------------

@rt("/members/{id}/relatives")
def get(id: int):
    return relatives_panel(id, database)


# ---------------------------------------------------------------------------
# Search (global, name + relationship label)
# ---------------------------------------------------------------------------

@rt("/search")
def get(q: str = "", person_id: int = 0):
    """
    If person_id is provided, search that person's relatives by relationship label.
    Otherwise, search all persons by name.
    """
    from relations import search_relatives_by_label

    if person_id and q:
        relatives = search_relatives_by_label(person_id, q, database)
        if not relatives:
            return Div(
                P("No relatives match that relationship.", cls="text-gray-400 text-center py-8"),
                id="member-list"
            )
        persons = [r["person"] for r in relatives]
        return Div(
            *[member_card(p) for p in persons],
            id="member-list",
            cls="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4"
        )

    persons = db_module.search_persons(persons_tbl, q)
    return Div(
        *[member_card(p) for p in persons],
        id="member-list",
        cls="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4"
    )


# ---------------------------------------------------------------------------
# Family tree page
# ---------------------------------------------------------------------------

@rt("/tree")
def get():
    count = _count()
    btn_base = "px-4 py-1.5 rounded-md text-sm transition-colors"
    btn_active   = f"{btn_base} bg-white text-emerald-700 font-semibold shadow-sm"
    btn_inactive = f"{btn_base} text-white/60"
    return page_shell(
        # family-chart CSS + fix for hardcoded white stroke on connection lines
        Link(rel="stylesheet",
             href="https://cdn.jsdelivr.net/npm/family-chart@0.9.0/dist/styles/family-chart.css"),
        Style("""
            #tree-fc-container path.link { stroke: #6b7280 !important; }
            #tree-fc-container path.link_upper,
            #tree-fc-container path.link_lower { stroke: #6b7280 !important; }
            #tree-fc-container .card_add,
            #tree-fc-container .card_edit,
            #tree-fc-container [class*="add_"],
            #tree-fc-container [class*="_add"] { display: none !important; }
        """),
        Div(
            # Header + toggle
            Div(
                Div(
                    H2("Family Tree", cls="text-2xl font-bold text-gray-900"),
                    P("Click a person to view their details. Scroll/pinch to zoom, drag to pan.",
                      cls="text-sm text-gray-500 mt-1"),
                ),
                Div(
                    Button("Graph", data_tree_mode="graph",
                           onclick="setTreeViewMode('graph')", cls=btn_active),
                    Button("Tree",  data_tree_mode="tree",
                           onclick="setTreeViewMode('tree')",  cls=btn_inactive),
                    cls="flex items-center gap-1 bg-emerald-700 rounded-lg p-1"
                ),
                cls="flex items-center justify-between mb-4"
            ),
            # Graph view container (D3 force-directed)
            Div(id="tree-graph-container",
                cls="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden",
                style="height: 75vh; width: 100%;"),
            # Tree view container (family-chart) — hidden initially
            Div(id="tree-fc-container",
                cls="f3 bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden",
                style="height: 75vh; width: 100%; display: none;"),
            # Legend
            Div(
                Span(cls="inline-block w-4 h-0.5 bg-gray-500 mr-2 align-middle"),
                Span("Parent–Child", cls="text-sm text-gray-600 mr-6"),
                Span(cls="inline-block w-4 h-0.5 border-t-2 border-dashed border-gray-400 mr-2 align-middle"),
                Span("Spouse / Partner", cls="text-sm text-gray-600 mr-6"),
                Span(cls="inline-block w-3 h-3 rounded-full bg-blue-400 mr-1 align-middle"),
                Span("Male", cls="text-sm text-gray-600 mr-4"),
                Span(cls="inline-block w-3 h-3 rounded-full bg-pink-400 mr-1 align-middle"),
                Span("Female", cls="text-sm text-gray-600 mr-4"),
                Span(cls="inline-block w-3 h-3 rounded-full bg-gray-400 mr-1 align-middle"),
                Span("Other / Unknown", cls="text-sm text-gray-600"),
                cls="mt-3 flex flex-wrap items-center gap-1"
            ),
            Script(src="https://cdn.jsdelivr.net/npm/d3@7/dist/d3.min.js"),
            Script(src="https://cdn.jsdelivr.net/npm/family-chart@0.9.0/dist/family-chart.min.js"),
            Script(src="/tree.js"),
        ),
        title="Family Tree — FamilyView",
        member_count=count
    )


@rt("/api/family-chart-data")
def get():
    data = build_family_chart_data(database)
    return Response(json.dumps(data), media_type="application/json")


@rt("/api/tree-data")
def get():
    data = build_tree_json(database)
    return Response(
        json.dumps(data),
        media_type="application/json"
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

serve()
