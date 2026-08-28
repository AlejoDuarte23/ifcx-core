# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from __future__ import annotations

import hashlib
import os
from collections import defaultdict
from pathlib import Path
from typing import Any

import pytest

import ifcx_core

ifcopenshell = pytest.importorskip("ifcopenshell")
from ifcopenshell.util.element import get_container, get_material, get_materials
from ifcopenshell.util.unit import calculate_unit_scale


EXPECTED_FIXTURE_SHA256 = "4f0bebf282ffed5a29c8f129995945950286b5294ab58f0b39723e0ecca4107f"


def fixture_path() -> Path:
    configured = os.environ.get("IFCX_PARITY_MODEL")
    if not configured:
        pytest.skip("set IFCX_PARITY_MODEL to the requested IFC comparison fixture")
    path = Path(configured)
    if not path.is_file():
        pytest.skip("set IFCX_PARITY_MODEL to the requested IFC comparison fixture")
    return path


@pytest.fixture(scope="module")
def compared() -> tuple[Any, dict[str, Any]]:
    path = fixture_path()
    source = path.read_bytes()
    assert hashlib.sha256(source).hexdigest() == EXPECTED_FIXTURE_SHA256
    return ifcopenshell.open(path), ifcx_core.model_data(source)


def oracle_edges(model: Any, relation_type: str) -> set[tuple[int, int, int]]:
    if relation_type in {"IfcRelAggregates", "IfcRelNests"}:
        relating_attr, related_attr = "RelatingObject", "RelatedObjects"
    elif relation_type in {
        "IfcRelContainedInSpatialStructure",
        "IfcRelReferencedInSpatialStructure",
    }:
        relating_attr, related_attr = "RelatingStructure", "RelatedElements"
    elif relation_type == "IfcRelDefinesByType":
        relating_attr, related_attr = "RelatingType", "RelatedObjects"
    elif relation_type == "IfcRelAssociatesMaterial":
        relating_attr, related_attr = "RelatingMaterial", "RelatedObjects"
    else:  # pragma: no cover - test table controls the values
        raise AssertionError(relation_type)

    return {
        (relationship.id(), getattr(relationship, relating_attr).id(), related.id())
        for relationship in model.by_type(relation_type)
        for related in getattr(relationship, related_attr)
    }


@pytest.mark.integration
def test_relationship_edges_exactly_match_ifcopenshell(compared: tuple[Any, dict[str, Any]]) -> None:
    model, data = compared
    ours: dict[str, set[tuple[int, int, int]]] = defaultdict(set)
    for edge in data["relationships"]["edges"]:
        ours[edge["relationship_type"]].add(
            (edge["relationship_id"], edge["relating_id"], edge["related_id"])
        )

    for relation_type in (
        "IfcRelAggregates",
        "IfcRelNests",
        "IfcRelContainedInSpatialStructure",
        "IfcRelReferencedInSpatialStructure",
        "IfcRelDefinesByType",
        "IfcRelAssociatesMaterial",
    ):
        assert ours[relation_type] == oracle_edges(model, relation_type)


@pytest.mark.integration
def test_spatial_results_match_ifcopenshell(compared: tuple[Any, dict[str, Any]]) -> None:
    model, data = compared
    spatial = data["spatial"]
    assert data["schema"] == "IFC4"
    assert data["entity_count"] == len(list(model))
    assert data["length_unit_scale"] == pytest.approx(calculate_unit_scale(model))
    assert spatial["project_id"] == model.by_type("IfcProject")[0].id()
    assert spatial["orphan_spatial_ids"] == []

    map_by_type = {
        "IfcSite": spatial["by_site"],
        "IfcBuilding": spatial["by_building"],
        "IfcBuildingStorey": spatial["by_storey"],
        "IfcSpace": spatial["by_space"],
    }
    for ifc_type, actual in map_by_type.items():
        expected: dict[int, list[int]] = {}
        for structure in model.by_type(ifc_type):
            direct = sorted(
                element.id()
                for relationship in getattr(structure, "ContainsElements", ())
                for element in relationship.RelatedElements
                if not element.is_a("IfcSpatialElement")
            )
            expected[structure.id()] = direct
        assert actual == expected

    # IFClite-compatible reverse maps intentionally cover direct containment
    # plus aggregate/nest descendants. IfcOpenShell additionally resolves
    # opening/filling ancestry; every mapping we emit must agree with its more
    # expansive get_container oracle.
    for element_id, container_id in spatial["element_to_container"].items():
        element = model.by_id(element_id)
        if not element or not element.is_a("IfcElement"):
            continue
        oracle = get_container(element)
        assert oracle is not None
        assert oracle.id() == container_id


def resolved_leaf_ids(material: dict[str, Any]) -> list[int]:
    material_type = material["material_type"]
    if material_type == "Material":
        return [material["resolved_definition_id"]]
    if material_type == "MaterialLayerSet":
        return [item["material_id"] for item in material["layers"] if item["material_id"]]
    if material_type == "MaterialProfileSet":
        return [item["material_id"] for item in material["profiles"] if item["material_id"]]
    if material_type == "MaterialConstituentSet":
        return [item["material_id"] for item in material["constituents"] if item["material_id"]]
    if material_type == "MaterialList":
        return [item["express_id"] for item in material["materials"]]
    raise AssertionError(material_type)


@pytest.mark.integration
def test_material_resolution_matches_ifcopenshell(compared: tuple[Any, dict[str, Any]]) -> None:
    model, data = compared
    assignments = data["materials"]["element_materials"]
    oracle_assigned = {
        element.id(): get_material(element, should_skip_usage=False, should_inherit=True)
        for element in model.by_type("IfcElement")
    }
    oracle_assigned = {key: value for key, value in oracle_assigned.items() if value is not None}

    assert set(assignments) == set(oracle_assigned)
    for element_id, oracle_material in oracle_assigned.items():
        actual = assignments[element_id]
        assert actual[0]["definition_id"] == oracle_material.id()
        assert resolved_leaf_ids(actual[0]["material"]) == [
            material.id() for material in get_materials(model.by_id(element_id))
        ]
