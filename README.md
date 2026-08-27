# ifcx-core

`ifcx-core` is a native Rust and Python library for IFC spatial relationships
and material assignments. It complements
[`ifclite-geom`](https://ifclite.dev/docs/api/python/): geometry, attributes,
property sets, and quantities stay in `ifclite-geom`; `ifcx-core` supplies the
relationship data needed by the `ifcx` viewer.

```python
import ifcx_core

with open("model.ifc", "rb") as stream:
    data = ifcx_core.model_data(stream.read())

print(data["spatial"]["roots"])
print(data["materials"]["element_materials"])
```

The output uses IFC STEP/express IDs throughout, so it joins directly against
`ifclite_geom.geometry_data_buffers()` and `ifclite_geom.entity_data()`.

## Current scope

- Bidirectional-friendly relationship edges for aggregation, nesting, spatial
  containment/reference, type assignment, and material association.
- Project/site/building/storey/space hierarchy with reverse element lookups,
  cycle protection, storey elevation, and IFC4.3 spatial facilities.
- Direct and type-inherited material assignments, including plain materials,
  layer sets, profile sets, constituent sets, lists, and usage indirection.
- A stable Rust API (`analyze_ifc`) and Python APIs (`model_data`,
  `model_data_json`).

## Development

```bash
cargo test
uvx --from maturin maturin develop
python -m pytest -q
```

The project is licensed under MPL-2.0. See [ACKNOWLEDGEMENTS.md](ACKNOWLEDGEMENTS.md)
for the IFClite attribution and implementation references.

The requested large-model comparison is recorded in
[docs/ifcopenshell-parity.md](docs/ifcopenshell-parity.md).
