import datetime as dt
import json

from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone as djangotime
from rest_framework import status
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from agents.file_transfer_relay import (
    clear_download_session_redis,
    clear_upload_session_redis,
    delete_upload_chunk,
    get_accepted_offset,
    get_download_ack,
    get_download_offered_offset,
    get_upload_ack,
    peek_upload_chunk,
    pipeline_depth_full,
    signal_upload_ack,
    store_download_chunk,
)
from agents.models import Agent, FileTransferSession
from agents.utils import parse_upload_content_range
from tacticalrmm.constants import (
    AGENT_DEFER,
    FILE_TRANSFER_ACK_CHECKPOINT_BYTES,
    FILE_TRANSFER_CHUNK_SIZE_MAX,
    FILE_TRANSFER_IDLE_EXPIRE_MINUTES,
    FILE_TRANSFER_PIPELINE_DEPTH,
    FILE_TRANSFER_SESSION_TTL_HOURS,
    FileTransferOperation,
    FileTransferStatus,
)
from tacticalrmm.helpers import notify_error, notify_retryable
from tacticalrmm.logger import logger

_TERMINAL_STATUSES = (
    FileTransferStatus.COMPLETED,
    FileTransferStatus.FAILED,
    FileTransferStatus.CANCELLED,
    FileTransferStatus.EXPIRED,
)
_MAX_WARNINGS_CHARS = 8192
_MAX_BYTE_COUNT = 2**63 - 1


def _agent_body_str(request, key: str) -> str:
    if not isinstance(request.data, dict):
        return ""
    value = request.data.get(key)
    if value is None:
        return ""
    return str(value).replace("\x00", "").strip()


def _warnings_json(warnings) -> str:
    """JSON list of the agent's warnings, dropping items so it fits the cap."""
    if not isinstance(warnings, list) or not warnings:
        return ""
    items = [str(w).replace("\x00", "") for w in warnings]
    while items:
        value = json.dumps(items)
        if len(value) <= _MAX_WARNINGS_CHARS:
            return value
        items.pop()
    return ""


class FileTransferNextChunk(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, session_id):
        agent = get_object_or_404(
            Agent.objects.defer(*AGENT_DEFER),
            user=request.user,
        )

        session = get_object_or_404(
            FileTransferSession,
            session_id=session_id,
            agent=agent,
            operation=FileTransferOperation.UPLOAD,
        )

        if session.expires_at <= djangotime.now():
            from agents.views import _expire_transfer_session

            _expire_transfer_session(session, agent)
            return notify_error("Upload session has expired")

        if session.status not in (
            FileTransferStatus.AGENT_READY,
            FileTransferStatus.TRANSFERRING,
        ):
            return notify_error("Upload session is not ready for chunk transfer")

        redis_committed = get_upload_ack(session.session_id)
        committed = max(session.committed_offset, redis_committed or 0)

        chunk = peek_upload_chunk(session.session_id, committed)
        if chunk is None:
            return Response("No pending chunk", status=status.HTTP_404_NOT_FOUND)

        response = HttpResponse(
            chunk.data,
            content_type="application/octet-stream",
        )
        response["Content-Range"] = (
            f"bytes {chunk.start}-{chunk.end}/{session.total_size}"
        )
        response["X-Chunk-Start"] = str(chunk.start)
        response["X-Chunk-End"] = str(chunk.end)
        return response


class FileTransferAck(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, session_id):
        agent = get_object_or_404(
            Agent.objects.defer(*AGENT_DEFER),
            user=request.user,
        )

        session = get_object_or_404(
            FileTransferSession,
            session_id=session_id,
            agent=agent,
            operation=FileTransferOperation.UPLOAD,
        )

        if session.expires_at <= djangotime.now():
            from agents.views import _expire_transfer_session

            _expire_transfer_session(session, agent)
            return notify_error("Upload session has expired")

        if session.status not in (
            FileTransferStatus.AGENT_READY,
            FileTransferStatus.TRANSFERRING,
        ):
            return notify_error("Upload session is not ready for chunk transfer")

        try:
            committed_offset = int(request.data.get("committed_offset"))
        except (AttributeError, TypeError, ValueError):
            return notify_error("committed_offset must be a positive integer")

        if committed_offset < 1 or committed_offset > session.total_size:
            return notify_error("committed_offset is out of range")

        redis_committed = get_upload_ack(session.session_id)
        current_committed = max(session.committed_offset, redis_committed or 0)

        if committed_offset < current_committed:
            return notify_error("committed_offset cannot decrease")

        accepted_offset = get_accepted_offset(session.session_id)
        if accepted_offset is not None and committed_offset > accepted_offset:
            return notify_error("committed_offset exceeds accepted_offset")

        if committed_offset == current_committed:
            signal_upload_ack(session.session_id, committed_offset)
            return Response({"committed_offset": committed_offset})

        should_checkpoint = (
            committed_offset == session.total_size
            or committed_offset - session.committed_offset
            >= FILE_TRANSFER_ACK_CHECKPOINT_BYTES
        )
        if should_checkpoint:
            now = djangotime.now()
            update_fields = [
                "committed_offset",
                "last_ack_at",
                "expires_at",
                "updated_at",
            ]
            session.committed_offset = committed_offset
            session.last_ack_at = now
            session.expires_at = now + dt.timedelta(
                hours=FILE_TRANSFER_SESSION_TTL_HOURS
            )
            session.save(update_fields=update_fields)
            from agents.views import _mark_transfer_transferring

            _mark_transfer_transferring(session)

        delete_upload_chunk(session.session_id, current_committed)
        signal_upload_ack(session.session_id, committed_offset)

        return Response({"committed_offset": committed_offset})


def download_relay_put_state(session):
    """Return committed, offered, can_put from Redis + the session row."""
    redis_committed = get_download_ack(session.session_id)
    committed = max(session.committed_offset, redis_committed or 0)
    redis_offered = get_download_offered_offset(session.session_id)
    offered = max(redis_offered or 0, committed)
    depth_bytes = FILE_TRANSFER_PIPELINE_DEPTH * session.chunk_size
    can_put = (
        session.status
        in (
            FileTransferStatus.AGENT_READY,
            FileTransferStatus.TRANSFERRING,
        )
        and offered < session.total_size
        and not pipeline_depth_full(offered, committed, depth_bytes)
    )
    return committed, offered, can_put


class FileTransferDownloadPutChunk(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, session_id):
        agent = get_object_or_404(
            Agent.objects.defer(*AGENT_DEFER),
            user=request.user,
        )

        session = get_object_or_404(
            FileTransferSession,
            session_id=session_id,
            agent=agent,
            operation=FileTransferOperation.DOWNLOAD,
        )

        if session.expires_at <= djangotime.now():
            from agents.views import _expire_transfer_session

            _expire_transfer_session(session, agent)
            return notify_error("Download session has expired")

        if session.status in _TERMINAL_STATUSES:
            committed, offered, _can_put = download_relay_put_state(session)
            return Response(
                {
                    "session_id": str(session.session_id),
                    "status": session.status,
                    "committed_offset": committed,
                    "offered_offset": offered,
                    "chunk_size": session.chunk_size,
                    "total_size": session.total_size,
                    "can_put": False,
                }
            )

        if session.status not in (
            FileTransferStatus.AGENT_READY,
            FileTransferStatus.TRANSFERRING,
        ):
            return notify_error("Download session is not ready for chunk transfer")

        committed, offered, can_put = download_relay_put_state(session)
        return Response(
            {
                "session_id": str(session.session_id),
                "status": session.status,
                "committed_offset": committed,
                "offered_offset": offered,
                "chunk_size": session.chunk_size,
                "total_size": session.total_size,
                "can_put": can_put,
            }
        )

    def put(self, request, session_id):
        agent = get_object_or_404(
            Agent.objects.defer(*AGENT_DEFER),
            user=request.user,
        )

        session = get_object_or_404(
            FileTransferSession,
            session_id=session_id,
            agent=agent,
            operation=FileTransferOperation.DOWNLOAD,
        )

        if session.expires_at <= djangotime.now():
            from agents.views import _expire_transfer_session

            _expire_transfer_session(session, agent)
            return notify_error("Download session has expired")

        if session.status not in (
            FileTransferStatus.AGENT_READY,
            FileTransferStatus.TRANSFERRING,
        ):
            return notify_error("Download session is not ready for chunk transfer")

        content_range = request.META.get("HTTP_CONTENT_RANGE", "")
        byte_range, range_err = parse_upload_content_range(
            content_range, session.total_size
        )
        if range_err:
            return notify_error(range_err)

        start, end = byte_range
        expected_len = end - start + 1

        if expected_len < 1 or expected_len > session.chunk_size:
            return notify_error("Chunk size exceeds allowed limit")

        content_length = request.META.get("CONTENT_LENGTH")
        if content_length:
            try:
                if int(content_length) != expected_len:
                    return notify_error(
                        "Request body size does not match Content-Range"
                    )
            except ValueError:
                return notify_error("Invalid Content-Length header")

        if expected_len > FILE_TRANSFER_CHUNK_SIZE_MAX:
            return notify_error("Chunk exceeds maximum request size")

        committed, offered, can_put = download_relay_put_state(session)
        if start != offered:
            return notify_error(
                f"Chunk start offset {start} does not match expected {offered}"
            )

        if not can_put:
            session.refresh_from_db(fields=["status", "error_message"])
            if session.status == FileTransferStatus.FAILED:
                return notify_error(session.error_message or "Download failed")
            _ = request.body
            return notify_retryable(
                "Timed out waiting for client to ACK previous chunk"
            )

        chunk_data = request.body
        if len(chunk_data) != expected_len:
            return notify_error("Request body size does not match Content-Range")

        store_err = store_download_chunk(session.session_id, start, end, chunk_data)
        if store_err:
            return notify_error(store_err)

        from agents.views import _mark_transfer_transferring

        if not _mark_transfer_transferring(session):
            # cancelled or failed while the chunk was being stored
            clear_download_session_redis(session.session_id)
            return notify_error("Download session is not ready for chunk transfer")

        logger.info(
            "file_transfer download chunk stored session=%s start=%s end=%s",
            session.session_id,
            start,
            end,
        )

        return Response(
            {
                "session_id": str(session.session_id),
                "status": session.status,
                "offered_offset": end + 1,
                "committed_offset": committed,
                "chunk_start": start,
                "chunk_end": end,
                "chunk_bytes": len(chunk_data),
            }
        )


class FileTransferFail(APIView):
    """When the download stream (or other agent-side work) hits a final
    failure so the session does not sit in ``transferring`` with an empty
    error until TTL/Celery. Idempotent for already-terminal sessions."""

    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, session_id):
        agent = get_object_or_404(
            Agent.objects.defer(*AGENT_DEFER),
            user=request.user,
        )

        session = get_object_or_404(
            FileTransferSession,
            session_id=session_id,
            agent=agent,
        )

        error = _agent_body_str(request, "error")
        if not error:
            error = "Agent reported transfer failure"
        error = error[:2048]

        with transaction.atomic():
            # lock so a complete that lands at the same time is not
            # overwritten with failed.
            locked = (
                FileTransferSession.objects.select_for_update()
                .filter(pk=session.pk)
                .first()
            )
            if locked is None or locked.status in _TERMINAL_STATUSES:
                return Response(
                    {"status": locked.status if locked else session.status},
                    status=status.HTTP_409_CONFLICT,
                )
            locked.status = FileTransferStatus.FAILED
            locked.error_message = error
            locked.save(update_fields=["status", "error_message", "updated_at"])
        session = locked

        if session.operation == FileTransferOperation.DOWNLOAD:
            clear_download_session_redis(session.session_id)
        else:
            clear_upload_session_redis(session.session_id)
        logger.error(
            "file_transfer agent fail session=%s operation=%s: %s",
            session.session_id,
            session.operation,
            error,
        )
        return Response({"status": "failed"})


class FileTransferArchiveReady(APIView):
    """Agent callback that completes an async archive (ZIP) prepare."""

    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, session_id):
        agent = get_object_or_404(
            Agent.objects.defer(*AGENT_DEFER),
            user=request.user,
        )

        session = get_object_or_404(
            FileTransferSession,
            session_id=session_id,
            agent=agent,
            operation=FileTransferOperation.DOWNLOAD,
        )

        if session.status in _TERMINAL_STATUSES:
            return Response(
                "Session is no longer active",
                status=status.HTTP_409_CONFLICT,
            )

        error = _agent_body_str(request, "error")
        if error:
            # don't overwrite a cancel
            FileTransferSession.objects.filter(
                pk=session.pk, status=FileTransferStatus.WAITING_FOR_AGENT
            ).update(
                status=FileTransferStatus.FAILED,
                error_message=error[:2048],
                updated_at=djangotime.now(),
            )
            session.error_message = error[:2048]
            logger.error(
                "file_transfer archive build failed session=%s: %s",
                session.session_id,
                session.error_message,
            )
            return Response({"status": "failed"})

        if session.status in (
            FileTransferStatus.AGENT_READY,
            FileTransferStatus.TRANSFERRING,
        ):
            return Response({"status": "ready"})

        try:
            total_size = int(request.data.get("total_size"))
        except (AttributeError, TypeError, ValueError):
            return notify_error("total_size must be a positive integer")
        if total_size < 1 or total_size > _MAX_BYTE_COUNT:
            return notify_error("Agent reported empty or invalid archive")

        archive_path = _agent_body_str(request, "archive_path")
        if not archive_path:
            return notify_error("archive_path is required")
        if len(archive_path) > 4096:
            return notify_error("archive_path is too long")

        warnings_value = _warnings_json(request.data.get("warnings"))

        now = djangotime.now()
        updated = FileTransferSession.objects.filter(
            pk=session.pk, status=FileTransferStatus.WAITING_FOR_AGENT
        ).update(
            destination_path=archive_path,
            total_size=total_size,
            warnings=warnings_value,
            status=FileTransferStatus.AGENT_READY,
            expires_at=now + dt.timedelta(hours=FILE_TRANSFER_SESSION_TTL_HOURS),
            updated_at=now,
        )
        if not updated:
            # cancelled, the agent deletes the archive
            return Response(
                "Session is no longer active",
                status=status.HTTP_409_CONFLICT,
            )
        logger.info(
            "file_transfer archive ready session=%s total_size=%s",
            session.session_id,
            total_size,
        )
        return Response({"status": "ready"})


_EXTRACT_ACTIVE_STATUSES = (
    FileTransferStatus.WAITING_FOR_AGENT,
    FileTransferStatus.AGENT_READY,
    FileTransferStatus.TRANSFERRING,
)


_MAX_FILE_COUNT = 2**31 - 1


def _agent_body_count(request, key: str, maximum: int = _MAX_FILE_COUNT) -> int:
    """Non-negative int from the agent's body, clamped to the column's range."""
    if not isinstance(request.data, dict):
        return 0
    try:
        return min(max(int(request.data.get(key) or 0), 0), maximum)
    except (TypeError, ValueError, OverflowError):
        return 0


def _agent_extract_session(request, session_id):
    agent = get_object_or_404(
        Agent.objects.defer(*AGENT_DEFER),
        user=request.user,
    )
    session = get_object_or_404(
        FileTransferSession,
        session_id=session_id,
        agent=agent,
        operation=FileTransferOperation.EXTRACT,
    )
    if session.status in _TERMINAL_STATUSES:
        return None, Response(
            "Session is no longer active",
            status=status.HTTP_409_CONFLICT,
        )
    return session, None


class FileTransferExtractProgress(APIView):
    """Agent progress for an extract; also keeps the session from idling out."""

    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, session_id):
        session, err = _agent_extract_session(request, session_id)
        if err is not None:
            return err

        now = djangotime.now()
        updated = FileTransferSession.objects.filter(
            pk=session.pk, status__in=_EXTRACT_ACTIVE_STATUSES
        ).update(
            status=FileTransferStatus.TRANSFERRING,
            committed_offset=_agent_body_count(request, "written", _MAX_BYTE_COUNT),
            total_size=_agent_body_count(request, "total", _MAX_BYTE_COUNT),
            files_done=_agent_body_count(request, "files_done"),
            files_total=_agent_body_count(request, "files_total"),
            expires_at=now + dt.timedelta(minutes=FILE_TRANSFER_IDLE_EXPIRE_MINUTES),
            updated_at=now,
        )
        if not updated:
            return Response(
                "Session is no longer active",
                status=status.HTTP_409_CONFLICT,
            )
        return Response({"status": FileTransferStatus.TRANSFERRING})


class FileTransferExtractDone(APIView):
    """Agent callback that finishes an extract, successfully or not."""

    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, session_id):
        session, err = _agent_extract_session(request, session_id)
        if err is not None:
            return err

        warnings_value = _warnings_json(request.data.get("warnings"))
        fields = {
            "files_done": _agent_body_count(request, "files"),
            "files_skipped": _agent_body_count(request, "skipped"),
            "files_total": _agent_body_count(request, "files_total"),
            "total_size": _agent_body_count(request, "total", _MAX_BYTE_COUNT),
            "warnings": warnings_value,
            "updated_at": djangotime.now(),
        }
        error = _agent_body_str(request, "error")[:2048]
        if error:
            fields.update(status=FileTransferStatus.FAILED, error_message=error)
        else:
            fields.update(
                status=FileTransferStatus.COMPLETED,
                error_message="",
                committed_offset=fields["total_size"],
            )

        updated = FileTransferSession.objects.filter(
            pk=session.pk, status__in=_EXTRACT_ACTIVE_STATUSES
        ).update(**fields)
        if not updated:
            return Response(
                "Session is no longer active",
                status=status.HTTP_409_CONFLICT,
            )
        if error:
            logger.error(
                "file_transfer extract failed session=%s: %s",
                session.session_id,
                error,
            )
        else:
            logger.info(
                "file_transfer extract done session=%s files=%s skipped=%s",
                session.session_id,
                fields["files_done"],
                fields["files_skipped"],
            )
        return Response({"status": fields["status"]})
