import pytest
from app import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_homepage_redirect(client):
    """Test that the root URL redirects to login when not authenticated."""
    response = client.get('/', follow_redirects=False)
    # Chưa đăng nhập sẽ bị đẩy về login (từ cơ chế Kerberos hoặc user session)
    assert response.status_code in [301, 302]

def test_api_not_found(client):
    """Test 404 response for nonexistent route."""
    response = client.get('/route_khong_ton_tai')
    assert response.status_code == 404
