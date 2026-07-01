from __future__ import annotations

import os
from typing import Any, Dict

from saas.usage import UsageMeter


class BillingService:
    """Stripe-backed subscription + usage billing wrapper."""

    def __init__(self, usage_meter: UsageMeter) -> None:
        self._usage_meter = usage_meter
        self._stripe_api_key = os.getenv("STRIPE_API_KEY", "")
        self._unit_price_cents = int(os.getenv("HOARE_USAGE_UNIT_PRICE_CENTS", "5"))

    def create_checkout_session(
        self,
        tenant_id: str,
        price_id: str,
        success_url: str,
        cancel_url: str,
    ) -> Dict[str, Any]:
        if not self._stripe_api_key:
            return {
                "mode": "mock",
                "tenant_id": tenant_id,
                "message": "Set STRIPE_API_KEY to enable live checkout sessions.",
            }

        import stripe  # type: ignore

        stripe.api_key = self._stripe_api_key
        session = stripe.checkout.Session.create(
            mode="subscription",
            line_items=[{"price": price_id, "quantity": 1}],
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={"tenant_id": tenant_id},
        )
        return {
            "mode": "live",
            "tenant_id": tenant_id,
            "checkout_session_id": session["id"],
            "checkout_url": session.get("url"),
        }

    def report_usage(self, tenant_id: str, units: int) -> Dict[str, Any]:
        self._usage_meter.record_usage_units(tenant_id, units)
        summary = self._usage_meter.summary(tenant_id)
        estimated_amount_cents = summary["usage_units_total"] * self._unit_price_cents
        return {
            "tenant_id": tenant_id,
            "usage_units_total": summary["usage_units_total"],
            "unit_price_cents": self._unit_price_cents,
            "estimated_amount_cents": estimated_amount_cents,
        }

