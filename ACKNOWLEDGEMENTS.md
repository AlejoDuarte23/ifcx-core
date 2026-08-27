# Acknowledgements

`ifcx-core` exists because the IFClite project established a fast, practical
architecture for IFC parsing and geometry across Rust, TypeScript, WebAssembly,
and Python.

We gratefully acknowledge the **IFC-Lite Contributors and LTplus-AG**. This
project:

- depends on IFClite's [`ifc-lite-core`](https://crates.io/crates/ifc-lite-core)
  Rust parser;
- ports behavioral ideas from IFClite's TypeScript relationship extractor,
  spatial hierarchy builder, and material resolver; and
- follows IFClite's PyO3/maturin packaging approach for native Python wheels.

The upstream source is available at
[github.com/LTplus-AG/ifc-lite](https://github.com/LTplus-AG/ifc-lite) and is
licensed under the Mozilla Public License 2.0. `ifcx-core` uses the same
license, retains MPL source headers, and aims to keep its relationship behavior
verifiable against both IFClite and IfcOpenShell.
