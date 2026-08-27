# IfcOpenShell parity report

The first-draft implementation was verified against IfcOpenShell 0.8.5 using:

```text
BuildingBIMModel_omniclass_qto_enriched.ifc
SHA-256 4f0bebf282ffed5a29c8f129995945950286b5294ab58f0b39723e0ecca4107f
Schema IFC4
280,178 STEP entities
Length unit scale 0.001 m
```

The model is an external test fixture and is not distributed with this
repository. Set `IFCX_PARITY_MODEL` to run the same integration suite with a
local copy.

## Exact relationship parity

`tests/test_ifcopenshell_parity.py` constructs the edge sets independently
through IfcOpenShell and requires exact equality of
`(relationship_id, relating_id, related_id)` tuples.

| Relationship | Relationships | Edges | Result |
|---|---:|---:|---|
| `IfcRelAggregates` | 56 | 4,914 | Exact |
| `IfcRelNests` | 30 | 30 | Exact |
| `IfcRelContainedInSpatialStructure` | 8 | 850 | Exact |
| `IfcRelReferencedInSpatialStructure` | 0 | 0 | Exact |
| `IfcRelDefinesByType` | 813 | 5,721 | Exact |
| `IfcRelAssociatesMaterial` | 332 | 6,201 | Exact |

## Spatial results

- One site, one building, five storeys, and 116 spaces are represented without
  orphan spatial nodes.
- Direct `by_site`, `by_building`, `by_storey`, and `by_space` contents exactly
  match IfcOpenShell's `ContainsElements` inverses.
- Every reverse container mapping emitted by `ifcx-core` agrees with
  `ifcopenshell.util.element.get_container`.
- `ifcx-core` follows the IFClite TypeScript contract: reverse maps cover direct
  containment and aggregate/nest descendants. IfcOpenShell additionally walks
  opening/filling ancestry, so its resolved universe can be larger. This model
  has 5,765 `IfcElement` instances; the additional IfcOpenShell paths are not
  reclassified as IFC spatial containment edges.

## Material results

- 50 `IfcMaterial` definitions and 314 `IfcMaterialConstituentSet` definitions
  are resolved.
- The 332 associations target 5,533 element occurrences and 668 type objects.
- `ifcx-core` resolves exactly the same 5,533 element assignments as
  `ifcopenshell.util.element.get_material`.
- Constituent expansion produces the same ordered leaf material IDs as
  `ifcopenshell.util.element.get_materials` for every assigned element.
- The model does not contain layer/profile sets or usage indirection, so those
  families are covered by synthetic Rust tests in `tests/core.rs`.
