// This Source Code Form is subject to the terms of the Mozilla Public
// License, v. 2.0. If a copy of the MPL was not distributed with this
// file, You can obtain one at https://mozilla.org/MPL/2.0/.

use ifcx_core::analyze_ifc;

fn wrap(body: &str) -> Vec<u8> {
    format!(
        "ISO-10303-21;\nHEADER;\nFILE_SCHEMA(('IFC4'));\nENDSEC;\nDATA;\n{}\nENDSEC;\nEND-ISO-10303-21;",
        body
    )
    .into_bytes()
}

#[test]
fn builds_ifclite_compatible_spatial_hierarchy_and_reverse_maps() {
    let ifc = wrap(
        r#"
#1=IFCPROJECT('P',$,'Project',$,$,$,$,$,#2);
#2=IFCUNITASSIGNMENT((#3));
#3=IFCSIUNIT(*,.LENGTHUNIT.,.MILLI.,.METRE.);
#10=IFCSITE('S',$,'Site',$,$,$,$,'Campus',.ELEMENT.,$,$,$,$,$);
#11=IFCBUILDING('B',$,'Building',$,$,$,$,'HQ',.ELEMENT.,$,$,$);
#12=IFCBUILDINGSTOREY('ST',$,'Level 1',$,$,#20,$,'First floor',.ELEMENT.,$);
#13=IFCSPACE('SP',$,'101',$,$,$,$,'Room',.ELEMENT.,.INTERNAL.);
#20=IFCLOCALPLACEMENT($,#21);
#21=IFCAXIS2PLACEMENT3D(#22,$,$);
#22=IFCCARTESIANPOINT((0.,0.,3000.));
#100=IFCWALL();
#101=IFCGRID();
#102=IFCBUILDINGELEMENTPART();
#103=IFCFURNISHINGELEMENT();
#104=IFCDISTRIBUTIONELEMENT();
#110=IFCRELAGGREGATES('R1',$,$,$,#1,(#10));
#111=IFCRELAGGREGATES('R2',$,$,$,#10,(#11));
#112=IFCRELAGGREGATES('R3',$,$,$,#11,(#12));
#113=IFCRELAGGREGATES('R4',$,$,$,#12,(#13));
#114=IFCRELCONTAINEDINSPATIALSTRUCTURE('R5',$,$,$,(#13,#100,#101),#12);
#115=IFCRELCONTAINEDINSPATIALSTRUCTURE('R6',$,$,$,(#103),#13);
#116=IFCRELAGGREGATES('R7',$,$,$,#100,(#102));
#117=IFCRELNESTS('R8',$,$,$,#100,(#104));
#118=IFCRELREFERENCEDINSPATIALSTRUCTURE('R9',$,$,$,(#103),#12);
"#,
    );

    let data = analyze_ifc(&ifc).expect("synthetic IFC should parse");
    assert_eq!(data.schema.as_deref(), Some("IFC4"));
    assert_eq!(data.length_unit_scale, 0.001);
    assert_eq!(data.spatial.project_id, Some(1));
    assert_eq!(data.spatial.roots.len(), 1);
    assert_eq!(data.spatial.by_storey.get(&12), Some(&vec![100, 101]));
    assert_eq!(data.spatial.by_space.get(&13), Some(&vec![103]));
    assert_eq!(data.spatial.storey_elevations.get(&12), Some(&3.0));
    assert_eq!(data.spatial.element_to_storey.get(&13), Some(&12));
    assert_eq!(data.spatial.element_to_storey.get(&102), Some(&12));
    assert_eq!(data.spatial.element_to_storey.get(&104), Some(&12));
    assert_eq!(data.spatial.element_to_container.get(&103), Some(&13));
    assert_eq!(
        data.spatial.referenced_by_structure.get(&12),
        Some(&vec![103])
    );

    let storey = &data.spatial.roots[0].children[0].children[0].children[0];
    assert_eq!(storey.express_id, 12);
    assert_eq!(storey.children.len(), 1, "space must be deduplicated");
    assert_eq!(storey.children[0].express_id, 13);
    assert_eq!(storey.elevation, Some(3.0));
}

#[test]
fn resolves_material_families_precedence_and_deterministic_order() {
    let ifc = wrap(
        r#"
#1=IFCPROJECT('P',$,'Project',$,$,$,$,$,#2);
#2=IFCUNITASSIGNMENT((#3));
#3=IFCSIUNIT(*,.LENGTHUNIT.,.MILLI.,.METRE.);
#100=IFCWALL();
#101=IFCWALL();
#102=IFCWALL();
#103=IFCWALL();
#104=IFCWALL();
#105=IFCBEAM();
#106=IFCWALL();
#500=IFCWALLTYPE();
#200=IFCMATERIAL('Concrete','Structural concrete','Concrete');
#201=IFCMATERIAL('Insulation',$,'Thermal');
#202=IFCMATERIAL('Steel',$,'Metal');
#210=IFCMATERIALCONSTITUENTSET('Composite',$,(#211,#212));
#211=IFCMATERIALCONSTITUENT('Core',$,#200,0.75,'Core');
#212=IFCMATERIALCONSTITUENT('Finish',$,#201,0.25,'Finish');
#220=IFCMATERIALLAYERSETUSAGE(#221,.AXIS2.,.POSITIVE.,0.,$);
#221=IFCMATERIALLAYERSET((#222,#223),'Wall build-up',$);
#222=IFCMATERIALLAYER(#200,200.,.F.,'Core',$,'Structure',$);
#223=IFCMATERIALLAYER(#201,50.,.T.,'Insulation',$,'Thermal',$);
#230=IFCMATERIALPROFILESET('Beam set',$,(#231),$);
#231=IFCMATERIALPROFILE('Steel profile',$,#202,$,$,'Structure');
#240=IFCMATERIALLIST((#200,#202));
#300=IFCRELASSOCIATESMATERIAL('M1',$,$,$,(#100),#210);
#301=IFCRELASSOCIATESMATERIAL('M2',$,$,$,(#500),#201);
#302=IFCRELDEFINESBYTYPE('T1',$,$,$,(#101,#102),#500);
#303=IFCRELASSOCIATESMATERIAL('M3',$,$,$,(#102),#202);
#304=IFCRELASSOCIATESMATERIAL('M4',$,$,$,(#104),#220);
#305=IFCRELASSOCIATESMATERIAL('M5',$,$,$,(#105),#230);
#306=IFCRELASSOCIATESMATERIAL('M6',$,$,$,(#106),#240);
#900=IFCRELASSOCIATESMATERIAL('M9',$,$,$,(#103),#200);
#800=IFCRELASSOCIATESMATERIAL('M8',$,$,$,(#103),#202);
#1000=IFCRELASSOCIATESMATERIAL('M10',$,$,$,(#103),#202);
"#,
    );

    let data = analyze_ifc(&ifc).expect("synthetic IFC should parse");
    let materials = data.materials;

    let wall_100 = &materials.element_materials[&100][0];
    assert_eq!(wall_100.material.material_type, "MaterialConstituentSet");
    assert_eq!(wall_100.material.constituents.len(), 2);
    assert_eq!(
        wall_100.material.constituents[0].material_name.as_deref(),
        Some("Concrete")
    );

    let inherited = &materials.element_materials[&101][0];
    assert_eq!(inherited.definition_id, 201);
    assert_eq!(inherited.inherited_from_type, Some(500));
    assert_eq!(inherited.material.name.as_deref(), Some("Insulation"));

    let overridden = &materials.element_materials[&102];
    assert_eq!(overridden.len(), 1);
    assert_eq!(overridden[0].definition_id, 202);
    assert_eq!(overridden[0].inherited_from_type, None);

    let multiple: Vec<u32> = materials.element_materials[&103]
        .iter()
        .map(|assignment| assignment.definition_id)
        .collect();
    assert_eq!(
        multiple,
        vec![202, 200],
        "lowest relationship ID wins ordering"
    );

    let layers = &materials.element_materials[&104][0].material;
    assert_eq!(layers.source_definition_id, 220);
    assert_eq!(layers.resolved_definition_id, 221);
    assert_eq!(layers.layers[0].thickness, Some(0.2));
    assert_eq!(layers.layers[1].thickness, Some(0.05));

    assert_eq!(
        materials.element_materials[&105][0].material.profiles.len(),
        1
    );
    assert_eq!(
        materials.element_materials[&106][0]
            .material
            .materials
            .len(),
        2
    );
    assert!(
        !materials.element_materials.contains_key(&500),
        "type objects are definitions, not elements"
    );
    assert!(materials.definitions.contains_key(&200));
    assert!(materials.definitions.contains_key(&210));
    assert!(materials.definitions.contains_key(&220));
}
