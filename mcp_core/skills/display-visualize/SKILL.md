---
name: display-visualize
description: Rendering data as tables and charts — Table, BarGraph, PieGraph, LineGraph, Println, Select projection
---

# Display & Visualize

Render query results as tables, charts, and text output. These are the final step in every fluent chain.

## Table() — interactive data grid

`.Table()` renders data as an interactive grid. Column headers match Revit parameter names for editing.

**SAFE — always works (fixed columns):**
```csharp
.CombinedParams().Table()                     // 4 cols: Scope | Name | Storage | Value
.GroupByParam("X").Table()                    // 2 cols: Group | Count
.GroupByParam("X", "Sum", "u").Table()        // 3 cols: Group | Count | Total
.Select(e => new { ... }).Table()             // You chose the columns, so it's safe
```

**FORBIDDEN — dumps every parameter as a column (50-200 columns):**
```csharp
GetElements("Walls").Table()                  // 78+ columns × 593 rows = disaster
.WhereParam(...).Table()                      // filtered but still all columns
.SetParam(...).Table()                        // after write, still all columns
```

**Rule:** If the thing before `.Table()` is NOT `CombinedParams`, `GroupByParam`, or `Select` with explicit columns, add `.Select()` first.

## Column Naming Rules for .Select()

Column names MUST match Revit parameter names. Replace spaces with underscores — the renderer converts them BACK to spaces:

```csharp
// CORRECT:
.Select(w => new {
    w.Id,
    Base_Constraint = w.GetStr("Base Constraint"),   // displays as "Base Constraint"
    Top_Offset = w.GetNum("Top Offset", "cm"),        // displays as "Top Offset"
    Area = w.GetNum("Area", "m2")                     // displays as "Area"
}).Table()

// WRONG:
Top_Offset_cm = w.GetNum("Top Offset", "cm")    // "Top Offset cm" ≠ "Top Offset"
Area_m2 = r.GetNum("Area", "m2")                // "Area m2" ≠ "Area"
```

**NEVER add unit suffixes to column names.** The unit is in `GetNum(name, unit)`, not in the column header.

## Charts

After `GroupByParam` — chain directly, no `.Select()` needed:
```csharp
GetElements("Rooms").GroupByParam("Level", "Area", "m2").BarGraph()
GetElements("Doors").GroupByParam("Level").PieGraph()
GetElements("Walls").GroupByParam("Base Constraint", "Length", "m").LineGraph()
```

**NOTE:** `.Bar()` does NOT exist — use `.BarGraph()`.

Charts render in the Analytics tab, not in chat. Tell the user to check there.

## Println() — status messages

```csharp
Println($"Updated {walls.Count()} walls — Top Offset set to -150 cm.");
Println("Done. Deleted 5 columns.");
```

**Use Println ONLY for status messages**, not data display. Never foreach+Println loops for data — use `.Table()` instead.

## Projection with .Select()

LINQ `.Select()` projects columns for `.Table()`:
```csharp
GetElements("Walls").WhereParam("Base Constraint", "Level 1")
    .Select(w => new {
        w.Id,
        Name = w.GetStr("Name"),
        Length = w.GetNum("Length", "m"),
        Area = w.GetNum("Area", "m2")
    }).Table()
```

Always put `Id` as the first column in `.Select()` projections.
