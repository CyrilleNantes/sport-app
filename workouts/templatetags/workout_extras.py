from datetime import date as date_type

from django import template

register = template.Library()


@register.filter
def get_item(mapping, key):
    return mapping.get(key)


@register.filter
def format_duration(value):
    """timedelta → '44m 50s' ou '1h 24m'"""
    if value is None:
        return "-"
    total = int(value.total_seconds())
    h = total // 3600
    m = (total % 3600) // 60
    s = total % 60
    if h > 0:
        return f"{h}h {m:02d}m"
    return f"{m}m {s:02d}s"


@register.filter
def relative_date(value):
    """date → 'Aujourd'hui', 'Demain', 'Hier', ou 'dd/mm'"""
    if value is None:
        return "-"
    today = date_type.today()
    delta = (value - today).days
    if delta == 0:
        return "Aujourd'hui"
    if delta == 1:
        return "Demain"
    if delta == -1:
        return "Hier"
    return value.strftime("%d/%m")
