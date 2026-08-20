def test_home_page_renders(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"Conversational CNC" in response.data
    assert b"Hole Drilling Operation" in response.data
    assert b"toolpathCanvas" in response.data

def test_drilling_page_renders(client):
    response = client.get("/drilling")
    assert response.status_code == 200
    assert b"Single Hole" in response.data
    assert b"Bolt Circle" in response.data

def test_machines_page_renders(client):
    response = client.get("/machines")
    assert response.status_code == 200
    assert b"Machine Profiles" in response.data

def test_tools_page_renders(client):
    response = client.get("/tools")
    assert response.status_code == 200
    assert b"Tool Library" in response.data

def test_peck_drilling_page_renders(client):
    response = client.get("/peck-drilling")
    assert response.status_code == 200
    assert b"Peck Drilling" in response.data

def test_thread_milling_page_renders(client):
    response = client.get("/thread-milling")
    assert response.status_code == 200
    assert b"Helical Thread Milling" in response.data

def test_circular_pocket_page_renders(client):
    response = client.get("/circular-pocket")
    assert response.status_code == 200
    assert b"Circular Pocket" in response.data

def test_surfacing_page_renders(client):
    response = client.get("/surfacing")
    assert response.status_code == 200
    assert b"Surfacing" in response.data

def test_engraving_page_renders(client):
    response = client.get("/engraving")
    assert response.status_code == 200
    assert b"Text Engraving" in response.data

def test_rectangular_pocket_page_renders(client):
    response = client.get("/rectangular-pocket")
    assert response.status_code == 200
    assert b"Rectangular Pocket" in response.data
    assert b"Raised Boss" in response.data

def test_transformations_page_renders(client):
    response = client.get("/transformations")
    assert response.status_code == 200
    assert b"Transformations" in response.data
    assert b"Shift / Offset" in response.data
    assert b"Split Tools" in response.data

def test_contouring_page_renders(client):
    response = client.get("/contouring")
    assert response.status_code == 200
    assert b"Contour Milling" in response.data
    assert b"toolpathCanvas" in response.data





