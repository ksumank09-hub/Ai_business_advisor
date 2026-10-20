"""tests/test_auth.py - registration, login, logout, and auth guard."""


def test_register_creates_user(client):
    response = client.post("/register", data={
        "name": "Alice",
        "email": "alice@example.com",
        "password": "secure123",
        "confirm_password": "secure123",
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b"Account created successfully" in response.data or b"login" in response.data.lower()


def test_register_rejects_mismatched_passwords(client):
    response = client.post("/register", data={
        "name": "Bob",
        "email": "bob@example.com",
        "password": "secure123",
        "confirm_password": "different123",
    }, follow_redirects=True)
    assert b"Passwords do not match" in response.data


def test_login_with_correct_credentials(client):
    client.post("/register", data={
        "name": "Carol", "email": "carol@example.com",
        "password": "mypassword", "confirm_password": "mypassword",
    })
    response = client.post("/login", data={
        "email": "carol@example.com", "password": "mypassword",
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b"Welcome" in response.data or b"Dashboard" in response.data


def test_login_with_wrong_password_fails(client):
    client.post("/register", data={
        "name": "Dave", "email": "dave@example.com",
        "password": "correctpass", "confirm_password": "correctpass",
    })
    response = client.post("/login", data={
        "email": "dave@example.com", "password": "wrongpass",
    }, follow_redirects=True)
    assert b"Invalid email or password" in response.data


def test_dashboard_requires_login(client):
    response = client.get("/dashboard", follow_redirects=True)
    assert b"Please log in" in response.data or b"Login" in response.data


def test_logout_clears_session(registered_user):
    response = registered_user.get("/logout", follow_redirects=True)
    assert response.status_code == 200
    # after logout, dashboard should redirect back to login
    dash_response = registered_user.get("/dashboard", follow_redirects=True)
    assert b"Login" in dash_response.data or b"log in" in dash_response.data.lower()


def test_forgot_password_resets_password(client):
    client.post("/register", data={
        "name": "Eve", "email": "eve@example.com",
        "password": "initialpass", "confirm_password": "initialpass",
    })
    # Reset password
    response = client.post("/forgot-password", data={
        "email": "eve@example.com",
        "new_password": "newsecurepass",
        "confirm_password": "newsecurepass",
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b"Password reset successfully" in response.data

    # Log in with new password
    login_response = client.post("/login", data={
        "email": "eve@example.com", "password": "newsecurepass",
    }, follow_redirects=True)
    assert login_response.status_code == 200
    assert b"Welcome back" in login_response.data or b"Dashboard" in login_response.data


def test_forgot_password_invalid_user(client):
    response = client.post("/forgot-password", data={
        "email": "nonexistent@example.com",
        "new_password": "newsecurepass",
        "confirm_password": "newsecurepass",
    }, follow_redirects=True)
    assert b"No account found" in response.data
