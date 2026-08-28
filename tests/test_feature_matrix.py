# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from __future__ import annotations

import json
from collections import defaultdict, deque
from typing import Any

import pytest

import ifcx_core

ifcopenshell = pytest.importorskip("ifcopenshell")
from ifcopenshell.util.element import get_container, get_material, get_materials
from ifcopenshell.util.placement import get_storey_elevation
from ifcopenshell.util.unit import calculate_unit_scale

from ifc_fixtures import as_bytes, material_model, spatial_model


RELATIONSHIP_ATTRIBUTES = {
    "IfcRelAggregates": ("RelatingObject", "RelatedObjects"),
    "IfcRelNests": ("RelatingObject", "RelatedObjects"),
    "IfcRelContainedInSpatialStructure": ("RelatingStructure", "RelatedElements"),
    "IfcRelReferencedInSpatialStructure": ("RelatingStructure", "RelatedElements"),
    "IfcRelDefinesByType": ("RelatingType", "RelatedObjects"),
    "IfcRelAssociatesMaterial": ("RelatingMaterial", "RelatedObjects"),
}

MATERIAL_DEFINITION_TYPES = {
    "IfcMaterial",
    "IfcMaterialLayerSet",
    "IfcMaterialLayerSetUsage",
    "IfcMaterialProfileSet",
    "IfcMaterialProfileSetUsage",
    "IfcMaterialConstituentSet",
    "IfcMaterialList",
}


def oracle_edges(model: Any) -> set[tuple[int, str, int, int]]:
    return {
        (relationship.id(), relation_type, getattr(relationship, relating_attr).id(), related.id())
        for relation_type, (relating_attr, related_attr) in RELATIONSHIP_ATTRIBUTES.items()
        for relationship in model.by_type(relation_type)
        for related in getattr(relationship, related_attr)
    }


def actual_edges(data: dict[str, Any]) -> set[tuple[int, str, int, int]]:
    return {
        (
            edge["relationship_id"],
            edge["relationship_type"],
            edge["relating_id"],
            edge["related_id"],
        )
        for edge in data["relationships"]["edges"]
    }


def flatten_spatial(nodes: list[dict[str, Any]]) -> dict[int, dict[str, Any]]:
    flattened: dict[int, dict[str, Any]] = {}
    pending = list(nodes)
    while pending:
        node = pending.pop()
        flattened[node["express_id"]] = node
        pending.extend(node["children"])
    return flattened


def json_compatible(value: Any) -> Any:
    """Apply JSON's string-key rule to the native Python representation."""

    if isinstance(value, dict):
        return {str(key) if isinstance(key, int) else key: json_compatible(item) for key, item in value.items()}
    if isinstance(value, list):
        return [json_compatible(item) for item in value]
    return value


def is_spatial(entity: Any) -> bool:
    return entity.is_a("IfcSpatialElement") or entity.is_a() == "IfcProject"


def spatial_oracle(model: Any, project_id: int) -> tuple[dict[int, set[int]], set[int]]:
    children: dict[int, set[int]] = defaultdict(set)
    for relationship in model.by_type("IfcRelAggregates"):
        for related in relationship.RelatedObjects:
            if is_spatial(related) and related.is_a() != "IfcProject":
                children[relationship.RelatingObject.id()].add(related.id())
    for relationship in model.by_type("IfcRelContainedInSpatialStructure"):
        for related in relationship.RelatedElements:
            if is_spatial(related) and related.is_a() != "IfcProject":
                children[relationship.RelatingStructure.id()].add(related.id())

    attached = {project_id}
    pending = deque([project_id])
    while pending:
        for child_id in children[pending.popleft()]:
            if child_id not in attached:
                attached.add(child_id)
                pending.append(child_id)
    return children, attached


def direct_elements(model: Any, structure: Any) -> list[int]:
    return sorted(
        element.id()
        for relationship in model.by_type("IfcRelContainedInSpatialStructure")
        if relationship.RelatingStructure == structure
        for element in relationship.RelatedElements
        if not is_spatial(element)
    )


def referenced_elements(model: Any, structure: Any) -> list[int]:
    return sorted(
        element.id()
        for relationship in model.by_type("IfcRelReferencedInSpatialStructure")
        if relationship.RelatingStructure == structure
        for element in relationship.RelatedElements
    )


def reference_oracle(model: Any) -> dict[int, list[int]]:
    result: dict[int, list[int]] = defaultdict(list)
    for relationship in model.by_type("IfcRelReferencedInSpatialStructure"):
        result[relationship.RelatingStructure.id()].extend(
            element.id() for element in relationship.RelatedElements
        )
    return {key: sorted(set(values)) for key, values in result.items()}


@pytest.mark.parametrize(("schema", "expected_schema"), [("IFC4", "IFC4"), ("IFC4X3", "IFC4X3")])
@pytest.mark.parametrize(("prefix", "scale"), [(None, 1.0), ("MILLI", 0.001)])
def test_spatial_feature_matrix_matches_ifcopenshell(
    schema: str, expected_schema: str, prefix: str | None, scale: float
) -> None:
    model, handles = spatial_model(schema, prefix)
    data = ifcx_core.model_data(as_bytes(model))
    spatial = data["spatial"]
    project_id = handles["project"].id()

    assert data["schema"] == expected_schema
    assert data["entity_count"] == len(list(model))
    assert data["length_unit_scale"] == pytest.approx(calculate_unit_scale(model))
    assert data["length_unit_scale"] == pytest.approx(scale)
    assert actual_edges(data) == oracle_edges(model)

    expected_children, attached = spatial_oracle(model, project_id)
    nodes = flatten_spatial(spatial["roots"])
    assert set(nodes) == attached
    assert spatial["project_id"] == project_id
    assert spatial["referenced_by_structure"] == reference_oracle(model)

    all_spatial_ids = {entity.id() for entity in model if is_spatial(entity)}
    assert spatial["orphan_spatial_ids"] == sorted(all_spatial_ids - attached)

    for express_id, node in nodes.items():
        entity = model.by_id(express_id)
        assert node["ifc_type"] == entity.is_a()
        assert node["global_id"] == getattr(entity, "GlobalId", None)
        assert node["name"] == (entity.Name or getattr(entity, "LongName", None) or f"Entity #{express_id}")
        expected_long_name = getattr(entity, "LongName", None)
        if expected_long_name == node["name"]:
            expected_long_name = None
        assert node["long_name"] == expected_long_name
        assert [child["express_id"] for child in node["children"]] == sorted(
            expected_children[express_id]
        )
        assert node["elements"] == direct_elements(model, entity)
        assert node["referenced_elements"] == referenced_elements(model, entity)

    for storey in model.by_type("IfcBuildingStorey"):
        if storey.id() in attached:
            expected = get_storey_elevation(storey) * calculate_unit_scale(model)
            assert spatial["storey_elevations"][storey.id()] == pytest.approx(expected)

    category_maps = {
        "by_site": {"IfcSite"},
        "by_building": {
            "IfcBuilding",
            "IfcFacility",
            "IfcBridge",
            "IfcRoad",
            "IfcRailway",
            "IfcMarineFacility",
        },
        "by_storey": {"IfcBuildingStorey"},
        "by_space": {"IfcSpace", "IfcSpatialZone"},
    }
    for output_name, ifc_types in category_maps.items():
        expected = {
            entity.id(): direct_elements(model, entity)
            for entity in model
            if entity.id() in attached and entity.is_a() in ifc_types
        }
        assert spatial[output_name] == expected

    for element_id, container_id in spatial["element_to_container"].items():
        oracle = get_container(model.by_id(element_id))
        assert oracle is not None
        assert oracle.id() == container_id
    for element_id, storey_id in spatial["element_to_storey"].items():
        entity = model.by_id(element_id)
        if is_spatial(entity):
            decomposes = getattr(entity, "Decomposes", ())
            oracle = decomposes[0].RelatingObject if decomposes else None
        else:
            oracle = get_container(entity)
        while oracle is not None and not oracle.is_a("IfcBuildingStorey"):
            decomposes = getattr(oracle, "Decomposes", ())
            oracle = decomposes[0].RelatingObject if decomposes else get_container(oracle)
        assert oracle is not None
        assert oracle.id() == storey_id


def expected_material(definition: Any, scale: float, source_id: int | None = None) -> dict[str, Any]:
    if definition.is_a() == "IfcMaterialLayerSetUsage":
        return expected_material(definition.ForLayerSet, scale, definition.id())
    if definition.is_a() == "IfcMaterialProfileSetUsage":
        return expected_material(definition.ForProfileSet, scale, definition.id())

    result: dict[str, Any] = {
        "source_definition_id": source_id or definition.id(),
        "resolved_definition_id": definition.id(),
        "material_type": definition.is_a().removeprefix("Ifc"),
        "name": None,
        "description": None,
        "category": None,
        "layers": [],
        "profiles": [],
        "constituents": [],
        "materials": [],
    }
    if definition.is_a() == "IfcMaterial":
        result.update(
            name=definition.Name,
            description=definition.Description,
            category=definition.Category,
        )
    elif definition.is_a() == "IfcMaterialLayerSet":
        result.update(name=definition.LayerSetName, description=definition.Description)
        result["layers"] = [
            {
                "express_id": layer.id(),
                "material_id": layer.Material.id() if layer.Material else None,
                "material_name": layer.Material.Name if layer.Material else None,
                "material_category": layer.Material.Category if layer.Material else None,
                "thickness": layer.LayerThickness * scale,
                "is_ventilated": layer.IsVentilated,
                "name": layer.Name,
                "description": layer.Description,
                "category": layer.Category,
                "priority": layer.Priority,
            }
            for layer in definition.MaterialLayers
        ]
    elif definition.is_a() == "IfcMaterialProfileSet":
        result.update(name=definition.Name, description=definition.Description)
        result["profiles"] = [
            {
                "express_id": profile.id(),
                "material_id": profile.Material.id() if profile.Material else None,
                "material_name": profile.Material.Name if profile.Material else None,
                "material_category": profile.Material.Category if profile.Material else None,
                "profile_id": profile.Profile.id() if profile.Profile else None,
                "name": profile.Name,
                "description": profile.Description,
                "category": profile.Category,
                "priority": profile.Priority,
            }
            for profile in definition.MaterialProfiles
        ]
    elif definition.is_a() == "IfcMaterialConstituentSet":
        result.update(name=definition.Name, description=definition.Description)
        result["constituents"] = [
            {
                "express_id": constituent.id(),
                "material_id": constituent.Material.id() if constituent.Material else None,
                "material_name": constituent.Material.Name if constituent.Material else None,
                "material_category": constituent.Material.Category if constituent.Material else None,
                "name": constituent.Name,
                "description": constituent.Description,
                "fraction": constituent.Fraction,
                "category": constituent.Category,
            }
            for constituent in definition.MaterialConstituents
        ]
    elif definition.is_a() == "IfcMaterialList":
        result["materials"] = [
            {
                "express_id": material.id(),
                "name": material.Name or f"Material #{material.id()}",
                "category": material.Category,
            }
            for material in definition.Materials
        ]
    else:  # pragma: no cover - the test's supported-type set controls this
        raise AssertionError(definition.is_a())
    return result


def material_leaf_ids(material: dict[str, Any]) -> list[int]:
    if material["material_type"] == "Material":
        return [material["resolved_definition_id"]]
    if material["material_type"] == "MaterialLayerSet":
        return [item["material_id"] for item in material["layers"] if item["material_id"]]
    if material["material_type"] == "MaterialProfileSet":
        return [item["material_id"] for item in material["profiles"] if item["material_id"]]
    if material["material_type"] == "MaterialConstituentSet":
        return [item["material_id"] for item in material["constituents"] if item["material_id"]]
    if material["material_type"] == "MaterialList":
        return [item["express_id"] for item in material["materials"]]
    raise AssertionError(material["material_type"])


@pytest.mark.parametrize("schema", ["IFC4", "IFC4X3"])
def test_material_feature_matrix_matches_ifcopenshell(schema: str) -> None:
    model, handles = material_model(schema)
    source = as_bytes(model)
    data = ifcx_core.model_data(source)
    materials = data["materials"]
    scale = calculate_unit_scale(model)

    assert actual_edges(data) == oracle_edges(model)

    expected_definition_ids = {
        entity.id() for entity in model if entity.is_a() in MATERIAL_DEFINITION_TYPES
    }
    assert set(materials["definitions"]) == expected_definition_ids
    for definition_id, actual in materials["definitions"].items():
        assert actual == expected_material(model.by_id(definition_id), scale)

    expected_associations = [
        {
            "relationship_id": relationship.id(),
            "relating_material_id": relationship.RelatingMaterial.id(),
            "related_objects": [entity.id() for entity in relationship.RelatedObjects],
        }
        for relationship in sorted(
            model.by_type("IfcRelAssociatesMaterial"), key=lambda entity: entity.id()
        )
    ]
    assert materials["associations"] == expected_associations

    # IfcOpenShell is the semantic oracle whenever an element has one effective
    # assignment. Multiple direct associations are checked independently below.
    multiple_id = handles["multiple"].id()
    for element_id, assignments in materials["element_materials"].items():
        if element_id == multiple_id:
            continue
        element = model.by_id(element_id)
        oracle = get_material(element, should_skip_usage=False, should_inherit=True)
        assert oracle is not None
        assert len(assignments) == 1
        assert assignments[0]["definition_id"] == oracle.id()
        assert material_leaf_ids(assignments[0]["material"]) == [
            material.id() for material in get_materials(element)
        ]

    multiple = materials["element_materials"][multiple_id]
    assert [assignment["definition_id"] for assignment in multiple] == [
        handles["steel"].id(),
        handles["concrete"].id(),
    ]
    assert all(assignment["inherited_from_type"] is None for assignment in multiple)

    inherited = materials["element_materials"][handles["elements"][7].id()][0]
    assert inherited["definition_id"] == handles["insulation"].id()
    assert inherited["inherited_from_type"] == handles["wall_type"].id()

    assert json.loads(ifcx_core.model_data_json(source)) == json_compatible(data)
    assert ifcx_core.model_data(source) == data


def test_ifc2x3_is_explicitly_rejected() -> None:
    model = ifcopenshell.file(schema="IFC2X3")
    model.create_entity("IfcProject", GlobalId=ifcopenshell.guid.new(), Name="Unsupported")
    with pytest.raises(RuntimeError, match="expected IFC4 or IFC4X3"):
        ifcx_core.model_data(as_bytes(model))
