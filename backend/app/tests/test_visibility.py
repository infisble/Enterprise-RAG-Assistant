from app.db.models import User, UserRole
from app.repositories.documents import DocumentRepository


def test_admin_query_is_unrestricted(db_session):
    user = User(id=1, email="admin@example.com", full_name="Admin", role=UserRole.admin.value)
    query = DocumentRepository(db_session).visible_documents_query(user)

    assert "WHERE" not in str(query)


def test_employee_query_contains_visibility_rules(db_session):
    user = User(id=2, email="e@example.com", full_name="Employee", role=UserRole.employee.value, team_id=7)
    query = DocumentRepository(db_session).visible_documents_query(user)
    compiled = str(query)

    assert "visibility" in compiled
    assert "owner_id" in compiled
    assert "team_id" in compiled
