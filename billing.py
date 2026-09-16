# billing.py — SwytchAI Stripe Integration
import stripe
import os

# Stripe API Keys
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
STRIPE_PUBLISHABLE_KEY = os.getenv("STRIPE_PUBLISHABLE_KEY")

# Plans
PLANS = {
    "starter": {
        "name": "Starter",
        "price": "$79/mo",
        "price_id": "price_1UG2d3Cze3Qf3UT4zvcBNgX0",
        "features": [
            "Up to 10 devices",
            "Up to 3 users",
            "AI Config Assistant",
            "Approval workflows",
            "Config versioning & diff",
            "Audit trail",
            "Email notifications",
            "Email support"
        ]
    },
    "professional": {
        "name": "Professional",
        "price": "$199/mo",
        "price_id": "price_1UG2gNCze3Qf3UT4EOBD7ZkE",
        "features": [
            "Up to 50 devices",
            "Up to 15 users",
            "Everything in Starter, plus:",
            "Bulk operations",
            "Scheduled backups",
            "Compliance scanner",
            "Config templates",
            "Webhooks & REST API",
            "PDF reports & CSV export",
            "Priority support"
        ]
    },
    "enterprise": {
        "name": "Enterprise",
        "price": "Custom",
        "price_id": None,
        "features": [
            "Unlimited devices",
            "Unlimited users",
            "Everything in Professional, plus:",
            "White-label branding",
            "Custom integrations",
            "Dedicated support",
            "SLA guarantee"
        ]
    }
}


def create_checkout_session(plan_key, org_id, username, success_url, cancel_url):
    """Creates a Stripe Checkout session for subscription."""
    plan = PLANS.get(plan_key)
    if not plan:
        return None

    try:
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{
                "price": plan["price_id"],
                "quantity": 1,
            }],
            mode="subscription",
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={
                "org_id": str(org_id),
                "username": username,
                "plan": plan_key,
            },
            subscription_data={
                "trial_period_days": 14,
            },
        )
        return session
    except Exception as e:
        print(f"Stripe error: {e}")
        return None


def create_billing_portal_session(stripe_customer_id, return_url):
    """Creates a Stripe Billing Portal session so users can manage subscription."""
    try:
        session = stripe.billing_portal.Session.create(
            customer=stripe_customer_id,
            return_url=return_url,
        )
        return session
    except Exception as e:
        print(f"Stripe portal error: {e}")
        return None


def get_subscription_status(stripe_customer_id):
    """Gets the current subscription status for a customer."""
    try:
        subscriptions = stripe.Subscription.list(
            customer=stripe_customer_id,
            status="all",
            limit=1,
        )
        if subscriptions.data:
            sub = subscriptions.data[0]
            return {
                "status": sub.status,
                "plan": sub.metadata.get("plan", "unknown"),
                "current_period_end": sub.current_period_end,
                "cancel_at_period_end": sub.cancel_at_period_end,
                "trial_end": sub.trial_end,
            }
        return None
    except Exception as e:
        print(f"Stripe status error: {e}")
        return None
