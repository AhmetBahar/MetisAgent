"""
Idempotency Service - Request Deduplication and Caching

Prevents duplicate operations by tracking idempotency keys and caching results.
Supports both in-memory (for development) and database-backed storage.

Features:
- Request deduplication using idempotency keys
- Result caching with TTL
- In-progress request tracking
- Automatic cleanup of expired records
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Optional
from uuid import uuid4

from ..contracts.tool_envelope import (
    IdempotencyRecord,
    IdempotencyStatus,
    ToolCallEnvelope,
    ToolCallResult
)

logger = logging.getLogger(__name__)


class IdempotencyService:
    """
    Service for managing request idempotency.

    Tracks requests by idempotency key to prevent duplicate operations
    and return cached results for repeated requests.
    """

    def __init__(
        self,
        default_ttl_seconds: int = 3600,  # 1 hour default
        max_records: int = 10000,
        cleanup_interval_seconds: int = 300  # 5 minutes
    ):
        """
        Initialize idempotency service.

        Args:
            default_ttl_seconds: Default time-to-live for idempotency records
            max_records: Maximum records to keep in memory
            cleanup_interval_seconds: Interval for automatic cleanup
        """
        self.default_ttl_seconds = default_ttl_seconds
        self.max_records = max_records
        self.cleanup_interval_seconds = cleanup_interval_seconds

        # In-memory storage (replace with database in production)
        self._records: Dict[str, IdempotencyRecord] = {}
        self._in_progress: Dict[str, asyncio.Event] = {}  # Keys currently being processed
        self._lock = asyncio.Lock()

        # Statistics
        self._stats = {
            "total_requests": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "duplicates_prevented": 0,
            "cleanups_run": 0
        }

    async def check_idempotency(
        self,
        envelope: ToolCallEnvelope
    ) -> tuple[IdempotencyStatus, Optional[ToolCallResult]]:
        """
        Check if request has been processed before.

        Args:
            envelope: Tool call envelope with idempotency key

        Returns:
            Tuple of (status, cached_result or None)
        """
        idempotency_key = envelope.get_idempotency_key()

        async with self._lock:
            self._stats["total_requests"] += 1

            # Check if we have a record for this key
            record = self._records.get(idempotency_key)

            if not record:
                # New request
                self._stats["cache_misses"] += 1
                return IdempotencyStatus.NEW, None

            # Check if record has expired
            if datetime.now() > record.expires_at:
                # Expired, treat as new
                del self._records[idempotency_key]
                self._stats["cache_misses"] += 1
                return IdempotencyStatus.EXPIRED, None

            # Check if request is currently in progress
            if record.status == IdempotencyStatus.IN_PROGRESS:
                return IdempotencyStatus.IN_PROGRESS, None

            # Duplicate request - return cached result
            self._stats["cache_hits"] += 1
            self._stats["duplicates_prevented"] += 1
            record.last_accessed_at = datetime.now()

            if record.result:
                # Update result to indicate it's from cache
                cached_result = record.result.model_copy(update={
                    "idempotency_status": IdempotencyStatus.DUPLICATE,
                    "cached_at": record.created_at
                })
                return IdempotencyStatus.DUPLICATE, cached_result

            return IdempotencyStatus.DUPLICATE, None

    async def start_processing(
        self,
        envelope: ToolCallEnvelope,
        ttl_seconds: Optional[int] = None
    ) -> str:
        """
        Mark request as in-progress.

        Args:
            envelope: Tool call envelope
            ttl_seconds: Optional custom TTL for this record

        Returns:
            Idempotency key
        """
        idempotency_key = envelope.get_idempotency_key()
        ttl = ttl_seconds or self.default_ttl_seconds

        async with self._lock:
            # Create in-progress record
            record = IdempotencyRecord(
                idempotency_key=idempotency_key,
                request_id=envelope.request_id,
                tool_name=envelope.tool_name,
                capability_name=envelope.capability_name,
                company_id=envelope.context.company_id,
                user_id=envelope.context.user_id,
                status=IdempotencyStatus.IN_PROGRESS,
                expires_at=datetime.now() + timedelta(seconds=ttl)
            )

            self._records[idempotency_key] = record

            # Create event for waiters
            self._in_progress[idempotency_key] = asyncio.Event()

        return idempotency_key

    async def complete_processing(
        self,
        idempotency_key: str,
        result: ToolCallResult
    ):
        """
        Mark request as completed and cache result.

        Args:
            idempotency_key: The idempotency key
            result: The result to cache
        """
        async with self._lock:
            record = self._records.get(idempotency_key)
            if record:
                record.status = IdempotencyStatus.NEW  # Completed successfully
                record.result = result

            # Signal waiters
            event = self._in_progress.pop(idempotency_key, None)
            if event:
                event.set()

    async def fail_processing(self, idempotency_key: str):
        """
        Mark request as failed (remove from tracking).

        Failed requests should not be cached - allow retry.
        """
        async with self._lock:
            self._records.pop(idempotency_key, None)

            # Signal waiters
            event = self._in_progress.pop(idempotency_key, None)
            if event:
                event.set()

    async def wait_for_completion(
        self,
        idempotency_key: str,
        timeout_seconds: float = 30.0
    ) -> Optional[ToolCallResult]:
        """
        Wait for an in-progress request to complete.

        Args:
            idempotency_key: The idempotency key to wait for
            timeout_seconds: Maximum time to wait

        Returns:
            Cached result if available, None if timeout or not found
        """
        event = self._in_progress.get(idempotency_key)
        if not event:
            return None

        try:
            await asyncio.wait_for(event.wait(), timeout=timeout_seconds)
        except asyncio.TimeoutError:
            logger.warning(f"Timeout waiting for idempotency key: {idempotency_key}")
            return None

        # Get the cached result
        record = self._records.get(idempotency_key)
        return record.result if record else None

    async def cleanup_expired(self):
        """Remove expired idempotency records."""
        async with self._lock:
            now = datetime.now()
            expired_keys = [
                key for key, record in self._records.items()
                if now > record.expires_at
            ]

            for key in expired_keys:
                del self._records[key]
                self._in_progress.pop(key, None)

            self._stats["cleanups_run"] += 1

            if expired_keys:
                logger.info(f"Cleaned up {len(expired_keys)} expired idempotency records")

    async def enforce_max_records(self):
        """Enforce maximum record limit by removing oldest records."""
        async with self._lock:
            if len(self._records) <= self.max_records:
                return

            # Sort by last accessed time and remove oldest
            sorted_records = sorted(
                self._records.items(),
                key=lambda x: x[1].last_accessed_at
            )

            records_to_remove = len(self._records) - self.max_records
            for key, _ in sorted_records[:records_to_remove]:
                del self._records[key]
                self._in_progress.pop(key, None)

            logger.info(f"Enforced max records, removed {records_to_remove} oldest records")

    def get_statistics(self) -> Dict[str, Any]:
        """Get idempotency service statistics."""
        return {
            **self._stats,
            "current_records": len(self._records),
            "in_progress_requests": len(self._in_progress),
            "cache_hit_rate": (
                self._stats["cache_hits"] / self._stats["total_requests"]
                if self._stats["total_requests"] > 0 else 0
            )
        }

    async def start_cleanup_task(self):
        """Start background cleanup task."""
        while True:
            await asyncio.sleep(self.cleanup_interval_seconds)
            await self.cleanup_expired()
            await self.enforce_max_records()


class IdempotencyMiddleware:
    """
    Middleware for automatic idempotency handling in tool execution.

    Wraps tool execution to automatically check and update idempotency.
    """

    def __init__(self, idempotency_service: IdempotencyService):
        self.service = idempotency_service

    async def execute_with_idempotency(
        self,
        envelope: ToolCallEnvelope,
        executor_fn
    ) -> ToolCallResult:
        """
        Execute tool with idempotency protection.

        Args:
            envelope: Tool call envelope
            executor_fn: Async function that executes the tool

        Returns:
            ToolCallResult (from cache or fresh execution)
        """
        # Check idempotency
        status, cached_result = await self.service.check_idempotency(envelope)

        if status == IdempotencyStatus.DUPLICATE and cached_result:
            logger.info(f"Returning cached result for idempotency key: {envelope.get_idempotency_key()}")
            return cached_result

        if status == IdempotencyStatus.IN_PROGRESS:
            # Wait for the in-progress request to complete
            logger.info(f"Waiting for in-progress request: {envelope.get_idempotency_key()}")
            result = await self.service.wait_for_completion(
                envelope.get_idempotency_key(),
                timeout_seconds=envelope.timeout_seconds
            )
            if result:
                return result
            # If timeout, fall through to execute fresh

        # Mark as in-progress
        idempotency_key = await self.service.start_processing(envelope)

        try:
            # Execute the tool
            result = await executor_fn(envelope)

            # Cache the result
            await self.service.complete_processing(idempotency_key, result)

            return result

        except Exception as e:
            # Don't cache failed requests
            await self.service.fail_processing(idempotency_key)
            raise
