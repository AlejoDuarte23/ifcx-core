# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import json

import ifcx_core


MINIMAL_IFC = b"""ISO-10303-21;
HEADER;
FILE_SCHEMA(('IFC4'));
ENDSEC;
DATA;
#1=IFCPROJECT('P',$,'Project',$,$,$,$,$,#2);
#2=IFCUNITASSIGNMENT((#3));
#3=IFCSIUNIT(*,.LENGTHUNIT.,$,.METRE.);
ENDSEC;
END-ISO-10303-21;
"""


def test_model_data_returns_native_python_objects() -> None:
    data = ifcx_core.model_data(MINIMAL_IFC)

    assert data["schema"] == "IFC4"
    assert data["entity_count"] == 3
    assert data["spatial"]["project_id"] == 1
    assert data["spatial"]["roots"][0]["express_id"] == 1
    assert data["materials"]["associations"] == []


def test_json_api_matches_native_api() -> None:
    assert json.loads(ifcx_core.model_data_json(MINIMAL_IFC)) == ifcx_core.model_data(MINIMAL_IFC)
