# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from __future__ import annotations

from typing import Any

import ifcopenshell


def _guid() -> str:
    return ifcopenshell.guid.new()


def _root(model: Any, prefix: str | None) -> tuple[Any, Any]:
    length_unit = model.create_entity(
        "IfcSIUnit", UnitType="LENGTHUNIT", Prefix=prefix, Name="METRE"
    )
    units = model.create_entity("IfcUnitAssignment", Units=[length_unit])
    project = model.create_entity(
        "IfcProject", GlobalId=_guid(), Name="Test project", UnitsInContext=units
    )
    return project, length_unit


def _object(model: Any, ifc_class: str, name: str) -> Any:
    return model.create_entity(ifc_class, GlobalId=_guid(), Name=name)


def _rel(model: Any, ifc_class: str, **attributes: Any) -> Any:
    return model.create_entity(ifc_class, GlobalId=_guid(), **attributes)


def spatial_model(schema: str, prefix: str | None = "MILLI") -> tuple[Any, dict[str, Any]]:
    """Build a small schema-valid model covering every spatial relationship path."""

    model = ifcopenshell.file(schema=schema)
    project, _ = _root(model, prefix)
    site = _object(model, "IfcSite", "Campus")
    building = _object(model, "IfcBuilding", "Headquarters")
    building.LongName = "Main building"
    storey = _object(model, "IfcBuildingStorey", "Level 01")
    storey.Elevation = 3000.0 if prefix == "MILLI" else 3.0
    placed_storey = _object(model, "IfcBuildingStorey", "Level 02")
    z = 6000.0 if prefix == "MILLI" else 6.0
    point = model.create_entity("IfcCartesianPoint", Coordinates=[0.0, 0.0, z])
    axis = model.create_entity("IfcAxis2Placement3D", Location=point)
    placed_storey.ObjectPlacement = model.create_entity(
        "IfcLocalPlacement", RelativePlacement=axis
    )
    space = _object(model, "IfcSpace", "Room 101")
    zone = _object(model, "IfcSpatialZone", "Fire zone")
    orphan = _object(model, "IfcSpace", "Unattached room")

    wall = _object(model, "IfcWall", "External wall")
    wall_part = _object(model, "IfcBuildingElementPart", "Aggregated leaf")
    nested_part = _object(model, "IfcBuildingElementPart", "Nested leaf")
    furniture = _object(model, "IfcFurniture", "Desk")
    zone_element = _object(model, "IfcFurnishingElement", "Zone equipment")
    wall_type = _object(model, "IfcWallType", "External wall type")

    _rel(model, "IfcRelAggregates", RelatingObject=project, RelatedObjects=[site])
    _rel(model, "IfcRelAggregates", RelatingObject=site, RelatedObjects=[building])
    _rel(
        model,
        "IfcRelAggregates",
        RelatingObject=building,
        RelatedObjects=[storey, placed_storey],
    )
    _rel(model, "IfcRelAggregates", RelatingObject=storey, RelatedObjects=[space, zone])
    _rel(model, "IfcRelAggregates", RelatingObject=wall, RelatedObjects=[wall_part])
    _rel(model, "IfcRelNests", RelatingObject=wall, RelatedObjects=[nested_part])
    _rel(
        model,
        "IfcRelContainedInSpatialStructure",
        RelatedElements=[wall],
        RelatingStructure=storey,
    )
    _rel(
        model,
        "IfcRelContainedInSpatialStructure",
        RelatedElements=[furniture],
        RelatingStructure=space,
    )
    _rel(
        model,
        "IfcRelContainedInSpatialStructure",
        RelatedElements=[zone_element],
        RelatingStructure=zone,
    )
    _rel(
        model,
        "IfcRelReferencedInSpatialStructure",
        RelatedElements=[furniture],
        RelatingStructure=storey,
    )
    _rel(model, "IfcRelDefinesByType", RelatedObjects=[wall], RelatingType=wall_type)

    handles = {
        "project": project,
        "site": site,
        "building": building,
        "storey": storey,
        "placed_storey": placed_storey,
        "space": space,
        "zone": zone,
        "orphan": orphan,
        "wall": wall,
        "wall_part": wall_part,
        "nested_part": nested_part,
        "furniture": furniture,
        "zone_element": zone_element,
    }

    if schema == "IFC4X3":
        facility_specs = [
            ("IfcFacility", ["IfcFacilityPart", "IfcFacilityPartCommon"]),
            ("IfcBridge", ["IfcBridgePart"]),
            ("IfcRoad", ["IfcRoadPart"]),
            ("IfcRailway", ["IfcRailwayPart"]),
            ("IfcMarineFacility", ["IfcMarinePart"]),
        ]
        for facility_class, part_classes in facility_specs:
            facility = _object(model, facility_class, f"Test {facility_class}")
            facility.CompositionType = "ELEMENT"
            parts = []
            for part_class in part_classes:
                part = _object(model, part_class, f"Test {part_class}")
                part.CompositionType = "ELEMENT"
                part.UsageType = "LONGITUDINAL"
                parts.append(part)
                handles[part_class] = part
            facility_element = _object(
                model, "IfcBuildingElementProxy", f"Element in {facility_class}"
            )
            _rel(model, "IfcRelAggregates", RelatingObject=project, RelatedObjects=[facility])
            _rel(model, "IfcRelAggregates", RelatingObject=facility, RelatedObjects=parts)
            _rel(
                model,
                "IfcRelContainedInSpatialStructure",
                RelatedElements=[facility_element],
                RelatingStructure=facility,
            )
            handles[facility_class] = facility
            handles[f"{facility_class}_element"] = facility_element

    return model, handles


def material_model(schema: str = "IFC4") -> tuple[Any, dict[str, Any]]:
    """Build all currently supported material families and assignment paths."""

    model = ifcopenshell.file(schema=schema)
    project, _ = _root(model, "MILLI")
    elements = [_object(model, "IfcWall", f"Wall {index}") for index in range(8)]
    wall_type = _object(model, "IfcWallType", "Typed wall")

    concrete = model.create_entity(
        "IfcMaterial", Name="Concrete", Description="Structural concrete", Category="Structure"
    )
    insulation = model.create_entity("IfcMaterial", Name="Insulation", Category="Thermal")
    steel = model.create_entity("IfcMaterial", Name="Steel", Category="Metal")

    layer_core = model.create_entity(
        "IfcMaterialLayer",
        Material=concrete,
        LayerThickness=200.0,
        IsVentilated=False,
        Name="Core",
        Description="Load-bearing layer",
        Category="Structure",
        Priority=100,
    )
    layer_finish = model.create_entity(
        "IfcMaterialLayer",
        Material=insulation,
        LayerThickness=50.0,
        IsVentilated=True,
        Name="Insulation",
        Category="Thermal",
        Priority=50,
    )
    layer_set = model.create_entity(
        "IfcMaterialLayerSet",
        MaterialLayers=[layer_core, layer_finish],
        LayerSetName="Wall build-up",
        Description="Two-layer wall",
    )
    layer_usage = model.create_entity(
        "IfcMaterialLayerSetUsage",
        ForLayerSet=layer_set,
        LayerSetDirection="AXIS2",
        DirectionSense="POSITIVE",
        OffsetFromReferenceLine=0.0,
    )

    rectangle = model.create_entity(
        "IfcRectangleProfileDef", ProfileType="AREA", ProfileName="RHS", XDim=200.0, YDim=100.0
    )
    material_profile = model.create_entity(
        "IfcMaterialProfile",
        Name="Steel profile",
        Description="Primary section",
        Material=steel,
        Profile=rectangle,
        Priority=80,
        Category="Structure",
    )
    profile_set = model.create_entity(
        "IfcMaterialProfileSet",
        Name="Beam set",
        Description="Structural profile",
        MaterialProfiles=[material_profile],
    )
    profile_usage = model.create_entity(
        "IfcMaterialProfileSetUsage", ForProfileSet=profile_set, CardinalPoint=5
    )

    core = model.create_entity(
        "IfcMaterialConstituent",
        Name="Core",
        Description="Concrete fraction",
        Material=concrete,
        Fraction=0.75,
        Category="Structure",
    )
    finish = model.create_entity(
        "IfcMaterialConstituent",
        Name="Finish",
        Material=insulation,
        Fraction=0.25,
        Category="Finish",
    )
    constituent_set = model.create_entity(
        "IfcMaterialConstituentSet",
        Name="Composite",
        Description="Core and finish",
        MaterialConstituents=[core, finish],
    )
    material_list = model.create_entity("IfcMaterialList", Materials=[concrete, steel])

    definitions = [
        concrete,
        layer_set,
        layer_usage,
        profile_set,
        profile_usage,
        constituent_set,
        material_list,
    ]
    for element, definition in zip(elements[:7], definitions, strict=True):
        _rel(
            model,
            "IfcRelAssociatesMaterial",
            RelatedObjects=[element],
            RelatingMaterial=definition,
        )

    _rel(
        model,
        "IfcRelAssociatesMaterial",
        RelatedObjects=[wall_type],
        RelatingMaterial=insulation,
    )
    _rel(
        model,
        "IfcRelDefinesByType",
        RelatedObjects=[elements[7]],
        RelatingType=wall_type,
    )

    # Multiple direct associations are legal in real-world files. The core
    # preserves all unique definitions in relationship-ID order.
    multiple = _object(model, "IfcWall", "Multiple materials")
    _rel(
        model,
        "IfcRelAssociatesMaterial",
        RelatedObjects=[multiple],
        RelatingMaterial=steel,
    )
    _rel(
        model,
        "IfcRelAssociatesMaterial",
        RelatedObjects=[multiple],
        RelatingMaterial=concrete,
    )
    _rel(
        model,
        "IfcRelAssociatesMaterial",
        RelatedObjects=[multiple],
        RelatingMaterial=steel,
    )

    return model, {
        "project": project,
        "elements": elements,
        "wall_type": wall_type,
        "multiple": multiple,
        "concrete": concrete,
        "insulation": insulation,
        "steel": steel,
        "layer_set": layer_set,
        "layer_usage": layer_usage,
        "profile_set": profile_set,
        "profile_usage": profile_usage,
        "constituent_set": constituent_set,
        "material_list": material_list,
    }


def as_bytes(model: Any) -> bytes:
    return model.to_string().encode("utf-8")
