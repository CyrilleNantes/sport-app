from django.conf import settings


def environment(request):
    """Injecte l'environnement courant dans tous les templates."""
    env = getattr(settings, "APP_ENV", "production")
    return {
        "APP_ENV": env,
        "IS_DEV": env != "production",
    }
