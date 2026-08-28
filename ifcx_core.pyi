# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from __future__ import annotations

from typing import TypedDict


class RelationshipEdge(TypedDict):
    relationship_id: int
    relationship_type: str
    relating_id: int
    related_id: int


class RelationshipData(TypedDict):
    edges: list[RelationshipEdge]


class SpatialNode(TypedDict):
    express_id: int
    ifc_type: str
    global_id: str | None
    name: str
    long_name: str | None
    elevation: float | None
    children: list[SpatialNode]
    elements: list[int]
    referenced_elements: list[int]


class SpatialData(TypedDict):
    project_id: int | None
    roots: list[SpatialNode]
    orphan_spatial_ids: list[int]
    by_storey: dict[int, list[int]]
    by_building: dict[int, list[int]]
    by_site: dict[int, list[int]]
    by_space: dict[int, list[int]]
    storey_elevations: dict[int, float]
    element_to_storey: dict[int, int]
    element_to_container: dict[int, int]
    referenced_by_structure: dict[int, list[int]]


class MaterialAssociation(TypedDict):
    relationship_id: int
    relating_material_id: int
    related_objects: list[int]


class MaterialLayer(TypedDict):
    express_id: int
    material_id: int | None
    material_name: str | None
    material_category: str | None
    thickness: float | None
    is_ventilated: bool | None
    name: str | None
    description: str | None
    category: str | None
    priority: float | None


class MaterialProfile(TypedDict):
    express_id: int
    material_id: int | None
    material_name: str | None
    material_category: str | None
    profile_id: int | None
    name: str | None
    description: str | None
    category: str | None
    priority: float | None


class MaterialConstituent(TypedDict):
    express_id: int
    material_id: int | None
    material_name: str | None
    material_category: str | None
    name: str | None
    description: str | None
    fraction: float | None
    category: str | None


class MaterialLeaf(TypedDict):
    express_id: int
    name: str
    category: str | None


class ResolvedMaterial(TypedDict):
    source_definition_id: int
    resolved_definition_id: int
    material_type: str
    name: str | None
    description: str | None
    category: str | None
    layers: list[MaterialLayer]
    profiles: list[MaterialProfile]
    constituents: list[MaterialConstituent]
    materials: list[MaterialLeaf]


class ElementMaterialAssignment(TypedDict):
    definition_id: int
    inherited_from_type: int | None
    material: ResolvedMaterial


class MaterialsData(TypedDict):
    associations: list[MaterialAssociation]
    definitions: dict[int, ResolvedMaterial]
    element_materials: dict[int, list[ElementMaterialAssignment]]


class ModelData(TypedDict):
    schema: str | None
    entity_count: int
    length_unit_scale: float
    relationships: RelationshipData
    spatial: SpatialData
    materials: MaterialsData

__version__: str

def model_data(ifc_bytes: bytes) -> ModelData: ...
def model_data_json(ifc_bytes: bytes) -> str: ...
