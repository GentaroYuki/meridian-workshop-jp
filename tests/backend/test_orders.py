"""
Tests for order API endpoints.

Spec: docs/rfp/vendor-handoff.md -- GET /api/orders (filters: warehouse, category, status, month).
Expected values are derived from the full order list, not hard-coded counts.
"""
import collections
import re

import pytest

VALID_STATUSES = {"Delivered", "Shipped", "Processing", "Backordered"}
ISO_DATETIME = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$")


@pytest.fixture
def all_orders(client):
    response = client.get("/api/orders")
    assert response.status_code == 200
    return response.json()


class TestOrdersList:
    """GET /api/orders without filters."""

    def test_get_all_orders(self, all_orders):
        assert isinstance(all_orders, list)
        assert len(all_orders) > 0

    def test_order_fields(self, all_orders):
        required = {"id", "order_number", "customer", "items", "status",
                    "order_date", "expected_delivery", "total_value"}
        for order in all_orders:
            missing = required - order.keys()
            assert not missing, f"Order {order.get('id')} is missing {missing}"

    def test_order_items_structure(self, all_orders):
        for order in all_orders:
            assert len(order["items"]) > 0, f"Order {order['id']} has no items"
            for item in order["items"]:
                assert {"sku", "name", "quantity", "unit_price"} <= item.keys()
                assert isinstance(item["quantity"], int) and item["quantity"] > 0
                assert isinstance(item["unit_price"], (int, float)) and item["unit_price"] >= 0

    def test_status_values(self, all_orders):
        for order in all_orders:
            assert order["status"] in VALID_STATUSES, f"Unexpected status {order['status']}"

    def test_date_formats(self, all_orders):
        for order in all_orders:
            assert ISO_DATETIME.match(order["order_date"]), order["order_date"]
            assert ISO_DATETIME.match(order["expected_delivery"]), order["expected_delivery"]
            if order.get("actual_delivery"):
                assert ISO_DATETIME.match(order["actual_delivery"]), order["actual_delivery"]

    def test_total_value_matches_items(self, all_orders):
        for order in all_orders:
            expected = sum(i["quantity"] * i["unit_price"] for i in order["items"])
            assert order["total_value"] == pytest.approx(expected, abs=0.01), \
                f"Order {order['id']}: total_value {order['total_value']} != {expected}"

    def test_only_delivered_orders_have_actual_delivery(self, all_orders):
        for order in all_orders:
            if order["status"] != "Delivered":
                assert not order.get("actual_delivery"), \
                    f"Order {order['id']} is {order['status']} but has actual_delivery"

    @pytest.mark.xfail(strict=True, reason="Data issue: 8 Delivered orders have no actual_delivery in server/data/orders.json")
    def test_delivered_orders_have_actual_delivery(self, all_orders):
        missing = [o["id"] for o in all_orders if o["status"] == "Delivered" and not o.get("actual_delivery")]
        assert not missing, f"Delivered orders without actual_delivery: {missing}"

    @pytest.mark.xfail(strict=True, reason="Data issue: ids/order_numbers 201-210 appear twice in server/data/orders.json")
    def test_order_ids_are_unique(self, all_orders):
        ids = collections.Counter(o["id"] for o in all_orders)
        duplicates = {k: v for k, v in ids.items() if v > 1}
        assert not duplicates, f"Duplicate order ids: {duplicates}"


class TestOrdersFilters:
    """GET /api/orders with query filters (warehouse, category, status, month)."""

    def test_filter_by_warehouse(self, client, all_orders):
        for warehouse in {o["warehouse"] for o in all_orders}:
            data = client.get("/api/orders", params={"warehouse": warehouse}).json()
            expected = [o for o in all_orders if o["warehouse"] == warehouse]
            assert len(data) == len(expected) > 0
            assert all(o["warehouse"] == warehouse for o in data)

    def test_filter_by_category(self, client, all_orders):
        for category in {o["category"] for o in all_orders}:
            data = client.get("/api/orders", params={"category": category}).json()
            expected = [o for o in all_orders if o["category"] == category]
            assert len(data) == len(expected) > 0
            assert all(o["category"] == category for o in data)

    def test_filter_by_category_is_case_insensitive(self, client):
        upper = client.get("/api/orders", params={"category": "SENSORS"}).json()
        normal = client.get("/api/orders", params={"category": "Sensors"}).json()
        assert len(upper) == len(normal) > 0

    def test_filter_by_status(self, client, all_orders):
        for status in VALID_STATUSES:
            data = client.get("/api/orders", params={"status": status}).json()
            expected = [o for o in all_orders if o["status"] == status]
            assert len(data) == len(expected)
            assert all(o["status"] == status for o in data)

    def test_filter_by_month(self, client, all_orders):
        data = client.get("/api/orders", params={"month": "2025-03"}).json()
        expected = [o for o in all_orders if o["order_date"].startswith("2025-03")]
        assert len(data) == len(expected) > 0
        assert all(o["order_date"].startswith("2025-03") for o in data)

    def test_filter_by_quarter(self, client, all_orders):
        data = client.get("/api/orders", params={"month": "Q1-2025"}).json()
        q1 = ("2025-01", "2025-02", "2025-03")
        expected = [o for o in all_orders if o["order_date"][:7] in q1]
        assert len(data) == len(expected) > 0
        assert all(o["order_date"][:7] in q1 for o in data)

    def test_quarters_partition_all_orders(self, client, all_orders):
        total = sum(
            len(client.get("/api/orders", params={"month": q}).json())
            for q in ("Q1-2025", "Q2-2025", "Q3-2025", "Q4-2025")
        )
        assert total == len(all_orders)

    def test_all_value_means_no_filter(self, client, all_orders):
        params = {"warehouse": "all", "category": "all", "status": "all", "month": "all"}
        data = client.get("/api/orders", params=params).json()
        assert len(data) == len(all_orders)

    def test_combined_filters(self, client, all_orders):
        params = {"warehouse": "Tokyo", "category": "Sensors", "status": "Delivered", "month": "Q1-2025"}
        data = client.get("/api/orders", params=params).json()
        expected = [
            o for o in all_orders
            if o["warehouse"] == "Tokyo" and o["category"] == "Sensors"
            and o["status"] == "Delivered" and o["order_date"][:7] in ("2025-01", "2025-02", "2025-03")
        ]
        assert [o["id"] for o in data] == [o["id"] for o in expected]

    def test_filter_with_no_matches_returns_empty_list(self, client):
        response = client.get("/api/orders", params={"warehouse": "Nowhere"})
        assert response.status_code == 200
        assert response.json() == []


class TestOrderById:
    """GET /api/orders/{order_id}."""

    def test_get_order_by_id(self, client, all_orders):
        order = all_orders[0]
        response = client.get(f"/api/orders/{order['id']}")
        assert response.status_code == 200
        assert response.json() == order

    def test_get_nonexistent_order(self, client):
        response = client.get("/api/orders/does-not-exist")
        assert response.status_code == 404
        assert "detail" in response.json()
