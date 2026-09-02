"""Filtros y tags globales de PL_SGE (registrados como builtins)."""
from __future__ import annotations

import json

from django import template
from django.utils.safestring import mark_safe

from core.configuration.icons import svg as render_icon

register = template.Library()


@register.simple_tag
def icon(name, size=20, css_class="icon"):
    return mark_safe(render_icon(name, int(size), css_class))


@register.filter(name="icon")
def icon_filter(name):
    return mark_safe(render_icon(name))


@register.simple_tag(takes_context=True)
def can(context, module_code, action="view"):
    from config.permissions import user_has_permission

    request = context.get("request")
    user = getattr(request, "user", None)
    return user_has_permission(user, module_code, action)


@register.filter(name="jsonify")
def jsonify(value):
    return mark_safe(json.dumps(value, ensure_ascii=False, default=str))


@register.filter(name="initials")
def initials(value):
    text = str(value or "").strip()
    if not text:
        return "?"
    parts = [p for p in text.split(" ") if p]
    return "".join(p[0] for p in parts[:2]).upper()


@register.filter(name="money")
def money(value):
    try:
        return f"$ {float(value):,.0f}".replace(",", ".")
    except (TypeError, ValueError):
        return value


@register.filter(name="grade")
def grade(value, decimals=1):
    try:
        return f"{float(value):.{int(decimals)}f}"
    except (TypeError, ValueError):
        return "-"


@register.filter(name="percent")
def percent(value, total):
    try:
        total = float(total)
        if total == 0:
            return "0%"
        return f"{(float(value) / total) * 100:.1f}%"
    except (TypeError, ValueError, ZeroDivisionError):
        return "0%"


@register.filter(name="get_item")
def get_item(mapping, key):
    if hasattr(mapping, "get"):
        return mapping.get(key)
    return None


@register.simple_tag
def badge(text, tone="neutral"):
    return mark_safe(f'<span class="badge badge--{tone}">{text}</span>')


@register.simple_tag(takes_context=True)
def active_url(context, *url_names):
    request = context.get("request")
    if not request:
        return ""
    match = getattr(request, "resolver_match", None)
    if not match:
        return ""
    current = f"{match.namespace}:{match.url_name}" if match.namespace else match.url_name
    return "is-active" if current in url_names else ""


@register.filter(name="split")
def split_filter(value, separator=","):
    return str(value or "").split(separator)


@register.simple_tag
def icons_json():
    """Expone el set de iconos SVG al runtime JavaScript."""
    from core.configuration.icons import ICONS

    return mark_safe(json.dumps(ICONS))


@register.simple_tag(takes_context=True)
def query_string(context, **kwargs):
    request = context.get("request")
    params = request.GET.copy() if request else {}
    for key, value in kwargs.items():
        if value is None:
            params.pop(key, None)
        else:
            params[key] = value
    return f"?{params.urlencode()}" if params else ""
