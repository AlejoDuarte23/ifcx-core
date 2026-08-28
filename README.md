# ifcx-core

Rust and Python support for IFC spatial relationships and materials. Complements
[`ifclite-geom`](https://ifclite.dev/docs/api/python/) and supports IFC4 and
IFC4X3 on Python 3.10+.

```python
import ifcx_core

data = ifcx_core.model_data(open("model.ifc", "rb").read())
```

## Development

```bash
cargo test
uv run maturin develop --uv
.venv/bin/python -m pytest -q
```

See [testing](docs/testing.md). Licensed under MPL-2.0.
