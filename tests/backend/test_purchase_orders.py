"""
Tests for purchase order endpoints used by the dashboard's PurchaseOrderModal.

POST /api/purchase-orders creates a PO in memory; GET /api/purchase-orders/{backlog_item_id} reads it.
"""
import pytest

from main import purchase_orders


@pytest.fixture(autouse=True)
def restore_purchase_orders():
    """POs are stored in a module-level list; restore it so tests stay independent."""
    saved = list(purchase_orders)
    yield
    purchase_orders[:] = saved


@pytest.fixture
def backlog_item(client):
    items = client.get("/api/backlog").json()
    free = [i for i in items if not i["has_purchase_order"]]
    assert free, "Need at least one backlog item without a purchase order"
    return free[0]


def po_payload(backlog_item_id, **overrides):
    payload = {
        "backlog_item_id": backlog_item_id,
        "supplier_name": "Acme Supply",
        "quantity": 350,
        "unit_cost": 12.5,
        "expected_delivery_date": "2025-12-15",
        "notes": "Rush order",
    }
    payload.update(overrides)
    return payload


class TestCreatePurchaseOrder:

    def test_create_returns_201_and_po(self, client, backlog_item):
        response = client.post("/api/purchase-orders", json=po_payload(backlog_item["id"]))
        assert response.status_code == 201
        po = response.json()
        assert po["id"]
        assert po["backlog_item_id"] == backlog_item["id"]
        assert po["supplier_name"] == "Acme Supply"
        assert po["quantity"] == 350
        assert po["unit_cost"] == 12.5
        assert po["expected_delivery_date"] == "2025-12-15"
        assert po["status"] == "Pending"
        assert po["created_date"]
        assert po["notes"] == "Rush order"

    def test_created_po_can_be_fetched(self, client, backlog_item):
        created = client.post("/api/purchase-orders", json=po_payload(backlog_item["id"])).json()
        response = client.get(f"/api/purchase-orders/{backlog_item['id']}")
        assert response.status_code == 200
        assert response.json() == created

    def test_backlog_reflects_created_po(self, client, backlog_item):
        client.post("/api/purchase-orders", json=po_payload(backlog_item["id"]))
        items = {i["id"]: i for i in client.get("/api/backlog").json()}
        assert items[backlog_item["id"]]["has_purchase_order"] is True

    def test_supplier_name_is_trimmed(self, client, backlog_item):
        po = client.post("/api/purchase-orders",
                         json=po_payload(backlog_item["id"], supplier_name="  Acme Supply  ")).json()
        assert po["supplier_name"] == "Acme Supply"

    def test_second_po_for_same_item_is_rejected(self, client, backlog_item):
        assert client.post("/api/purchase-orders", json=po_payload(backlog_item["id"])).status_code == 201
        response = client.post("/api/purchase-orders", json=po_payload(backlog_item["id"]))
        assert response.status_code == 409

    def test_unknown_backlog_item_returns_404(self, client):
        response = client.post("/api/purchase-orders", json=po_payload("does-not-exist"))
        assert response.status_code == 404

    @pytest.mark.parametrize("overrides", [
        {"quantity": 0},
        {"quantity": -5},
        {"unit_cost": -1},
        {"supplier_name": ""},
        {"expected_delivery_date": "not-a-date"},
    ])
    def test_invalid_input_is_rejected(self, client, backlog_item, overrides):
        response = client.post("/api/purchase-orders", json=po_payload(backlog_item["id"], **overrides))
        assert response.status_code == 422

    def test_blank_supplier_name_is_rejected(self, client, backlog_item):
        response = client.post("/api/purchase-orders", json=po_payload(backlog_item["id"], supplier_name="   "))
        assert response.status_code == 400

    def test_rejected_request_creates_nothing(self, client, backlog_item):
        client.post("/api/purchase-orders", json=po_payload(backlog_item["id"], quantity=0))
        assert client.get(f"/api/purchase-orders/{backlog_item['id']}").status_code == 404


class TestGetPurchaseOrder:

    def test_missing_po_returns_404(self, client, backlog_item):
        response = client.get(f"/api/purchase-orders/{backlog_item['id']}")
        assert response.status_code == 404
        assert "detail" in response.json()
