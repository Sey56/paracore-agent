# Modification Workflow (Agent)

Modifications use TWO kinds of tool calls. Know the difference:

**`explore_revit_data`** (SILENT — runs in background, user sees NO prompt):
→ Use for: discovering parameter names, checking level names, exploring schema.
→ The user never sees these — they happen silently.

**`execute_dynamic_query`** (USER-FACING — shows "Action Proposed" for approval):
→ Use ONLY for the FINAL modification that changes the model.
→ This is what the user actually asked you to do.

## Step 1 — DISCOVER & VALIDATE (silent, use explore_revit_data)

- For QUERIES (GroupByParam, Table, BarGraph, etc.): skip discovery. Just execute.
  If the query returns empty, the summarizer will say "No results found" — that's fine.
  Do NOT pre-check with GetMagicNames() or GetElements().Count().
- If you don't know the parameter name for a category, discover it:
  `explore_revit_data`: `GetElements("Walls").First().CombinedParams().Table()`
- If the user mentioned specific level names, verify they exist:
  `explore_revit_data`: `GetElements("Levels").Select(l => new { Name = l.GetStr("Name") }).Table()`
- If the catalog or parameter table already tells you the exact parameter name, skip discovery.

## Step 2 — MODIFY (user-facing, use execute_dynamic_query)

Generate the final modification code. Always include Println for conversational output:

```csharp
// Fluent chain — no Transact() needed:
var walls = GetElements("Walls").WhereParam("Base Constraint", "Level 01");
walls.SetParam("Top Offset", -150, "cm");
Println($"Updated {walls.Count()} walls — Top Offset set to -150 cm.");

// Manual foreach — Transact() REQUIRED:
var walls = GetElements("Walls").WhereParam("Base Constraint", "Level 01");
Transact("Update walls", () => {
    foreach (var w in walls) {
        w.SetVal("Top Constraint", "Level 02");
        w.SetNum("Top Offset", -150, "cm");
    }
});

// Delete:
GetElements("Generic Models").WhereMatches("TEMP").Delete();
```

**CRITICAL:** Step 2 is NOT optional. Discovery alone does NOT satisfy a modification request.

---

# Measurement Takeoff Workflow (TakeOff MCP)

When the user requests a quantity takeoff or bill of quantities, follow the
Paracore BIM Measurement Standard (v1.0) — 7 Work Groups in sequence.

## Discovery (before WG1)

1. `discover_model_categories` → see what's in the model
2. `get_levels` → understand vertical structure

## Work Groups 1–7 (in order)

Execute each Work Group's tools in sequence. Do not skip groups.
If a group returns empty (no elements of that type), note it and continue.

| WG | Tools | What you get |
|---|---|---|
| **1. Substructure** | get_excavation_quantities, get_concrete_quantities("Structural Foundations"), get_concrete_summary | Excavation, foundation concrete, formwork |
| **2. RC Frame** | get_concrete_quantities, get_concrete_summary, get_rebar_quantities, get_rebar_summary, compute_formwork | Concrete, rebar, formwork per category |
| **3. Masonry** | get_material_quantities("Walls"), get_compound_structure_layers("Walls"), get_opening_areas | Wall materials, layers, deductions |
| **4. Openings** | get_door_schedule, get_window_schedule | Door/window dimensions |
| **5. Finishes** | get_wall_finish_areas, get_floor_finish_summary, get_room_data | Plaster, floor finishes, rooms |
| **6. Steel** | get_steel_tonnage_summary | Steel tonnage (if present) |
| **7. MEP** | get_linear_summary | Pipes, ducts, trays (if present) |

## Export

After all 7 Work Groups complete, call `export_takeoff_to_excel` to produce
the final spreadsheet. Present the file path to the user.

## Rules

- Present each Work Group's results before proceeding to the next
- Tag each group with its WG number and name
- If an element category doesn't exist in the model, say so and move on
- All quantities from model geometry — the engine does not estimate
- The QS adds specifications, rates, and preliminaries after export
