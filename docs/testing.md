# Testing strategy

`ifcx-core` supports IFC4 and IFC4X3. IFC2X3 is deliberately rejected.

The suite uses three complementary levels of verification.

## Self-contained IfcOpenShell parity matrix

`tests/test_feature_matrix.py` creates small valid IFC files with IfcOpenShell,
serializes them to STEP, parses those bytes with `ifcx-core`, and independently
derives the expected results from the IfcOpenShell model.

The spatial matrix runs against IFC4 and IFC4X3 in metres and millimetres. It
checks:

- exact edges for aggregation, nesting, containment, spatial references, type
  assignment, and material association;
- the complete attached hierarchy and orphan detection;
- node identity, names, long names, direct elements, references, and children;
- site, building/facility, storey, space, and spatial-zone indexes;
- direct and placement-derived storey elevations in metres;
- reverse container and storey maps, including aggregate/nest descendants; and
- all currently recognized IFC4X3 facility and facility-part hierarchy types.

The material matrix runs against IFC4 and IFC4X3. It checks:

- plain materials, layer sets, profile sets, constituent sets, and lists;
- layer-set and profile-set usage indirection;
- material names, descriptions, categories, thicknesses, ventilation flags,
  priorities, profiles, fractions, and ordered leaves;
- direct assignments, type inheritance, direct precedence, multiple
  associations, duplicate-definition removal, and deterministic ordering; and
- native Python and JSON API equivalence after applying JSON's required
  stringification of numeric object keys.

These tests do not require a checked-in IFC fixture and therefore run in CI.

## Rust invariants and error behavior

`tests/core.rs` covers behavior for which IfcOpenShell is not the correct
oracle: cycle termination, deterministic output, dangling references, missing
projects/entities, schema rejection, multiple-association ordering, and the
IFClite-compatible spatial propagation contract.

## Optional large-model regression

`tests/test_ifcopenshell_parity.py` compares a real 280,178-entity IFC model
against IfcOpenShell. It is skipped when the model is unavailable. Set
`IFCX_PARITY_MODEL` to run it with a local model:

```bash
IFCX_PARITY_MODEL=/absolute/path/model.ifc .venv/bin/python -m pytest -m integration -q
```

The self-contained matrix is the branch-coverage suite. Large models add scale
and real-world exporter variation, so additional known models can be exercised
through the same environment variable without becoming repository assets.

## Local commands

```bash
cargo fmt --check
cargo clippy --all-targets --all-features -- -D warnings
cargo test
env -u CONDA_PREFIX uv run maturin develop --uv
.venv/bin/python -m pytest -q
```

On systems without Conda, omit `env -u CONDA_PREFIX`.
