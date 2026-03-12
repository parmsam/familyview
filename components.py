"""Reusable FastHTML FT component functions."""

from fasthtml.common import *
from relations import get_all_relatives
import db as db_module


# ---------------------------------------------------------------------------
# Layout
# ---------------------------------------------------------------------------

def nav_bar(member_count: int = 0):
    return Nav(
        Div(
            A(
                Span("🌳", cls="text-2xl"),
                Span("FamilyView", cls="text-xl font-bold text-white ml-2"),
                href="/",
                cls="flex items-center hover:opacity-80 transition-opacity"
            ),
            cls="flex items-center"
        ),
        Div(
            Input(
                type="search",
                name="q",
                placeholder="Search by name or relationship...",
                hx_get="/members",
                hx_trigger="input changed delay:300ms, search",
                hx_target="#member-list",
                hx_swap="innerHTML",
                cls="w-80 px-4 py-2 rounded-lg bg-white/10 text-white placeholder-white/60 "
                    "border border-white/20 focus:outline-none focus:ring-2 focus:ring-white/40"
            ),
            cls="flex-1 mx-8 max-w-lg"
        ),
        Div(
            Span(f"{member_count} members", cls="text-white/70 text-sm mr-4"),
            A("Family Tree", href="/tree",
              cls="text-white/90 hover:text-white mr-4 text-sm font-medium"),
            A(
                "+ Add Member",
                href="/members/new",
                cls="bg-white text-emerald-700 px-4 py-2 rounded-lg text-sm font-semibold "
                    "hover:bg-white/90 transition-colors"
            ),
            cls="flex items-center"
        ),
        cls="bg-emerald-700 px-6 py-4 flex items-center justify-between shadow-md sticky top-0 z-50"
    )


def page_shell(*content, title="FamilyView", member_count=0):
    return Titled(
        title,
        nav_bar(member_count),
        Main(*content, cls="max-w-7xl mx-auto px-6 py-8"),
        cls="min-h-screen bg-gray-50"
    )


# ---------------------------------------------------------------------------
# Member cards
# ---------------------------------------------------------------------------

def member_card(person: dict):
    photo = person.get("photo_path")
    gender = (person.get("gender") or "unknown").lower()
    gender_color = {
        "male": "bg-blue-100 text-blue-800",
        "female": "bg-pink-100 text-pink-800",
    }.get(gender, "bg-gray-100 text-gray-700")

    birth = person.get("birth_date", "") or ""
    death = person.get("death_date", "") or ""
    date_str = birth
    if death:
        date_str = f"{birth} – {death}" if birth else f"d. {death}"

    photo_el = (
        Img(src=f"/{photo}", alt=person["name"],
            cls="w-16 h-16 rounded-full object-cover")
        if photo else
        Div(person["name"][0].upper(),
            cls="w-16 h-16 rounded-full bg-emerald-200 text-emerald-800 "
                "flex items-center justify-center text-2xl font-bold")
    )

    return Div(
        Div(
            photo_el,
            Div(
                A(person["name"],
                  href=f"/members/{person['id']}",
                  cls="font-semibold text-gray-900 hover:text-emerald-700 transition-colors"),
                Div(date_str, cls="text-sm text-gray-500 mt-0.5"),
                Span(gender, cls=f"inline-block text-xs px-2 py-0.5 rounded-full mt-1 {gender_color}"),
                cls="ml-4 flex-1 min-w-0"
            ),
            cls="flex items-center"
        ),
        Div(
            A("View", href=f"/members/{person['id']}",
              cls="text-sm text-emerald-700 hover:text-emerald-900 font-medium mr-3"),
            A("Edit", href=f"/members/{person['id']}/edit",
              cls="text-sm text-gray-500 hover:text-gray-700 mr-3"),
            Button(
                "Delete",
                hx_delete=f"/members/{person['id']}",
                hx_target="#member-list",
                hx_swap="innerHTML",
                hx_confirm=f"Delete {person['name']}? This cannot be undone.",
                cls="text-sm text-red-500 hover:text-red-700 cursor-pointer border-none bg-transparent"
            ),
            cls="mt-3 flex items-center border-t border-gray-100 pt-3"
        ),
        cls="bg-white rounded-xl shadow-sm border border-gray-200 p-4 "
            "hover:shadow-md transition-shadow"
    )


def member_list(persons: list[dict]):
    if not persons:
        return Div(
            Div("🌿", cls="text-5xl mb-3"),
            P("No family members found.", cls="text-gray-500 text-lg"),
            P("Add your first member to get started.",
              cls="text-gray-400 text-sm mt-1"),
            cls="col-span-full text-center py-16"
        )
    return Div(
        *[member_card(p) for p in persons],
        id="member-list",
        cls="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4"
    )


# ---------------------------------------------------------------------------
# Forms
# ---------------------------------------------------------------------------

def person_form(person: dict | None = None, action: str = "/members/new"):
    v = person or {}
    field_cls = ("w-full px-3 py-2 border border-gray-300 rounded-lg "
                 "focus:outline-none focus:ring-2 focus:ring-emerald-500 bg-white")
    label_cls = "block text-sm font-medium text-gray-700 mb-1"

    return Form(
        Div(
            Label("Full Name *", cls=label_cls),
            Input(name="name", value=v.get("name", ""), required=True,
                  placeholder="e.g. Jane Smith", cls=field_cls),
            cls="mb-4"
        ),
        Div(
            Div(
                Label("Birth Date", cls=label_cls),
                Input(name="birth_date", type="date",
                      value=v.get("birth_date", "") or "", cls=field_cls),
                cls="flex-1"
            ),
            Div(
                Label("Death Date", cls=label_cls),
                Input(name="death_date", type="date",
                      value=v.get("death_date", "") or "", cls=field_cls),
                cls="flex-1"
            ),
            cls="flex gap-4 mb-4"
        ),
        Div(
            Label("Gender", cls=label_cls),
            Select(
                Option("Select...", value=""),
                Option("Male", value="male",
                       selected=v.get("gender") == "male"),
                Option("Female", value="female",
                       selected=v.get("gender") == "female"),
                Option("Other", value="other",
                       selected=v.get("gender") == "other"),
                Option("Unknown", value="unknown",
                       selected=v.get("gender") == "unknown"),
                name="gender",
                cls=field_cls
            ),
            cls="mb-4"
        ),
        Div(
            Label("Bio / Notes", cls=label_cls),
            Textarea(
                v.get("bio", "") or "",
                name="bio",
                rows=4,
                placeholder="Background, notable facts, memories...",
                cls=field_cls
            ),
            cls="mb-6"
        ),
        Div(
            Button(
                "Save Member",
                type="submit",
                cls="bg-emerald-600 text-white px-6 py-2 rounded-lg font-semibold "
                    "hover:bg-emerald-700 transition-colors"
            ),
            A("Cancel", href="/",
              cls="ml-4 text-gray-500 hover:text-gray-700"),
            cls="flex items-center"
        ),
        action=action,
        method="post",
        cls="bg-white rounded-xl shadow-sm border border-gray-200 p-6"
    )


# ---------------------------------------------------------------------------
# Photo widget
# ---------------------------------------------------------------------------

def photo_widget(person: dict):
    photo = person.get("photo_path")
    person_id = person["id"]

    current_photo = (
        Img(src=f"/{photo}", alt=person["name"],
            cls="w-32 h-32 rounded-full object-cover border-4 border-white shadow-md")
        if photo else
        Div(
            person["name"][0].upper(),
            cls="w-32 h-32 rounded-full bg-emerald-200 text-emerald-800 "
                "flex items-center justify-center text-5xl font-bold "
                "border-4 border-white shadow-md"
        )
    )

    return Div(
        current_photo,
        Form(
            Input(type="file", name="photo", accept="image/*",
                  cls="hidden", id=f"photo-input-{person_id}",
                  hx_encoding="multipart/form-data"),
            Label(
                "Change Photo",
                hx_for=f"photo-input-{person_id}",
                cls="mt-2 text-xs text-emerald-600 hover:text-emerald-800 "
                    "cursor-pointer font-medium"
            ),
            hx_post=f"/members/{person_id}/photo",
            hx_encoding="multipart/form-data",
            hx_target=f"#photo-widget-{person_id}",
            hx_swap="outerHTML",
            id=f"photo-widget-{person_id}",
            cls="flex flex-col items-center"
        ),
        cls="flex flex-col items-center"
    )


# ---------------------------------------------------------------------------
# Relationship widget
# ---------------------------------------------------------------------------

def relationship_widget(person_id: int, database, persons):
    all_persons = list(persons.rows_where("id != ?", [person_id], order_by="name"))

    parents = db_module.get_parents(database, person_id)
    children = db_module.get_children(database, person_id)
    spouses = db_module.get_spouses(database, person_id)

    def person_option_list():
        return [Option(p["name"], value=p["id"]) for p in all_persons]

    def rel_badge(p, rel_id):
        return Span(
            p["name"],
            Button(
                "×",
                hx_delete=f"/relationships/{rel_id}",
                hx_target="#relationship-widget",
                hx_swap="outerHTML",
                cls="ml-1 text-gray-400 hover:text-red-500 font-bold cursor-pointer "
                    "border-none bg-transparent"
            ),
            cls="inline-flex items-center bg-gray-100 text-gray-700 "
                "rounded-full px-3 py-1 text-sm mr-2 mb-2"
        )

    def get_rel_id(person_a, person_b, rel_type):
        rels = database.t.relationships
        rows = list(rels.rows_where(
            "(person_a_id = ? AND person_b_id = ? OR person_a_id = ? AND person_b_id = ?) "
            "AND rel_type = ?",
            [person_a, person_b, person_b, person_a, rel_type]
        ))
        return rows[0]["id"] if rows else None

    field_cls = ("w-full px-3 py-2 border border-gray-300 rounded-lg "
                 "focus:outline-none focus:ring-2 focus:ring-emerald-500 text-sm bg-white")

    def add_form(label, rel_type, a_is_person=True):
        # a_is_person=True → current person is person_a (parent of selected)
        # a_is_person=False → current person is person_b (child of selected)
        form_id = f"rel-form-{rel_type}-{'a' if a_is_person else 'b'}"
        select_id = f"rel-select-{rel_type}-{'a' if a_is_person else 'b'}"
        hint_id = f"rel-hint-{rel_type}-{'a' if a_is_person else 'b'}"
        return Form(
            Div(
                Select(
                    Option("Select person...", value=""),
                    *person_option_list(),
                    name="other_id",
                    id=select_id,
                    onchange=f"""
                        var btn = document.getElementById('{form_id}-btn');
                        var hint = document.getElementById('{hint_id}');
                        if (this.value) {{
                            btn.disabled = false;
                            btn.classList.remove('opacity-50', 'cursor-not-allowed');
                            hint.classList.add('hidden');
                        }} else {{
                            btn.disabled = true;
                            btn.classList.add('opacity-50', 'cursor-not-allowed');
                            hint.classList.remove('hidden');
                        }}
                    """,
                    cls=field_cls
                ),
                Input(type="hidden", name="rel_type", value=rel_type),
                Input(type="hidden", name="person_id", value=person_id),
                Input(type="hidden", name="a_is_person",
                      value="1" if a_is_person else "0"),
                Button(
                    f"+ Add {label}",
                    type="submit",
                    id=f"{form_id}-btn",
                    disabled=True,
                    cls="ml-2 bg-emerald-600 text-white px-3 py-2 rounded-lg text-sm "
                        "transition-colors whitespace-nowrap opacity-50 cursor-not-allowed"
                ),
                cls="flex items-center"
            ),
            P(
                "Select a family member from the list first.",
                id=hint_id,
                cls="text-xs text-amber-600 mt-1"
            ),
            hx_post="/relationships",
            hx_target="#relationship-widget",
            hx_swap="outerHTML",
            id=form_id,
        )

    # Build badges for existing relationships - we need rel IDs
    parent_badges = []
    for p in parents:
        rid = get_rel_id(p["id"], person_id, "parent_child")
        if rid:
            parent_badges.append(rel_badge(p, rid))

    children_badges = []
    for p in children:
        rid = get_rel_id(person_id, p["id"], "parent_child")
        if rid:
            children_badges.append(rel_badge(p, rid))

    spouse_badges = []
    for p in spouses:
        rid = get_rel_id(person_id, p["id"], "spouse")
        if not rid:
            rid = get_rel_id(p["id"], person_id, "spouse")
        if rid:
            spouse_badges.append(rel_badge(p, rid))

    section_cls = "mb-5"
    section_title_cls = "text-sm font-semibold text-gray-700 mb-2 uppercase tracking-wide"

    return Div(
        Div(
            H3("Relationships", cls="font-semibold text-gray-900 mb-4 text-lg"),
            Div(
                P("Parents", cls=section_title_cls),
                Div(*parent_badges, cls="mb-2") if parent_badges else P("None", cls="text-sm text-gray-400 mb-2"),
                add_form("Parent", "parent_child", a_is_person=False),
                cls=section_cls
            ),
            Div(
                P("Children", cls=section_title_cls),
                Div(*children_badges, cls="mb-2") if children_badges else P("None", cls="text-sm text-gray-400 mb-2"),
                add_form("Child", "parent_child", a_is_person=True),
                cls=section_cls
            ),
            Div(
                P("Spouses / Partners", cls=section_title_cls),
                Div(*spouse_badges, cls="mb-2") if spouse_badges else P("None", cls="text-sm text-gray-400 mb-2"),
                add_form("Spouse/Partner", "spouse", a_is_person=True),
                cls=section_cls
            ),
            cls="bg-white rounded-xl shadow-sm border border-gray-200 p-5"
        ),
        id="relationship-widget"
    )


# ---------------------------------------------------------------------------
# Relatives panel (computed relationships)
# ---------------------------------------------------------------------------

def relatives_panel(person_id: int, database):
    relatives = get_all_relatives(person_id, database)
    if not relatives:
        return Div(
            P("No computed relatives yet. Add relationships above.",
              cls="text-sm text-gray-400 italic"),
            id="relatives-panel"
        )

    # Group by category
    groups: dict[str, list] = {"direct": [], "extended": [], "cousins": []}
    for r in relatives:
        cat = r.get("category", "extended")
        groups.setdefault(cat, []).append(r)

    group_labels = {
        "direct": "Direct Family",
        "extended": "Extended Family",
        "cousins": "Cousins",
    }

    sections = []
    for cat, label in group_labels.items():
        items = groups.get(cat, [])
        if not items:
            continue
        # Sort by label then name
        items.sort(key=lambda r: (r["label"], r["person"]["name"]))
        sections.append(
            Div(
                H4(label, cls="text-xs font-semibold text-gray-500 uppercase "
                               "tracking-wide mb-2 mt-4 first:mt-0"),
                *[
                    Div(
                        A(r["person"]["name"],
                          href=f"/members/{r['person']['id']}",
                          cls="text-sm font-medium text-emerald-700 hover:text-emerald-900"),
                        Span(f" — {r['label']}",
                             cls="text-sm text-gray-500"),
                        # data-rel used by the JS filter below
                        data_rel=f"{r['person']['name'].lower()} {r['label'].lower()}",
                        cls="relative-row py-1 border-b border-gray-50 last:border-0"
                    )
                    for r in items
                ]
            )
        )

    filter_script = Script("""
        function filterRelatives(q) {
            var term = q.toLowerCase().trim();
            var rows = document.querySelectorAll('#relatives-panel .relative-row');
            var emptySections = 0, totalSections = 0;
            rows.forEach(function(row) {
                var match = !term || row.dataset.rel.includes(term);
                row.style.display = match ? '' : 'none';
            });
            // Show/hide section headers based on whether any row in them is visible
            document.querySelectorAll('#relatives-panel h4').forEach(function(h4) {
                var section = h4.parentElement;
                var visible = section.querySelectorAll('.relative-row:not([style*="none"])');
                section.style.display = visible.length ? '' : 'none';
            });
            // Show no-results message
            var noResults = document.getElementById('relatives-no-results');
            var anyVisible = document.querySelectorAll('#relatives-panel .relative-row:not([style*="none"])').length > 0;
            if (noResults) noResults.style.display = (!term || anyVisible) ? 'none' : '';
        }
    """)

    return Div(
        Div(
            H3("All Relatives", cls="font-semibold text-gray-900 text-lg"),
            Input(
                type="search",
                placeholder='Filter by name or relationship (e.g. "cousin", "uncle")…',
                oninput="filterRelatives(this.value)",
                cls="mt-2 w-full px-3 py-1.5 text-sm border border-gray-200 rounded-lg "
                    "focus:outline-none focus:ring-2 focus:ring-emerald-400 bg-gray-50"
            ),
            cls="mb-3"
        ),
        P("Computed from parent-child and spouse links above.",
          cls="text-xs text-gray-400 mb-4"),
        P("No relatives match your filter.", id="relatives-no-results",
          cls="text-sm text-gray-400 italic hidden"),
        *sections,
        filter_script,
        id="relatives-panel",
        cls="bg-white rounded-xl shadow-sm border border-gray-200 p-5"
    )
