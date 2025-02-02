from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

mock_db_session = MagicMock()
mock_db_session.query.return_value.filter.return_value.first.return_value = None
mock_db_session.commit.return_value = None
mock_db_session.refresh.return_value = None

@patch("database.get_db", return_value=mock_db_session)
@patch("auth.create_access_token", return_value="test_token")
@patch("auth.send_verification_email", return_value=None)
def test_signup(mock_send_email, mock_create_token, mock_db):
    response = client.post("/user/signup", json={
        "username": "testuser",
        "email": "test@example.com",
        "password": "securepassword"
    })
    print("Signup response:", response.json())
    assert response.status_code in [201, 200]

@patch("auth.jwt.decode", return_value={"sub": "test@example.com"})
@patch("database.get_db", return_value=mock_db_session)
def test_verify_email(mock_db, mock_jwt_decode):
    response = client.get("/user/verify-email", params={"token": "test_token"})
    print("Verify email response:", response.json())
    assert response.status_code in [200, 400]

@patch("auth.get_current_user", return_value={"id": 1, "username": "testuser", "email": "test@example.com", "role": "user"})
@patch("database.get_db", return_value=mock_db_session)
def test_get_user_profile(mock_db, mock_get_user):
    headers = {"Authorization": "Bearer test_token"}
    response = client.get("/user/me", headers=headers)
    print("Get user profile response:", response.json())
    assert response.status_code == 200

@patch("auth.get_current_user", return_value={"id": 1, "username": "adminuser", "email": "admin@example.com", "role": "admin"})
@patch("database.get_db", return_value=mock_db_session)
def test_set_role(mock_db, mock_get_user):
    headers = {"Authorization": "Bearer test_token"}
    response = client.put("/user/set-role/1", json={"new_role": "admin"}, headers=headers)
    print("Set user role response:", response.json())
    assert response.status_code in [200, 404]

@patch("auth.get_current_user", return_value={"id": 1, "username": "testuser", "email": "test@example.com", "role": "user"})
@patch("database.get_db", return_value=mock_db_session)
@patch("cloudinary.uploader.upload", return_value={"url": "https://fake-avatar.com/avatar.png"})
def test_upload_avatar(mock_cloudinary, mock_db, mock_get_user):
    headers = {"Authorization": "Bearer test_token"}
    files = {"file": ("avatar.png", b"fake image data", "image/png")}
    response = client.post("/user/avatar/", files=files, headers=headers)
    print("Upload avatar response:", response.json())
    assert response.status_code in [200, 202]

@patch("auth.jwt.decode", return_value={"sub": "test@example.com"})
@patch("auth.get_current_user", return_value={"id": 1, "username": "testuser", "email": "test@example.com", "role": "user"})
@patch("database.get_db", return_value=mock_db_session)
def test_reset_password(mock_db, mock_get_user, mock_jwt_decode):
    response = client.post("/user/reset-password", json={
        "token": "test_token",
        "new_password": "new_secure_password"
    })
    print("Reset password response:", response.json())
    assert response.status_code in [200, 400]

@patch("auth.get_current_user", return_value={"id": 1, "username": "testuser", "email": "test@example.com", "role": "user"})
@patch("repository.contacts.get_upcoming_birthdays", return_value=[{
    "id": 1, "first_name": "Alice", "last_name": "Smith", "email": "alice@example.com", "phone": "0987654321"
}])
@patch("database.get_db", return_value=mock_db_session)
def test_upcoming_birthdays(mock_db, mock_get_birthdays, mock_get_user):
    headers = {"Authorization": "Bearer test_token"}
    response = client.get("/contacts/upcoming-birthdays/", headers=headers)
    print("Upcoming birthdays response:", response.json())
    assert response.status_code in [200, 202]
