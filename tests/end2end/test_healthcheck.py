"""Tests for the /_healthz and /nginx_status endpoints."""

import time

import pytest


def test_healthcheck_returns_200(session, artifacts_url):
    resp = session.get(f'{artifacts_url}/_healthz')
    assert resp.status_code == 200


def test_healthcheck_put_is_forbidden(session, artifacts_url):
    """Only GET is allowed on /_healthz; PUT returns 403."""
    resp = session.put(f'{artifacts_url}/_healthz')
    assert resp.status_code == 403


def test_nginx_status_reports_active_connections(session, artifacts_url):
    """The stub_status endpoint is reachable and reports connection counts."""
    # Retry a few times: other test fixtures may temporarily inflate the
    # active-connections count beyond 1.
    for attempt in range(10):
        resp = session.get(f'{artifacts_url}/nginx_status')
        assert resp.status_code == 200
        if 'Active connections: 1 \n' in resp.text:
            return
        time.sleep(1)
    assert False, (
        f"Expected 'Active connections: 1' in nginx_status, got:\n{resp.text}"
    )
