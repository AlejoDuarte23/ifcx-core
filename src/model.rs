// This Source Code Form is subject to the terms of the Mozilla Public
// License, v. 2.0. If a copy of the MPL was not distributed with this
// file, You can obtain one at https://mozilla.org/MPL/2.0/.

use std::collections::BTreeMap;

use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ModelData {
    pub schema: Option<String>,
    pub entity_count: usize,
    pub length_unit_scale: f64,
    pub relationships: RelationshipData,
    pub spatial: SpatialData,
    pub materials: MaterialsData,
}

#[derive(Debug, Clone, Default, PartialEq, Eq, Serialize, Deserialize)]
pub struct RelationshipData {
    pub edges: Vec<RelationshipEdge>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct RelationshipEdge {
    pub relationship_id: u32,
    pub relationship_type: String,
    pub relating_id: u32,
    pub related_id: u32,
}

#[derive(Debug, Clone, Default, PartialEq, Serialize, Deserialize)]
pub struct SpatialData {
    pub project_id: Option<u32>,
    pub roots: Vec<SpatialNode>,
    pub orphan_spatial_ids: Vec<u32>,
    pub by_storey: BTreeMap<u32, Vec<u32>>,
    pub by_building: BTreeMap<u32, Vec<u32>>,
    pub by_site: BTreeMap<u32, Vec<u32>>,
    pub by_space: BTreeMap<u32, Vec<u32>>,
    pub storey_elevations: BTreeMap<u32, f64>,
    pub element_to_storey: BTreeMap<u32, u32>,
    pub element_to_container: BTreeMap<u32, u32>,
    pub referenced_by_structure: BTreeMap<u32, Vec<u32>>,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct SpatialNode {
    pub express_id: u32,
    pub ifc_type: String,
    pub global_id: Option<String>,
    pub name: String,
    pub long_name: Option<String>,
    pub elevation: Option<f64>,
    pub children: Vec<SpatialNode>,
    pub elements: Vec<u32>,
    pub referenced_elements: Vec<u32>,
}

#[derive(Debug, Clone, Default, PartialEq, Serialize, Deserialize)]
pub struct MaterialsData {
    pub associations: Vec<MaterialAssociation>,
    pub definitions: BTreeMap<u32, ResolvedMaterial>,
    pub element_materials: BTreeMap<u32, Vec<ElementMaterialAssignment>>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct MaterialAssociation {
    pub relationship_id: u32,
    pub relating_material_id: u32,
    pub related_objects: Vec<u32>,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ElementMaterialAssignment {
    pub definition_id: u32,
    pub inherited_from_type: Option<u32>,
    pub material: ResolvedMaterial,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ResolvedMaterial {
    pub source_definition_id: u32,
    pub resolved_definition_id: u32,
    pub material_type: String,
    pub name: Option<String>,
    pub description: Option<String>,
    pub category: Option<String>,
    pub layers: Vec<MaterialLayer>,
    pub profiles: Vec<MaterialProfile>,
    pub constituents: Vec<MaterialConstituent>,
    pub materials: Vec<MaterialLeaf>,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct MaterialLayer {
    pub express_id: u32,
    pub material_id: Option<u32>,
    pub material_name: Option<String>,
    pub material_category: Option<String>,
    pub thickness: Option<f64>,
    pub is_ventilated: Option<bool>,
    pub name: Option<String>,
    pub description: Option<String>,
    pub category: Option<String>,
    pub priority: Option<f64>,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct MaterialProfile {
    pub express_id: u32,
    pub material_id: Option<u32>,
    pub material_name: Option<String>,
    pub material_category: Option<String>,
    pub profile_id: Option<u32>,
    pub name: Option<String>,
    pub description: Option<String>,
    pub category: Option<String>,
    pub priority: Option<f64>,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct MaterialConstituent {
    pub express_id: u32,
    pub material_id: Option<u32>,
    pub material_name: Option<String>,
    pub material_category: Option<String>,
    pub name: Option<String>,
    pub description: Option<String>,
    pub fraction: Option<f64>,
    pub category: Option<String>,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct MaterialLeaf {
    pub express_id: u32,
    pub name: String,
    pub category: Option<String>,
}
