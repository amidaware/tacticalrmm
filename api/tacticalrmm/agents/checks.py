"""Django system checks for the file-transfer subsystem.

These guard the timing relationships the chunked transfer protocol relies on.
If an operator overrides one of the constants in a way that breaks the ladder,
`manage.py check` (run on startup/migrate) fails fast with a clear message
instead of the protocol silently misbehaving at runtime.
"""

from django.core.checks import Error, register


@register()
def file_transfer_timeout_ladder_check(app_configs, **kwargs):
    from django.conf import settings

    from tacticalrmm.constants import (
        FILE_TRANSFER_AGENT_ACK_WAIT_SECONDS,
        FILE_TRANSFER_CHUNK_SIZE_MAX,
        FILE_TRANSFER_PIPELINE_DEPTH,
        FILE_TRANSFER_REDIS_CHUNK_TTL_SECONDS,
    )

    errors = []

    if FILE_TRANSFER_REDIS_CHUNK_TTL_SECONDS <= FILE_TRANSFER_AGENT_ACK_WAIT_SECONDS:
        errors.append(
            Error(
                "FILE_TRANSFER_REDIS_CHUNK_TTL_SECONDS must be greater than the "
                "agent's client-ACK wait so a buffered download chunk does not "
                "expire while the agent's stream is still waiting on it.",
                hint=(
                    f"CHUNK_TTL={FILE_TRANSFER_REDIS_CHUNK_TTL_SECONDS}, "
                    f"agent ACK wait={FILE_TRANSFER_AGENT_ACK_WAIT_SECONDS}"
                ),
                id="agents.E002",
            )
        )

    data_upload_max = getattr(settings, "DATA_UPLOAD_MAX_MEMORY_SIZE", None)
    if data_upload_max is not None and data_upload_max < FILE_TRANSFER_CHUNK_SIZE_MAX:
        errors.append(
            Error(
                "DATA_UPLOAD_MAX_MEMORY_SIZE must be >= FILE_TRANSFER_CHUNK_SIZE_MAX "
                "so the largest negotiated chunk body is not rejected by Django "
                "before the view runs.",
                hint=(
                    f"DATA_UPLOAD_MAX_MEMORY_SIZE={data_upload_max}, "
                    f"FILE_TRANSFER_CHUNK_SIZE_MAX={FILE_TRANSFER_CHUNK_SIZE_MAX}"
                ),
                id="agents.E003",
            )
        )

    if FILE_TRANSFER_PIPELINE_DEPTH < 1:
        errors.append(
            Error(
                "FILE_TRANSFER_PIPELINE_DEPTH must be >= 1 (the sender must be "
                "allowed at least one chunk in flight).",
                hint=f"FILE_TRANSFER_PIPELINE_DEPTH={FILE_TRANSFER_PIPELINE_DEPTH}",
                id="agents.E004",
            )
        )

    return errors
