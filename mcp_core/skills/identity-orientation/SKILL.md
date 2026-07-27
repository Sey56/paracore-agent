---
name: identity-orientation
description: Element identity, family info, door/window orientation — FamilyName, Matches, RoomFrom, Handing, HingeSide
---

# Identity & Orientation

Identify what an element is, match it by name, and for doors/windows, determine orientation and room relationships.

## Identity Helpers

```csharp
element.FamilyName()                       // "Basic Wall"
element.GetStr("Family and Type")          // full identity string
element.Matches("HCB")                     // fuzzy match: Type Name + Family Name
element.GetElementType()                   // returns the ElementType for any instance
id.ToElement(Doc)                          // resolve ElementId → Element
```

## Door & Window Orientation

Stable regardless of flips:

```csharp
door.RoomFrom()                            // "LIVING ROOM"
door.RoomTo()                              // "CORRIDOR"
door.RoomAccess()                          // alias for RoomFrom
door.RoomDestination()                     // alias for RoomTo
door.Handing()                             // "LH" or "RH"
door.HingeSide()                           // "Left" or "Right"
door.IsHandFlipped                         // true/false
door.IsFacingFlipped                       // true/false
door.FindSwingArc()                        // largest Arc in geometry (swing path)
```

## Standard Door Filter

```csharp
// Exclude curtain-wall-hosted glass doors
GetElements<FamilyInstance>("Doors").StandardDoor().Table()
// → 33 standard doors (out of 40 total)

door.IsStandardDoor()                      // true if NOT hosted on a Curtain Wall
```

## Native Identity Properties (dot access)

```
el.Id          → ElementId (use .IntegerValue for int)
el.Name        → string (type name on instances, element name otherwise)
el.Symbol      → ElementId of the family symbol
```

## Typed vs String Retrieval

Some categories have C# classes (`.Name`, `.Area` are dot-access properties). Others are loadable families — must use `.GetStr()` for everything.

**Typed (use `<T>()`):** Wall, Floor, Room, Ceiling, Level, Roof, Stairs, View, ViewSheet, Grid

**String (use `("Category")`):** Doors, Windows, Furniture, Structural Columns, Structural Framing, Generic Models
