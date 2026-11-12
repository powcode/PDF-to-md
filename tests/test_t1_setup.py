import pytest
from app import create_app

@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client

def test_index_page(client):
    response = client.get("/")
    assert response.status_code == 200
    html = response.data.decode("utf-8")
    assert "Slidekit" in html
    assert "PDF ke Markdown" in html
    assert "Split PDF" in html
    assert 'lang="id"' in html

def test_404_error(client):
    response = client.get("/nonexistent-route")
    assert response.status_code == 404
    data = response.get_json()
    assert "error" in data
    assert "tidak ditemukan" in data["error"]
