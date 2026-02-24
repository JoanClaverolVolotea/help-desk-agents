from __future__ import annotations

import re

SUPPORTED_LANGUAGES = {"en", "es"}

_TOKEN_PATTERN = re.compile(r"[A-Za-zÀ-ÿ']+")
_SPANISH_CHAR_PATTERN = re.compile(r"[áéíóúñü¿¡]")

_SPANISH_HINT_WORDS = {
    "acceso",
    "agente",
    "alta",
    "ayuda",
    "categoria",
    "categorias",
    "con",
    "contraseña",
    "correo",
    "crear",
    "cuenta",
    "de",
    "el",
    "en",
    "es",
    "gracias",
    "hola",
    "incidencia",
    "necesito",
    "nuevo",
    "para",
    "por",
    "porfavor",
    "problema",
    "publicar",
    "que",
    "restablecer",
    "soporte",
    "ticket",
    "usuario",
}

_ENGLISH_HINT_WORDS = {
    "access",
    "account",
    "agent",
    "and",
    "archive",
    "case",
    "category",
    "create",
    "for",
    "help",
    "hello",
    "issue",
    "login",
    "need",
    "new",
    "password",
    "please",
    "publish",
    "request",
    "reset",
    "restore",
    "support",
    "the",
    "ticket",
    "user",
    "with",
}

_TEXT_BY_LANGUAGE = {
    "en": {
        "handoff_event": "Handed off from {source} to {target}",
        "tool_call_event": "Calling tool {tool_name}",
        "skip_event": "Skipping {item_class}",
        "no_categories_available": "No categories available.",
        "validation_errors_prefix": "Validation errors: {errors}",
        "category_draft_created": (
            "Category draft created. category_id={category_id}, slug={slug}, "
            "draft_version={draft_version}."
        ),
        "category_published": (
            "Category published. category_id={category_id}, version={version}."
        ),
        "category_status_line": (
            "- {category_id} | {display_name} "
            "(published={published_version}, draft={draft_version}, archived={archived})"
        ),
        "step_verify_requester": "Verify requester identity before account changes.",
        "step_reset_ecrew_access": "Reset eCrew access and unlock account.",
        "step_provision_email": "Provision company email account.",
        "step_provision_efos": "Provision EFOS platform access.",
        "step_provision_pelesys": "Provision PELESYS learning profile.",
        "step_append_resolution_note": "Append a closure note to the ticket.",
        "step_manual_instruction": "Write a deterministic operator-facing instruction.",
        "workflow_verify_requester": (
            "[verify_requester] Requester verified for ticket {ticket_id} as "
            "{requester_name}."
        ),
        "workflow_reset_ecrew_access": (
            "[reset_ecrew_access] eCrew account reset completed for ticket {ticket_id}."
        ),
        "workflow_provision_email": (
            "[provision_email] Mailbox {mailbox}@volotea.example provisioned for ticket "
            "{ticket_id}."
        ),
        "workflow_provision_efos": (
            "[provision_efos] EFOS access granted to {employee_name} for ticket "
            "{ticket_id}."
        ),
        "workflow_provision_pelesys": (
            "[provision_pelesys] PELESYS profile created for {employee_name} on ticket "
            "{ticket_id}."
        ),
        "workflow_default_resolution_note": "Resolution note added.",
        "workflow_default_manual_instruction": "Manual instruction completed.",
        "workflow_unsupported_step": "[{step_id}] Unsupported step id.",
        "workflow_closure": (
            "[closure] Workflow completed with deterministic execution for ticket "
            "{ticket_id}."
        ),
    },
    "es": {
        "handoff_event": "Transferido de {source} a {target}",
        "tool_call_event": "Llamando a la herramienta {tool_name}",
        "skip_event": "Omitiendo {item_class}",
        "no_categories_available": "No hay categorias disponibles.",
        "validation_errors_prefix": "Errores de validacion: {errors}",
        "category_draft_created": (
            "Borrador de categoria creado. category_id={category_id}, slug={slug}, "
            "draft_version={draft_version}."
        ),
        "category_published": (
            "Categoria publicada. category_id={category_id}, version={version}."
        ),
        "category_status_line": (
            "- {category_id} | {display_name} "
            "(publicada={published_version}, borrador={draft_version}, archivada={archived})"
        ),
        "step_verify_requester": "Verificar identidad del solicitante antes de cambios.",
        "step_reset_ecrew_access": "Restablecer acceso de eCrew y desbloquear cuenta.",
        "step_provision_email": "Provisionar cuenta de correo corporativo.",
        "step_provision_efos": "Provisionar acceso a la plataforma EFOS.",
        "step_provision_pelesys": "Provisionar perfil de aprendizaje en PELESYS.",
        "step_append_resolution_note": "Anadir nota de cierre al ticket.",
        "step_manual_instruction": "Escribir instruccion determinista para el operador.",
        "workflow_verify_requester": (
            "[verify_requester] Solicitante verificado para el ticket {ticket_id} "
            "como {requester_name}."
        ),
        "workflow_reset_ecrew_access": (
            "[reset_ecrew_access] Restablecimiento de cuenta eCrew completado para el "
            "ticket {ticket_id}."
        ),
        "workflow_provision_email": (
            "[provision_email] Buzon {mailbox}@volotea.example aprovisionado para el "
            "ticket {ticket_id}."
        ),
        "workflow_provision_efos": (
            "[provision_efos] Acceso EFOS concedido a {employee_name} para el ticket "
            "{ticket_id}."
        ),
        "workflow_provision_pelesys": (
            "[provision_pelesys] Perfil PELESYS creado para {employee_name} en el "
            "ticket {ticket_id}."
        ),
        "workflow_default_resolution_note": "Nota de resolucion anadida.",
        "workflow_default_manual_instruction": "Instruccion manual completada.",
        "workflow_unsupported_step": "[{step_id}] Id de paso no soportado.",
        "workflow_closure": (
            "[closure] Flujo completado con ejecucion determinista para el ticket "
            "{ticket_id}."
        ),
    },
}


def normalize_language(code: str | None) -> str:
    if not code:
        return "en"

    normalized = code.strip().lower().replace("_", "-")
    if normalized.startswith("es"):
        return "es"
    return "en"


def detect_user_language(text: str, previous_language: str | None) -> str:
    previous = normalize_language(previous_language)
    stripped = text.strip()
    if not stripped:
        return previous

    lowered = stripped.lower()
    tokens = _TOKEN_PATTERN.findall(lowered)

    spanish_score = 0
    english_score = 0

    if _SPANISH_CHAR_PATTERN.search(lowered):
        spanish_score += 2

    spanish_score += sum(1 for token in tokens if token in _SPANISH_HINT_WORDS)
    english_score += sum(1 for token in tokens if token in _ENGLISH_HINT_WORDS)

    if spanish_score > english_score:
        return "es"
    if english_score > spanish_score:
        return "en"
    return previous


def translate_backend_text(key: str, language: str, **kwargs: object) -> str:
    normalized = normalize_language(language)
    localized_map = _TEXT_BY_LANGUAGE.get(normalized, _TEXT_BY_LANGUAGE["en"])
    template = localized_map.get(key) or _TEXT_BY_LANGUAGE["en"].get(key)
    if template is None:
        raise KeyError(key)
    return template.format(**kwargs)
