import pytest
from app import app, db, User
import random


@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'  # Use in-memory DB
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
        yield client


def test_home_page(client):
    response = client.get('/')
    assert response.status_code == 200
    assert b"Welcome to the Trivia Game!" in response.data


def test_register_login(client):
    # Fetch CSRF token from the registration page
    response = client.get('/register')
    assert response.status_code == 200

    csrf_token = response.data.decode().split('name="csrf_token" type="hidden" value="')[1].split('"')[0]

    # Ensure unique username to avoid conflicts
    unique_username = f"testuser{random.randint(1000, 9999)}"

    # Test registration with CSRF token
    response = client.post('/register', data={
        'csrf_token': csrf_token,
        'username': unique_username,
        'password': '24651361',
        'confirm_password': '24651361'
    })
    assert response.status_code == 302  # Redirect after successful registration

    # Test login
    response = client.post('/login', data={
        'csrf_token': csrf_token,
        'username': unique_username,
        'password': '24651361'
    })
    assert response.status_code == 302  # Redirect after successful login



def test_leaderboard(client):
    response = client.get('/leaderboard')
    assert response.status_code == 200
