
import pytest
import requests

BASE_INVOICES = "/api/v1/billing/invoices/"


@pytest.mark.smoke
@pytest.mark.critical
def test_create_draft_invoice_for_patient(base_url, biller_headers, billing_test_patient):
    resp = requests.post(f"{base_url}{BASE_INVOICES}", json={"patient": billing_test_patient["id"]}, headers=biller_headers)
    assert resp.status_code == 201, resp.text
    assert resp.json()["status"] == "DRAFT"


@pytest.mark.critical
def test_issue_invoice_changes_status(base_url, biller_headers, draft_invoice):
    resp = requests.post(f"{base_url}{BASE_INVOICES}{draft_invoice['id']}/issue/", headers=biller_headers)
    assert resp.status_code == 200, resp.text

    check = requests.get(f"{base_url}{BASE_INVOICES}{draft_invoice['id']}/", headers=biller_headers)
    assert check.json()["status"] == "ISSUED", "Invoice should reflect ISSUED status after the issue action"


@pytest.mark.critical
def test_invoices_summary_is_server_side_aggregate(base_url, biller_headers):
    resp = requests.get(f"{base_url}{BASE_INVOICES}summary/", headers=biller_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), dict), "Summary should be one aggregate object, not a list"


@pytest.mark.regression
@pytest.mark.negative
def test_cancel_already_cancelled_invoice_is_rejected(base_url, biller_headers, draft_invoice):
    first_cancel = requests.post(f"{base_url}{BASE_INVOICES}{draft_invoice['id']}/cancel/", headers=biller_headers)
    assert first_cancel.status_code == 200, first_cancel.text

    second_cancel = requests.post(f"{base_url}{BASE_INVOICES}{draft_invoice['id']}/cancel/", headers=biller_headers)
    assert second_cancel.status_code == 400, (
        "Cancelling an already-cancelled invoice should be rejected, not silently accepted"
    )


@pytest.mark.regression
@pytest.mark.negative
def test_create_invoice_without_patient_returns_400(base_url, biller_headers):
    resp = requests.post(f"{base_url}{BASE_INVOICES}", json={}, headers=biller_headers)
    assert resp.status_code == 400










    