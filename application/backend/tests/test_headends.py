"""Tests for headend endpoints."""
import pytest
from fastapi import status
from app.models import HeadendModel


@pytest.fixture
def sample_headends(db_session):
    """Create sample headends for testing."""
    headends = []
    for i in range(3):
        he = HeadendModel(
            id=i + 1,
            headend_id=f"HE-TEST-{i+1:03d}",
            name=f"Test Headend {i+1}",
            region="Northeast",
            city="New York",
            state="NY",
            status="operational" if i < 2 else "maintenance",
            service_area=f"Area-{i+1}",
            power_capacity_mw=2.5,
            total_rack_units=100,
        )
        db_session.add(he)
        headends.append(he)
    db_session.commit()
    return headends


class TestHeadendEndpoints:
    """Tests for headend endpoints (renamed from datacenters)."""

    def test_get_headends_empty(self, client):
        """Test getting headends when none exist."""
        response = client.get("/api/v1/headends")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 0
        assert data["items"] == []

    def test_get_headends_with_data(self, client, sample_headends):
        """Test getting headends when data exists."""
        response = client.get("/api/v1/headends")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 3
        assert len(data["items"]) == 3
        assert data["items"][0]["headend_id"].startswith("HE-TEST-")

    def test_get_headends_filter_by_region(self, client, sample_headends):
        """Test filtering headends by region."""
        response = client.get("/api/v1/headends?region=Northeast")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 3

        response = client.get("/api/v1/headends?region=Nonexistent")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 0

    def test_get_headends_filter_by_status(self, client, sample_headends):
        """Test filtering headends by status."""
        response = client.get("/api/v1/headends?status=operational")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 2

    def test_get_headends_pagination(self, client, sample_headends):
        """Test headend pagination."""
        response = client.get("/api/v1/headends?limit=2")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 3
        assert len(data["items"]) == 2

    def test_get_headend_metadata_summary(self, client, sample_headends):
        """Test headend metadata summary."""
        response = client.get("/api/v1/headends/metadata/summary")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total_headends"] == 3
        assert len(data["regions"]) >= 1
        assert len(data["statuses"]) >= 1
