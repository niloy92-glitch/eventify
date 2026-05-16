"""Template context processors for the `users` app.

Provides lightweight site-wide metrics used by templates.
"""
import logging
from django.apps import apps
from django.contrib.auth import get_user_model

logger = logging.getLogger(__name__)


def site_stats(request):
    """Return small site metrics for the layout/marketing tiles.

    Keeps the work simple and robust: failures return zeroes so templates
    continue rendering in development without a DB.
    """
    site_clients_count = 0
    site_vendors_count = 0
    try:
        user_model = get_user_model()
        site_clients_count = user_model.objects.filter(
            role="client", is_active=True
        ).count()
        site_vendors_count = user_model.objects.filter(
            role="vendor", is_active=True
        ).count()
    except Exception as e:
        logger.error(f"Failed to fetch site user counts in context processor: {e}")

    site_events_count = 0
    try:
        Event = apps.get_model("events", "Event")
        site_events_count = Event.objects.count()
    except Exception as e:
        logger.error(f"Failed to fetch site events count in context processor: {e}")

    return {
        "site_clients_count": site_clients_count,
        "site_vendors_count": site_vendors_count,
        "site_events_count": site_events_count,
    }
