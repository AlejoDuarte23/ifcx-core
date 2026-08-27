// This Source Code Form is subject to the terms of the Mozilla Public
// License, v. 2.0. If a copy of the MPL was not distributed with this
// file, You can obtain one at https://mozilla.org/MPL/2.0/.

use std::collections::BTreeMap;

use crate::{
    model::{MaterialAssociation, RelationshipData, RelationshipEdge},
    parser::{reference, refs, EntityRecord, ParsedModel},
};

#[derive(Debug, Clone, Default)]
pub(crate) struct Relations {
    pub edges: RelationshipData,
    pub aggregates: BTreeMap<u32, Vec<u32>>,
    pub contains: BTreeMap<u32, Vec<u32>>,
    pub references: BTreeMap<u32, Vec<u32>>,
    pub defines_type: BTreeMap<u32, Vec<(u32, u32)>>,
    pub material_associations: Vec<MaterialAssociation>,
}

pub(crate) fn extract_relations(model: &ParsedModel) -> Relations {
    let mut out = Relations::default();

    for record in model.records.values() {
        let upper = model
            .entity_types
            .get(&record.id)
            .map(String::as_str)
            .unwrap_or_default();
        match upper {
            "IFCRELAGGREGATES" | "IFCRELNESTS" => {
                add_single_to_many(record, upper, 4, 5, &mut out.aggregates, &mut out.edges)
            }
            "IFCRELCONTAINEDINSPATIALSTRUCTURE" => {
                add_many_to_single(record, upper, 4, 5, &mut out.contains, &mut out.edges)
            }
            "IFCRELREFERENCEDINSPATIALSTRUCTURE" => {
                add_many_to_single(record, upper, 4, 5, &mut out.references, &mut out.edges)
            }
            "IFCRELDEFINESBYTYPE" => {
                let targets = refs(record.attributes.get(4));
                if let Some(type_id) = reference(record.attributes.get(5)) {
                    for target in targets {
                        out.defines_type
                            .entry(target)
                            .or_default()
                            .push((record.id, type_id));
                        out.edges.edges.push(edge(record, upper, type_id, target));
                    }
                }
            }
            "IFCRELASSOCIATESMATERIAL" => {
                let related_objects = refs(record.attributes.get(4));
                if let Some(material_id) = reference(record.attributes.get(5)) {
                    for target in &related_objects {
                        out.edges
                            .edges
                            .push(edge(record, upper, material_id, *target));
                    }
                    out.material_associations.push(MaterialAssociation {
                        relationship_id: record.id,
                        relating_material_id: material_id,
                        related_objects,
                    });
                }
            }
            _ => {}
        }
    }

    for values in out.aggregates.values_mut() {
        values.sort_unstable();
        values.dedup();
    }
    for values in out.contains.values_mut() {
        values.sort_unstable();
        values.dedup();
    }
    for values in out.references.values_mut() {
        values.sort_unstable();
        values.dedup();
    }
    for values in out.defines_type.values_mut() {
        values.sort_unstable_by_key(|(relationship_id, _)| *relationship_id);
        values.dedup();
    }
    out.material_associations
        .sort_unstable_by_key(|association| association.relationship_id);
    out.edges
        .edges
        .sort_unstable_by_key(|item| (item.relationship_id, item.relating_id, item.related_id));
    out
}

fn add_single_to_many(
    record: &EntityRecord,
    type_upper: &str,
    relating_index: usize,
    related_index: usize,
    adjacency: &mut BTreeMap<u32, Vec<u32>>,
    edges: &mut RelationshipData,
) {
    let Some(relating) = reference(record.attributes.get(relating_index)) else {
        return;
    };
    for related in refs(record.attributes.get(related_index)) {
        adjacency.entry(relating).or_default().push(related);
        edges
            .edges
            .push(edge(record, type_upper, relating, related));
    }
}

fn add_many_to_single(
    record: &EntityRecord,
    type_upper: &str,
    related_index: usize,
    relating_index: usize,
    adjacency: &mut BTreeMap<u32, Vec<u32>>,
    edges: &mut RelationshipData,
) {
    let Some(relating) = reference(record.attributes.get(relating_index)) else {
        return;
    };
    for related in refs(record.attributes.get(related_index)) {
        adjacency.entry(relating).or_default().push(related);
        edges
            .edges
            .push(edge(record, type_upper, relating, related));
    }
}

fn edge(
    record: &EntityRecord,
    type_upper: &str,
    relating_id: u32,
    related_id: u32,
) -> RelationshipEdge {
    RelationshipEdge {
        relationship_id: record.id,
        relationship_type: canonical_relationship_type(type_upper).to_string(),
        relating_id,
        related_id,
    }
}

fn canonical_relationship_type(type_upper: &str) -> &str {
    match type_upper {
        "IFCRELAGGREGATES" => "IfcRelAggregates",
        "IFCRELNESTS" => "IfcRelNests",
        "IFCRELCONTAINEDINSPATIALSTRUCTURE" => "IfcRelContainedInSpatialStructure",
        "IFCRELREFERENCEDINSPATIALSTRUCTURE" => "IfcRelReferencedInSpatialStructure",
        "IFCRELDEFINESBYTYPE" => "IfcRelDefinesByType",
        "IFCRELASSOCIATESMATERIAL" => "IfcRelAssociatesMaterial",
        _ => "IfcRelationship",
    }
}
