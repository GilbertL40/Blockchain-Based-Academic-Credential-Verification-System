"""
Acceptance tests for the Blockchain-Based Academic Credential Verification System.

Covers the five routes defined in app.py:
    /          -> login page (home)
    /login     -> login page (GET and POST)
    /admin     -> administrator dashboard
    /student   -> student dashboard
    /verifier  -> verifier / employer portal

Run with:
    pip install pytest --break-system-packages   (or: pip install pytest)
    pytest tests/test_app.py -v

Place this file inside a top-level "tests/" folder in the repo, e.g.:
    tests/test_app.py
"""

import sys
import os

# Allow running pytest from the repo root without a package install step.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from app import app as flask_app


@pytest.fixture
def client():
    flask_app.config.update(TESTING=True)
    with flask_app.test_client() as test_client:
        yield test_client


# ---------------------------------------------------------------------------
# Route availability — each page must load successfully (HTTP 200)
# ---------------------------------------------------------------------------

def test_home_page_loads(client):
    """GET / should serve the login page."""
    response = client.get('/')
    assert response.status_code == 200
    assert b'<html' in response.data.lower()


def test_login_page_loads_get(client):
    """GET /login should serve the login page."""
    response = client.get('/login')
    assert response.status_code == 200


def test_login_page_loads_post(client):
    """POST /login should also succeed (route accepts GET and POST)."""
    response = client.post('/login', data={'email': 'test@ibs.edu.pg', 'password': 'placeholder'})
    assert response.status_code == 200


def test_admin_dashboard_loads(client):
    """GET /admin should serve the administrator dashboard."""
    response = client.get('/admin')
    assert response.status_code == 200


def test_student_dashboard_loads(client):
    """GET /student should serve the student dashboard."""
    response = client.get('/student')
    assert response.status_code == 200


def test_verifier_dashboard_loads(client):
    """GET /verifier should serve the verifier/employer portal."""
    response = client.get('/verifier')
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# Basic content sanity checks — confirms the correct template rendered,
# not just any 200 response
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("route,expected_snippet", [
    ('/admin', b'admin'),
    ('/student', b'student'),
    ('/verifier', b'verif'),
])
def test_dashboard_content_matches_role(client, route, expected_snippet):
    """Each dashboard's HTML should reference its own role somewhere
    (in text, ids, or classes) rather than accidentally rendering
    the wrong template."""
    response = client.get(route)
    assert expected_snippet in response.data.lower()


# ---------------------------------------------------------------------------
# Unknown routes should not silently succeed
# ---------------------------------------------------------------------------

def test_unknown_route_returns_404(client):
    response = client.get('/this-route-does-not-exist')
    assert response.status_code == 404
