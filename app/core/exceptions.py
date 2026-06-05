"""
app/core/exceptions.py
───────────────────────
Custom business exception hierarchy and global FastAPI exception handlers.

Design:
  - All domain errors subclass BusinessError.
  - A single exception_handler in main.py catches BusinessError and returns
    a consistent JSON envelope: { "error": "CODE", "message": "..." }.
  - This means routers never need try/except for business logic — they just
    let exceptions propagate up to the handler.
"""

from __future__ import annotations

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse


# ── Base Business Exception ────────────────────────────────────────────────

class BusinessError(Exception):
    """
    Base class for all domain-level exceptions.
    Subclass this — never raise BusinessError directly.
    """

    def __init__(self, code: str, message: str, http_status: int = 400) -> None:
        self.code = code
        self.message = message
        self.http_status = http_status
        super().__init__(message)


# ── Auth Exceptions ────────────────────────────────────────────────────────

class InvalidCredentialsError(BusinessError):
    def __init__(self) -> None:
        super().__init__(
            code="INVALID_CREDENTIALS",
            message="Invalid Member ID or password.",
            http_status=status.HTTP_401_UNAUTHORIZED,
        )


class AccountLockedError(BusinessError):
    def __init__(self, locked_until_str: str) -> None:
        super().__init__(
            code="ACCOUNT_LOCKED",
            message=(
                f"Account locked due to too many failed login attempts. "
                f"Try again after {locked_until_str} UTC."
            ),
            http_status=status.HTTP_423_LOCKED,
        )


class EmailAlreadyRegisteredError(BusinessError):
    def __init__(self) -> None:
        super().__init__(
            code="EMAIL_ALREADY_REGISTERED",
            message="An account with this email already exists.",
            http_status=status.HTTP_409_CONFLICT,
        )


class InvalidRefreshTokenError(BusinessError):
    def __init__(self) -> None:
        super().__init__(
            code="INVALID_REFRESH_TOKEN",
            message="Invalid or expired refresh token. Please log in again.",
            http_status=status.HTTP_401_UNAUTHORIZED,
        )


# ── Attendance Exceptions ──────────────────────────────────────────────────

class AlreadyCheckedInError(BusinessError):
    def __init__(self, session: str, checked_in_at: str) -> None:
        super().__init__(
            code="ALREADY_CHECKED_IN",
            message=f"You have already marked {session} attendance today at {checked_in_at}.",
            http_status=status.HTTP_409_CONFLICT,
        )


class MembershipExpiredError(BusinessError):
    def __init__(self, expired_on: str) -> None:
        super().__init__(
            code="MEMBERSHIP_EXPIRED",
            message=(
                f"Your membership expired on {expired_on}. "
                f"Please renew to mark attendance."
            ),
            http_status=status.HTTP_403_FORBIDDEN,
        )


class MembershipPendingError(BusinessError):
    def __init__(self) -> None:
        super().__init__(
            code="MEMBERSHIP_PENDING",
            message="Your membership is pending admin approval. Please contact the front desk.",
            http_status=status.HTTP_403_FORBIDDEN,
        )


# ── Payment Exceptions ─────────────────────────────────────────────────────

class PendingPaymentExistsError(BusinessError):
    def __init__(self) -> None:
        super().__init__(
            code="PENDING_PAYMENT_EXISTS",
            message=(
                "You already have a pending payment request awaiting admin approval. "
                "Please wait before submitting another."
            ),
            http_status=status.HTTP_409_CONFLICT,
        )


# ── Generic Exceptions ─────────────────────────────────────────────────────

class ResourceNotFoundError(BusinessError):
    def __init__(self, resource: str = "Resource") -> None:
        super().__init__(
            code="NOT_FOUND",
            message=f"{resource} not found.",
            http_status=status.HTTP_404_NOT_FOUND,
        )


# ── Exception Handler Registration ────────────────────────────────────────

def register_exception_handlers(app: FastAPI) -> None:
    """
    Register global exception handlers on the FastAPI app.
    Call this in main.py before including routers.
    """

    @app.exception_handler(BusinessError)
    async def business_error_handler(
        request: Request, exc: BusinessError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=exc.http_status,
            content={"error": exc.code, "message": exc.message},
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(
        request: Request, exc: HTTPException
    ) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": "REQUEST_ERROR", "message": exc.detail},
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        # In production, never expose internal error details
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred. Please try again.",
            },
        )
