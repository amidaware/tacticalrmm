import json
from dataclasses import dataclass
from functools import lru_cache
from typing import Optional
from uuid import UUID

from django.conf import settings
from redis import Redis, from_url

from tacticalrmm.constants import (
    FILE_TRANSFER_REDIS_ACK_TTL_SECONDS,
    FILE_TRANSFER_REDIS_CHUNK_TTL_SECONDS,
)


@dataclass
class PendingUploadChunk:
    start: int
    end: int
    data: bytes


@dataclass
class PendingDownloadChunk:
    start: int
    end: int
    data: bytes


_STORE_CHUNK_SCRIPT = """
local created = redis.call('SET', KEYS[1], ARGV[1], 'EX', ARGV[3], 'NX')
if not created then
    return 0
end
redis.call('SET', KEYS[2], ARGV[2], 'EX', ARGV[3])
redis.call('SET', KEYS[3], ARGV[4], 'EX', ARGV[5])
return 1
"""

_PEEK_CHUNK_SCRIPT = """
local meta = redis.call('GET', KEYS[1])
if not meta then
    return {false}
end
local data = redis.call('GET', KEYS[2])
if not data then
    return {false}
end
return {meta, data}
"""


@lru_cache(maxsize=1)
def _redis_client() -> Redis:
    return from_url(f"redis://{settings.REDIS_HOST}", decode_responses=False)


@lru_cache(maxsize=1)
def _store_chunk_redis_script():
    return _redis_client().register_script(_STORE_CHUNK_SCRIPT)


@lru_cache(maxsize=1)
def _peek_chunk_redis_script():
    return _redis_client().register_script(_PEEK_CHUNK_SCRIPT)


def _chunk_prefix(session_id: UUID) -> str:
    return f"upload:chunk:{session_id}/"


def _chunk_data_key_at(session_id: UUID, start: int) -> str:
    return f"{_chunk_prefix(session_id)}{start}:data"


def _chunk_meta_key_at(session_id: UUID, start: int) -> str:
    return f"{_chunk_prefix(session_id)}{start}:meta"


def pipeline_depth_full(ahead_offset: int, committed: int, depth_bytes: int) -> bool:
    return ahead_offset - committed >= depth_bytes


def _ack_key(session_id: UUID) -> str:
    return f"upload:ack:{session_id}"


def _accepted_key(session_id: UUID) -> str:
    return f"upload:accepted:{session_id}"


def get_accepted_offset(session_id: UUID) -> Optional[int]:
    raw = _redis_client().get(_accepted_key(session_id))
    if raw is None:
        return None
    return int(raw.decode())


def get_upload_ack(session_id: UUID) -> Optional[int]:
    raw = _redis_client().get(_ack_key(session_id))
    if raw is None:
        return None
    return int(raw.decode())


def store_upload_chunk(
    session_id: UUID, start: int, end: int, data: bytes
) -> Optional[str]:
    """Store chunk at offset-indexed keys and advance accepted_offset atomically.

    Returns an error string if the chunk is already pending at this offset,
    or None on success.
    """
    meta_key = _chunk_meta_key_at(session_id, start)
    data_key = _chunk_data_key_at(session_id, start)
    accepted_key = _accepted_key(session_id)
    meta = json.dumps({"start": start, "end": end}).encode()
    chunk_ttl = FILE_TRANSFER_REDIS_CHUNK_TTL_SECONDS
    accepted_ttl = FILE_TRANSFER_REDIS_ACK_TTL_SECONDS

    created = _store_chunk_redis_script()(
        keys=[meta_key, data_key, accepted_key],
        args=[meta, data, chunk_ttl, str(end + 1), accepted_ttl],
    )
    if not created:
        return "Chunk at this offset is already pending"
    return None


def rollback_upload_chunk(session_id: UUID, start: int, prev_accepted: int) -> None:
    """Undo a store_upload_chunk call (e.g. after NATS failure).

    Deletes the chunk keys and resets accepted_offset to prev_accepted.
    """
    client = _redis_client()
    client.delete(
        _chunk_meta_key_at(session_id, start),
        _chunk_data_key_at(session_id, start),
    )
    client.set(
        _accepted_key(session_id),
        str(prev_accepted).encode(),
        ex=FILE_TRANSFER_REDIS_ACK_TTL_SECONDS,
    )


def peek_upload_chunk(session_id: UUID, start: int) -> Optional[PendingUploadChunk]:
    """Chunk is only deleted on ack so the agent can retry a lost pull."""
    meta_key = _chunk_meta_key_at(session_id, start)
    data_key = _chunk_data_key_at(session_id, start)

    result = _peek_chunk_redis_script()(keys=[meta_key, data_key])

    if not result or result[0] is False or result[0] is None:
        return None

    meta_raw, data = result[0], result[1]
    meta = json.loads(meta_raw.decode())
    return PendingUploadChunk(
        start=int(meta["start"]),
        end=int(meta["end"]),
        data=data,
    )


def delete_upload_chunk(session_id: UUID, start: int) -> None:
    _redis_client().delete(
        _chunk_meta_key_at(session_id, start),
        _chunk_data_key_at(session_id, start),
    )


def signal_upload_ack(session_id: UUID, committed_offset: int) -> None:
    _redis_client().set(
        _ack_key(session_id),
        str(committed_offset).encode(),
        ex=FILE_TRANSFER_REDIS_ACK_TTL_SECONDS,
    )


def clear_upload_session_redis(session_id: UUID) -> None:
    client = _redis_client()
    client.delete(_ack_key(session_id), _accepted_key(session_id))
    for key in client.scan_iter(match=f"{_chunk_prefix(session_id)}*", count=1000):
        client.delete(key)


_STORE_DOWNLOAD_CHUNK_SCRIPT = """
local created = redis.call('SET', KEYS[1], ARGV[1], 'EX', ARGV[3], 'NX')
if not created then
    return 0
end
redis.call('SET', KEYS[2], ARGV[2], 'EX', ARGV[3])
redis.call('SET', KEYS[3], ARGV[4], 'EX', ARGV[5])
return 1
"""


@lru_cache(maxsize=1)
def _store_download_chunk_redis_script():
    return _redis_client().register_script(_STORE_DOWNLOAD_CHUNK_SCRIPT)


def _dl_chunk_prefix(session_id: UUID) -> str:
    return f"download:chunk:{session_id}/"


def _dl_chunk_data_key_at(session_id: UUID, start: int) -> str:
    return f"{_dl_chunk_prefix(session_id)}{start}:data"


def _dl_chunk_meta_key_at(session_id: UUID, start: int) -> str:
    return f"{_dl_chunk_prefix(session_id)}{start}:meta"


def _dl_offered_key(session_id: UUID) -> str:
    return f"download:offered:{session_id}"


def _dl_ack_key(session_id: UUID) -> str:
    return f"download:ack:{session_id}"


def get_download_offered_offset(session_id: UUID) -> Optional[int]:
    raw = _redis_client().get(_dl_offered_key(session_id))
    if raw is None:
        return None
    return int(raw.decode())


def get_download_ack(session_id: UUID) -> Optional[int]:
    raw = _redis_client().get(_dl_ack_key(session_id))
    if raw is None:
        return None
    return int(raw.decode())


def store_download_chunk(
    session_id: UUID, start: int, end: int, data: bytes
) -> Optional[str]:
    """Store a chunk pushed by the agent and wake any waiting client GET.

    Returns an error string if the chunk is already pending, or None on success.
    """
    meta_key = _dl_chunk_meta_key_at(session_id, start)
    data_key = _dl_chunk_data_key_at(session_id, start)
    offered_key = _dl_offered_key(session_id)
    meta = json.dumps({"start": start, "end": end}).encode()
    chunk_ttl = FILE_TRANSFER_REDIS_CHUNK_TTL_SECONDS
    offered_ttl = FILE_TRANSFER_REDIS_ACK_TTL_SECONDS

    created = _store_download_chunk_redis_script()(
        keys=[meta_key, data_key, offered_key],
        args=[meta, data, chunk_ttl, str(end + 1), offered_ttl],
    )
    if not created:
        return "Chunk at this offset is already pending"
    return None


def peek_download_chunk(session_id: UUID, start: int) -> Optional[PendingDownloadChunk]:
    """Fetch the download chunk stored at `start` without deleting it."""
    meta_key = _dl_chunk_meta_key_at(session_id, start)
    data_key = _dl_chunk_data_key_at(session_id, start)

    result = _peek_chunk_redis_script()(keys=[meta_key, data_key])

    if not result or result[0] is False or result[0] is None:
        return None

    meta_raw, data = result[0], result[1]
    meta = json.loads(meta_raw.decode())
    return PendingDownloadChunk(
        start=int(meta["start"]),
        end=int(meta["end"]),
        data=data,
    )


def delete_download_chunk(session_id: UUID, start: int) -> None:
    """Drop the buffered download chunk stored at `start`."""
    _redis_client().delete(
        _dl_chunk_meta_key_at(session_id, start),
        _dl_chunk_data_key_at(session_id, start),
    )


def signal_download_ack(session_id: UUID, committed_offset: int) -> None:
    _redis_client().set(
        _dl_ack_key(session_id),
        str(committed_offset).encode(),
        ex=FILE_TRANSFER_REDIS_ACK_TTL_SECONDS,
    )


def clear_download_session_redis(session_id: UUID) -> None:
    client = _redis_client()
    client.delete(
        _dl_offered_key(session_id),
        _dl_ack_key(session_id),
    )
    for key in client.scan_iter(match=f"{_dl_chunk_prefix(session_id)}*", count=1000):
        client.delete(key)
