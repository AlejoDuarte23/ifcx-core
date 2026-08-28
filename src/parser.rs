// This Source Code Form is subject to the terms of the Mozilla Public
// License, v. 2.0. If a copy of the MPL was not distributed with this
// file, You can obtain one at https://mozilla.org/MPL/2.0/.

use std::{collections::BTreeMap, sync::Arc};

use ifc_lite_core::{
    build_entity_index, try_extract_length_unit_scale, AttributeValue, DecodedEntity,
    EntityDecoder, EntityScanner,
};

use crate::Error;

#[derive(Debug, Clone)]
pub(crate) struct EntityRecord {
    pub id: u32,
    pub ifc_type: String,
    pub attributes: Arc<Vec<AttributeValue>>,
}

#[derive(Debug)]
pub(crate) struct ParsedModel {
    pub schema: Option<String>,
    pub entity_types: BTreeMap<u32, String>,
    pub records: BTreeMap<u32, EntityRecord>,
    pub project_ids: Vec<u32>,
    pub length_unit_scale: f64,
}

pub(crate) fn parse_model(bytes: &[u8]) -> Result<ParsedModel, Error> {
    let schema = detect_schema(bytes);
    if !matches!(schema.as_deref(), Some("IFC4" | "IFC4X3")) {
        return Err(Error::InvalidIfc(
            "unsupported or missing schema; expected IFC4 or IFC4X3".to_string(),
        ));
    }

    let mut entity_types = BTreeMap::new();
    let mut relevant_ids = Vec::new();
    let mut project_ids = Vec::new();
    let mut scanner = EntityScanner::new(bytes);

    while let Some((id, type_name, _, _)) = scanner.next_entity() {
        let upper = type_name.to_ascii_uppercase();
        if upper == "IFCPROJECT" {
            project_ids.push(id);
        }
        if is_relevant_type(&upper) {
            relevant_ids.push(id);
        }
        entity_types.insert(id, upper);
    }

    if entity_types.is_empty() {
        return Err(Error::InvalidIfc("no STEP entities found".to_string()));
    }
    if project_ids.is_empty() {
        return Err(Error::InvalidIfc("no IfcProject found".to_string()));
    }

    let index = build_entity_index(bytes);
    let mut decoder = EntityDecoder::with_index(bytes, index);
    let length_unit_scale = project_ids
        .first()
        .and_then(|id| try_extract_length_unit_scale(&mut decoder, *id))
        .unwrap_or(1.0);

    let mut records = BTreeMap::new();
    for id in relevant_ids {
        let entity = decoder
            .decode_by_id(id)
            .map_err(|error| Error::ParseEntity {
                express_id: id,
                message: error.to_string(),
            })?;
        records.insert(id, record_from_entity(entity));
    }

    // Decode only the short placement chain needed for the storey-elevation
    // fallback. Parsing every CartesianPoint would pull the model's complete
    // geometry coordinate population into this relationship-only library.
    let storey_ids: Vec<u32> = entity_types
        .iter()
        .filter_map(|(id, type_name)| (type_name == "IFCBUILDINGSTOREY").then_some(*id))
        .collect();
    for storey_id in storey_ids {
        let placement_id = records
            .get(&storey_id)
            .and_then(|record| reference(record.attributes.get(5)));
        let Some(placement_id) = placement_id else {
            continue;
        };
        decode_and_insert(&mut decoder, &mut records, placement_id)?;
        let axis_id = records
            .get(&placement_id)
            .and_then(|record| reference(record.attributes.get(1)));
        let Some(axis_id) = axis_id else { continue };
        decode_and_insert(&mut decoder, &mut records, axis_id)?;
        let location_id = records
            .get(&axis_id)
            .and_then(|record| reference(record.attributes.first()));
        let Some(location_id) = location_id else {
            continue;
        };
        decode_and_insert(&mut decoder, &mut records, location_id)?;
    }

    Ok(ParsedModel {
        schema,
        entity_types,
        records,
        project_ids,
        length_unit_scale,
    })
}

fn decode_and_insert(
    decoder: &mut EntityDecoder<'_>,
    records: &mut BTreeMap<u32, EntityRecord>,
    express_id: u32,
) -> Result<(), Error> {
    if records.contains_key(&express_id) {
        return Ok(());
    }
    let entity = decoder
        .decode_by_id(express_id)
        .map_err(|error| Error::ParseEntity {
            express_id,
            message: error.to_string(),
        })?;
    records.insert(express_id, record_from_entity(entity));
    Ok(())
}

fn record_from_entity(entity: DecodedEntity) -> EntityRecord {
    EntityRecord {
        id: entity.id,
        ifc_type: format!("{:?}", entity.ifc_type),
        attributes: entity.attributes,
    }
}

fn is_relevant_type(type_upper: &str) -> bool {
    is_spatial_type(type_upper)
        || matches!(
            type_upper,
            "IFCRELAGGREGATES"
                | "IFCRELNESTS"
                | "IFCRELCONTAINEDINSPATIALSTRUCTURE"
                | "IFCRELREFERENCEDINSPATIALSTRUCTURE"
                | "IFCRELDEFINESBYTYPE"
                | "IFCRELASSOCIATESMATERIAL"
                | "IFCMATERIAL"
                | "IFCMATERIALLAYER"
                | "IFCMATERIALLAYERSET"
                | "IFCMATERIALLAYERSETUSAGE"
                | "IFCMATERIALPROFILE"
                | "IFCMATERIALPROFILESET"
                | "IFCMATERIALPROFILESETUSAGE"
                | "IFCMATERIALCONSTITUENT"
                | "IFCMATERIALCONSTITUENTSET"
                | "IFCMATERIALLIST"
        )
}

pub(crate) fn is_spatial_type(type_upper: &str) -> bool {
    matches!(
        type_upper,
        "IFCPROJECT"
            | "IFCSITE"
            | "IFCBUILDING"
            | "IFCBUILDINGSTOREY"
            | "IFCSPACE"
            | "IFCSPATIALZONE"
            | "IFCFACILITY"
            | "IFCFACILITYPART"
            | "IFCFACILITYPARTCOMMON"
            | "IFCBRIDGE"
            | "IFCBRIDGEPART"
            | "IFCROAD"
            | "IFCROADPART"
            | "IFCRAILWAY"
            | "IFCRAILWAYPART"
            | "IFCMARINEFACILITY"
            | "IFCMARINEPART"
    )
}

pub(crate) fn refs(value: Option<&AttributeValue>) -> Vec<u32> {
    match value {
        Some(AttributeValue::EntityRef(id)) => vec![*id],
        Some(AttributeValue::List(values)) => values
            .iter()
            .filter_map(AttributeValue::as_entity_ref)
            .collect(),
        _ => Vec::new(),
    }
}

pub(crate) fn reference(value: Option<&AttributeValue>) -> Option<u32> {
    value.and_then(AttributeValue::as_entity_ref)
}

pub(crate) fn string(value: Option<&AttributeValue>) -> Option<String> {
    value
        .and_then(AttributeValue::as_string)
        .map(str::trim)
        .filter(|value| !value.is_empty())
        .map(ToOwned::to_owned)
}

pub(crate) fn number(value: Option<&AttributeValue>) -> Option<f64> {
    match value {
        Some(AttributeValue::Float(value)) => Some(*value),
        Some(AttributeValue::Integer(value)) => Some(*value as f64),
        Some(AttributeValue::List(values)) if values.len() >= 2 => number(values.get(1)),
        _ => None,
    }
}

pub(crate) fn boolean(value: Option<&AttributeValue>) -> Option<bool> {
    match value {
        Some(AttributeValue::Enum(value)) => match value.to_ascii_uppercase().as_str() {
            "T" | "TRUE" => Some(true),
            "F" | "FALSE" => Some(false),
            _ => None,
        },
        _ => None,
    }
}

fn detect_schema(bytes: &[u8]) -> Option<String> {
    let header_end = bytes
        .windows(b"ENDSEC;".len())
        .position(|window| window.eq_ignore_ascii_case(b"ENDSEC;"))
        .unwrap_or(bytes.len().min(64 * 1024));
    let header = String::from_utf8_lossy(&bytes[..header_end]).to_ascii_uppercase();
    if header.contains("IFC4X3") {
        Some("IFC4X3".to_string())
    } else if header.contains("IFC4") {
        Some("IFC4".to_string())
    } else if header.contains("IFC2X3") {
        Some("IFC2X3".to_string())
    } else {
        None
    }
}
