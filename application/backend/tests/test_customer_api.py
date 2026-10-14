"""Tests for Customer Intelligence API endpoints."""
import pytest
from datetime import datetime
from app.models import CustomerAccountModel, CustomerSentimentModel


@pytest.fixture
def sample_customers(db_session, sample_node):
    """Create sample customer accounts for testing."""
    customers = []
    for i in range(5):
        plans = ["Internet 200", "Internet 400", "Internet 1000", "Gig+", "Internet 200"]
        statuses = ["active", "active", "active", "suspended", "closed"]
        c = CustomerAccountModel(
            id=i + 1,
            account_id=f"ACCT-{i + 1:07d}",
            name=f"Test Customer {i + 1}",
            address=f"{100 + i} Main St",
            city="New York",
            state="NY",
            zip_code="10001",
            node_id=sample_node.node_id,
            service_plan=plans[i],
            provisioned_download_mbps=200 + i * 200,
            provisioned_upload_mbps=20 + i * 10,
            monthly_rate=49.99 + i * 20,
            modem_manufacturer="ARRIS",
            modem_model="S33",
            docsis_version="3.1",
            actual_download_mbps=180.0 + i * 200,
            actual_upload_mbps=18.0 + i * 10,
            connection_drops_24h=i,
            account_status=statuses[i],
            contract_status="active",
            tenure_months=12 + i * 6,
        )
        db_session.add(c)
        customers.append(c)
    db_session.commit()
    return customers


@pytest.fixture
def sample_sentiments(db_session, sample_customers):
    """Create sample sentiment records for testing."""
    sentiments = []
    sources = ["nps_survey", "social_media", "call_center", "app_review", "chat"]
    labels = ["positive", "neutral", "negative", "positive", "very_negative"]
    for i, cust in enumerate(sample_customers):
        s = CustomerSentimentModel(
            id=i + 1,
            sentiment_id=f"SENT-{i + 1:012d}",
            account_id=cust.account_id,
            source=sources[i],
            sentiment_score=0.5 - i * 0.3,
            sentiment_label=labels[i],
            topics=["speed_issues", "pricing"],
            summary=f"Test sentiment for customer {i + 1}",
            nps_score=9 - i if sources[i] == "nps_survey" else None,
            resolution_status="resolved" if i < 3 else "unresolved",
            timestamp=datetime.now(),
        )
        db_session.add(s)
        sentiments.append(s)
    db_session.commit()
    return sentiments


# ===== GET /customers/overview =====

def test_customer_overview_empty(client):
    """Overview returns zeros when no customers exist."""
    resp = client.get("/api/v1/customers/overview")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_customers"] == 0
    assert data["total_active"] == 0
    assert "by_service_plan" in data
    assert "connection_quality" in data


def test_customer_overview_with_data(client, sample_customers, sample_sentiments):
    """Overview returns correct counts and averages."""
    resp = client.get("/api/v1/customers/overview")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_customers"] == 5
    assert data["total_active"] == 3
    assert data["total_sentiments"] == 5
    assert "by_service_plan" in data
    assert "by_docsis_version" in data
    assert "connection_quality" in data


# ===== GET /customers/list =====

def test_customer_list_empty(client):
    """Empty list when no customers exist."""
    resp = client.get("/api/v1/customers/list")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0
    assert data["customers"] == []


def test_customer_list_with_data(client, sample_customers, sample_sentiments):
    """List returns customers with sentiment scores."""
    resp = client.get("/api/v1/customers/list")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 5
    assert len(data["customers"]) == 5
    # Check fields exist
    cust = data["customers"][0]
    assert "account_id" in cust
    assert "name" in cust
    assert "service_plan" in cust
    assert "avg_sentiment_score" in cust


def test_customer_list_filter_plan(client, sample_customers):
    """Filter by service plan."""
    resp = client.get("/api/v1/customers/list?service_plan=Internet 200")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2  # Two customers with Internet 200


def test_customer_list_filter_status(client, sample_customers):
    """Filter by account status."""
    resp = client.get("/api/v1/customers/list?account_status=active")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 3


def test_customer_list_search(client, sample_customers):
    """Search by name."""
    resp = client.get("/api/v1/customers/list?search=Customer 1")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1


def test_customer_list_pagination(client, sample_customers):
    """Pagination works correctly."""
    resp = client.get("/api/v1/customers/list?skip=0&limit=2")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 5
    assert len(data["customers"]) == 2

    resp2 = client.get("/api/v1/customers/list?skip=2&limit=2")
    data2 = resp2.json()
    assert len(data2["customers"]) == 2
    assert data2["customers"][0]["account_id"] != data["customers"][0]["account_id"]


# ===== GET /customers/sentiment/summary =====

def test_sentiment_summary_empty(client):
    """Sentiment summary returns empty when no data."""
    resp = client.get("/api/v1/customers/sentiment/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert data["by_source"] == []
    assert data["nps"]["total_responses"] == 0


def test_sentiment_summary_with_data(client, sample_customers, sample_sentiments):
    """Sentiment summary returns source breakdown and NPS."""
    resp = client.get("/api/v1/customers/sentiment/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["by_source"]) > 0
    assert "by_label" in data
    assert "nps" in data
    assert data["nps"]["total_responses"] >= 1
    assert "by_resolution" in data


# ===== GET /customers/plans/breakdown =====

def test_plans_breakdown_empty(client):
    """Plans breakdown returns empty list when no customers."""
    resp = client.get("/api/v1/customers/plans/breakdown")
    assert resp.status_code == 200
    data = resp.json()
    assert data["plans"] == []


def test_plans_breakdown_with_data(client, sample_customers):
    """Plans breakdown returns per-plan analytics."""
    resp = client.get("/api/v1/customers/plans/breakdown")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["plans"]) > 0
    plan = data["plans"][0]
    assert "plan" in plan
    assert "total" in plan
    assert "monthly_revenue" in plan
    assert "churn_risk_pct" in plan
    assert "speed_compliance_pct" in plan
