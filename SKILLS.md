# Paracore Method Skills

Nine operation-based skills. Read `query-filter` first (always needed), then pull others as the task demands.

## query-filter
Element retrieval, filtering, and sorting.
**When:** Always. Every query starts here.

GetElements (typed + string), WhereParam (string match, numeric comparison, starts/contains), WhereAnyParam, WhereTypeParam, WhereMatches, WhereMaterial/WhereMaterialNot, StandardDoor, OrderByParam/OrderByParamDesc, Count, Any, First, FirstOrDefault, Take, Skip.

## aggregate-group
Grouping, counting, and summing.
**When:** "How many per level?", "Total area by type?", any aggregation.

GroupByParam (count per group), GroupByParam with sum (3-arg overload), SumParam (grand total), what CANNOT be chained after GroupByParam, common pattern quick-reference table.

## parameter-access
Reading element parameters and properties.
**When:** Reading any data from elements.

GetStr, GetNum, GetVal, GetInt, type-level accessors (GetTypeStr/Num/Val/Int), native properties (dot access: Id, Name, Area, Volume, Location.Point.X/Y/Z), unit strings reference.

## write-modify
Modifying elements.
**When:** Any modification request.

Transaction rules (single auto-transact, collection bulk, manual foreach), SetNum with unit conversion, SetVal (smart setter — string/double/int/ElementId), SetParam (collection bulk, dynamic factory, indexed factory), Delete/Hide/Unhide/Isolate, Transact syntax, chainable bulk writes.

## display-visualize
Tables, charts, and output.
**When:** Rendering results.

Table() safe/forbidden patterns, column naming rules (underscores to spaces, no unit suffixes), BarGraph/PieGraph/LineGraph (after GroupByParam, no Select needed), Println (status only, never for data), LINQ Select projection for Table.

## discovery-debug
Exploring unknown elements.
**When:** "What parameters does this element have?", first time with a category.

CombinedParams (primary — all params + values, zero args), BuiltInParams, InstanceParams, TypeParams, ParamsDict, NativeProperties, ReflectionProperties/Methods, Peek, GeometrySummary, discovery workflow (CombinedParams first, search_schema for fast cached lookup).

## create-geometry
Creating new Revit elements.
**When:** "Place a wall/floor/door/column."

XYZ, Line.CreateBound, Arc.Create, CurveLoop, Wall.Create, Floor.Create, FamilyInstance placement, column placement, InputUnit (human to feet), pre-imported namespaces, Transact REQUIRED for all creation.

## identity-orientation
Element identity and door/window data.
**When:** Identifying what something is, door schedules, orientation queries.

FamilyName, Matches (fuzzy), GetElementType, id.ToElement, door methods (RoomFrom/RoomTo, Handing LH/RH, HingeSide Left/Right, IsHandFlipped, IsFacingFlipped, FindSwingArc), StandardDoor filter, IsStandardDoor, typed-vs-string retrieval table.

## materials-units
Materials, unit conversion, numeric helpers.
**When:** Material queries, unit conversion, geometry comparisons.

Materials/Table, MaterialNames, GetMaterialNames, WhereMaterial/WhereMaterialNot filters, InputUnit (human to feet), OutputUnit (feet to human), FormatUnit, FormatValueOnly, RoundTo, accepted unit strings table, precision-aware comparisons (IsAlmostEqualTo, AlmostZero, IsLessThan, IsGreaterThan, IsPositive, IsNegative).

## Typical Usage Patterns

**Simple query** ("list all doors on Level 1"):
query-filter + display-visualize

**Aggregation** ("room area per level"):
query-filter + aggregate-group + display-visualize

**Modification** ("set fire rating on all Level 1 walls"):
query-filter + write-modify + display-visualize

**Exploration** ("what parameters do these columns have?"):
query-filter + discovery-debug + display-visualize

**Creation** ("place a 900mm door on Level 1"):
query-filter + create-geometry + write-modify (for parameters)

**Door schedule** ("door schedule with handing"):
query-filter + identity-orientation + display-visualize

**Material query** ("what material are these walls?"):
query-filter + materials-units + display-visualize
