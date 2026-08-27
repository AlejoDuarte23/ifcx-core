// This Source Code Form is subject to the terms of the Mozilla Public
// License, v. 2.0. If a copy of the MPL was not distributed with this
// file, You can obtain one at https://mozilla.org/MPL/2.0/.

//! IFC spatial and material relationship extraction.
//!
//! `ifcx-core` complements `ifclite-geom`: the latter produces geometry and
//! entity/property data, while this crate resolves the relationship structures
//! needed by IFC viewers and analysis applications.

mod materials;
mod model;
mod parser;
mod relationships;
mod spatial;

pub use model::*;

use thiserror::Error;

#[cfg(feature = "python")]
use pyo3::{exceptions::PyRuntimeError, prelude::*, types::PyModule};
#[cfg(feature = "python")]
use pythonize::pythonize;

#[derive(Debug, Error)]
pub enum Error {
    #[error("invalid IFC: {0}")]
    InvalidIfc(String),
    #[error("failed to parse IFC entity #{express_id}: {message}")]
    ParseEntity { express_id: u32, message: String },
    #[error("failed to serialize IFC relationship data: {0}")]
    Serialize(#[from] serde_json::Error),
}

pub fn analyze_ifc(ifc_bytes: &[u8]) -> Result<ModelData, Error> {
    let parsed = parser::parse_model(ifc_bytes)?;
    let relations = relationships::extract_relations(&parsed);
    let spatial = spatial::build_spatial(&parsed, &relations);
    let materials = materials::build_materials(&parsed, &relations);
    Ok(ModelData {
        schema: parsed.schema,
        entity_count: parsed.entity_types.len(),
        length_unit_scale: parsed.length_unit_scale,
        relationships: relations.edges,
        spatial,
        materials,
    })
}

#[cfg(feature = "python")]
#[pyfunction]
fn model_data(py: Python<'_>, ifc_bytes: Vec<u8>) -> PyResult<Py<PyAny>> {
    let data = py
        .detach(|| analyze_ifc(&ifc_bytes))
        .map_err(|error| PyRuntimeError::new_err(error.to_string()))?;
    pythonize(py, &data)
        .map(Bound::unbind)
        .map_err(|error| PyRuntimeError::new_err(error.to_string()))
}

#[cfg(feature = "python")]
#[pyfunction]
fn model_data_json(py: Python<'_>, ifc_bytes: Vec<u8>) -> PyResult<String> {
    py.detach(|| {
        let data = analyze_ifc(&ifc_bytes).map_err(|error| error.to_string())?;
        serde_json::to_string(&data).map_err(|error| error.to_string())
    })
    .map_err(PyRuntimeError::new_err)
}

#[cfg(feature = "python")]
#[pymodule]
fn ifcx_core(module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add_function(wrap_pyfunction!(model_data, module)?)?;
    module.add_function(wrap_pyfunction!(model_data_json, module)?)?;
    module.add("__version__", env!("CARGO_PKG_VERSION"))?;
    module.add(
        "__doc__",
        "Native IFC spatial and material relationships, complementing ifclite-geom.",
    )?;
    Ok(())
}
