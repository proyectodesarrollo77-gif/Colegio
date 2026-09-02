"""Utilidades compartidas de autenticacion."""


def get_client_ip(request):
    if request is None:
        return None
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def get_user_agent(request):
    if request is None:
        return ""
    return (request.META.get("HTTP_USER_AGENT") or "")[:320]


def guess_device(user_agent: str) -> str:
    agent = (user_agent or "").lower()
    if "mobile" in agent or "android" in agent or "iphone" in agent:
        return "Movil"
    if "tablet" in agent or "ipad" in agent:
        return "Tablet"
    if not agent:
        return "Desconocido"
    return "Escritorio"


def browser_name(user_agent: str) -> str:
    agent = (user_agent or "").lower()
    for token, label in (
        ("edg", "Edge"),
        ("opr", "Opera"),
        ("chrome", "Chrome"),
        ("safari", "Safari"),
        ("firefox", "Firefox"),
    ):
        if token in agent:
            return label
    return "Otro"
