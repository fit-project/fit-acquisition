from __future__ import annotations

import sys
import threading
import uuid
from dataclasses import dataclass

from PySide6.QtCore import QObject, Signal


class PrivilegeDeniedError(RuntimeError):
    """Raised when the user refuses or cancels privileged operations."""


@dataclass(frozen=True)
class PrivilegeRequest:
    request_id: str
    operation: str
    title: str
    message: str

    def as_dict(self) -> dict[str, str]:
        return {
            "request_id": self.request_id,
            "operation": self.operation,
            "title": self.title,
            "message": self.message,
        }


class PrivilegeAuthorization(QObject):
    """One shared, thread-safe authorization decision per acquisition."""

    requested = Signal(object)

    def __init__(self) -> None:
        super().__init__()
        self._condition = threading.Condition()
        self._request: PrivilegeRequest | None = None
        self._decision: bool | None = None
        self._cancelled = False

    def require(self, operation: str) -> None:
        if sys.platform != "linux":
            return
        emit_request = None
        with self._condition:
            if self._cancelled:
                raise PrivilegeDeniedError("Privilege request was cancelled")
            if self._decision is True:
                return
            if self._decision is False:
                raise PrivilegeDeniedError("Privileged operations were refused")
            if self._request is None:
                self._request = PrivilegeRequest(
                    request_id=uuid.uuid4().hex,
                    operation=operation,
                    title="Administrative privileges required",
                    message="FIT needs administrative privileges for network capture operations.",
                )
                emit_request = self._request.as_dict()
        if emit_request is not None:
            self.requested.emit(emit_request)
        with self._condition:
            while self._decision is None and not self._cancelled:
                self._condition.wait()
            if self._cancelled or self._decision is not True:
                raise PrivilegeDeniedError("Privileged operations were refused or cancelled")

    def respond(self, request_id: str, approved: bool) -> bool:
        with self._condition:
            if (
                self._request is None
                or self._request.request_id != request_id
                or self._decision is not None
                or self._cancelled
            ):
                return False
            self._decision = bool(approved)
            self._condition.notify_all()
            return True

    def cancel(self) -> None:
        with self._condition:
            self._cancelled = True
            self._condition.notify_all()

    def reset(self) -> None:
        with self._condition:
            self._request = None
            self._decision = None
            self._cancelled = False
