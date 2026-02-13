"""Tests for audit logging system."""

import logging

import pytest
from django.test import override_settings

import djust_tenants.audit as audit_module
from djust_tenants.audit import (
    AuditEvent,
    CallbackAuditBackend,
    LoggingAuditBackend,
    _backend_cache,  # noqa: F401
    audit_action,
    emit_audit,
    get_audit_backend,
)


@pytest.fixture(autouse=True)
def reset_backend_cache():
    """Clear backend cache between tests."""
    audit_module._backend_cache = None
    yield
    audit_module._backend_cache = None


class TestAuditEvent:
    """Tests for AuditEvent dataclass."""

    def test_create_event(self):
        event = AuditEvent(
            timestamp=1000.0,
            event_type="tenant_resolved",
            action="resolve",
            tenant_id="acme",
        )
        assert event.event_type == "tenant_resolved"
        assert event.tenant_id == "acme"
        assert event.severity == "info"

    def test_event_defaults(self):
        event = AuditEvent(timestamp=1000.0, event_type="test", action="test")
        assert event.tenant_id is None
        assert event.user_id is None
        assert event.resource is None
        assert event.detail is None
        assert event.ip_address is None
        assert event.severity == "info"


class TestLoggingAuditBackend:
    """Tests for LoggingAuditBackend."""

    def test_emit_logs_info(self, caplog):
        backend = LoggingAuditBackend()
        event = AuditEvent(
            timestamp=1000.0,
            event_type="tenant_resolved",
            action="resolve",
            tenant_id="acme",
            severity="info",
        )
        with caplog.at_level(logging.INFO, logger="djust_tenants.audit"):
            backend.emit(event)
        assert "tenant_resolved" in caplog.text
        assert "acme" in caplog.text

    def test_emit_logs_warning(self, caplog):
        backend = LoggingAuditBackend()
        event = AuditEvent(
            timestamp=1000.0,
            event_type="unscoped_access",
            action="unscoped",
            severity="warning",
        )
        with caplog.at_level(logging.WARNING, logger="djust_tenants.audit"):
            backend.emit(event)
        assert "unscoped_access" in caplog.text


class TestCallbackAuditBackend:
    """Tests for CallbackAuditBackend."""

    def test_callback_receives_event(self):
        events = []
        backend = CallbackAuditBackend(events.append)
        event = AuditEvent(
            timestamp=1000.0,
            event_type="test",
            action="do_thing",
            tenant_id="acme",
        )
        backend.emit(event)
        assert len(events) == 1
        assert events[0].tenant_id == "acme"


class TestGetAuditBackend:
    """Tests for get_audit_backend()."""

    def test_default_is_logging(self):
        backend = get_audit_backend()
        assert isinstance(backend, LoggingAuditBackend)

    @override_settings(DJUST_TENANTS={"AUDIT_BACKEND": "logging"})
    def test_explicit_logging(self):
        backend = get_audit_backend()
        assert isinstance(backend, LoggingAuditBackend)

    @override_settings(
        DJUST_TENANTS={
            "AUDIT_BACKEND": "callback",
            "AUDIT_CALLBACK": "tests.test_audit.dummy_callback",
        }
    )
    def test_callback_backend(self):
        backend = get_audit_backend()
        assert isinstance(backend, CallbackAuditBackend)

    @override_settings(DJUST_TENANTS={"AUDIT_BACKEND": "callback"})
    def test_callback_missing_path_raises(self):
        with pytest.raises(ValueError, match="AUDIT_CALLBACK"):
            get_audit_backend()

    def test_backend_is_cached(self):
        b1 = get_audit_backend()
        b2 = get_audit_backend()
        assert b1 is b2


class TestEmitAudit:
    """Tests for emit_audit() helper."""

    def test_emit_creates_event(self, caplog):
        with caplog.at_level(logging.INFO, logger="djust_tenants.audit"):
            emit_audit(
                "tenant_resolved",
                tenant_id="acme",
                action="resolve",
            )
        assert "tenant_resolved" in caplog.text

    @override_settings(
        DJUST_TENANTS={
            "AUDIT_BACKEND": "callback",
            "AUDIT_CALLBACK": "tests.test_audit.dummy_callback",
        }
    )
    def test_emit_sends_to_callback(self):
        _captured.clear()
        emit_audit(
            "test_event",
            tenant_id="acme",
            action="test",
            severity="warning",
        )
        assert len(_captured) == 1
        assert _captured[0].severity == "warning"


class TestAuditActionDecorator:
    """Tests for @audit_action decorator."""

    def test_decorator_emits_event(self, caplog):
        @audit_action(action="do_thing", resource="item")
        def my_handler():
            return 42

        with caplog.at_level(logging.INFO, logger="djust_tenants.audit"):
            result = my_handler()

        assert result == 42
        assert "do_thing" in caplog.text

    def test_decorator_uses_function_name(self, caplog):
        @audit_action()
        def delete_item():
            return True

        with caplog.at_level(logging.INFO, logger="djust_tenants.audit"):
            delete_item()

        assert "delete_item" in caplog.text

    def test_decorator_preserves_function_name(self):
        @audit_action(action="test")
        def my_func():
            pass

        assert my_func.__name__ == "my_func"


# Module-level callback for tests
_captured = []


def dummy_callback(event):
    _captured.append(event)
