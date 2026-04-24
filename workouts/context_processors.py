from django.conf import settings


def environment(request):
    """Injecte l'environnement courant dans tous les templates."""
    env = getattr(settings, "ENVIRONMENT", "production")
    return {
        "ENVIRONMENT": env,
        "IS_DEV": env != "production",
    }
