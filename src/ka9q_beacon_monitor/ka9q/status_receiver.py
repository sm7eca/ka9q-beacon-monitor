"""Asynchronous transport boundary for KA9Q radiod status multicast.

The receiver owns UDP multicast transport, datagram framing, decoding dispatch,
and error isolation. The binary KA9Q status format is intentionally represented
by the ``StatusDatagramDecoder`` protocol so the verified wire decoder can be
plugged in without coupling transport to a specific radiod release.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime, timezone
import ipaddress
import socket
from typing import Protocol, runtime_checkable

from ka9q_beacon_monitor.model import StatusSample


class StatusDecodeError(ValueError):
    """Raised when a datagram cannot be normalized into a StatusSample."""


@runtime_checkable
class StatusDatagramDecoder(Protocol):
    """Decoder contract for one KA9Q status datagram."""

    def decode(
        self,
        datagram: bytes,
        *,
        received_at_utc: datetime,
        source: tuple[str, int] | None,
    ) -> StatusSample:
        """Decode one complete datagram or raise StatusDecodeError."""


SampleHandler = Callable[[StatusSample], Awaitable[None] | None]
ErrorHandler = Callable[[Exception, bytes, tuple[str, int] | None], Awaitable[None] | None]


@dataclass(frozen=True, slots=True)
class MulticastEndpoint:
    """Validated IPv4 multicast endpoint configuration."""

    group: str
    port: int
    interface: str = "0.0.0.0"
    receive_buffer_bytes: int = 1_048_576
    max_datagram_bytes: int = 65_535

    def __post_init__(self) -> None:
        group = ipaddress.ip_address(self.group)
        interface = ipaddress.ip_address(self.interface)
        if group.version != 4 or not group.is_multicast:
            raise ValueError("group must be an IPv4 multicast address")
        if interface.version != 4:
            raise ValueError("interface must be an IPv4 address")
        if not 1 <= self.port <= 65_535:
            raise ValueError("port must be in range 1..65535")
        if self.receive_buffer_bytes <= 0:
            raise ValueError("receive_buffer_bytes must be positive")
        if not 1 <= self.max_datagram_bytes <= 65_535:
            raise ValueError("max_datagram_bytes must be in range 1..65535")


@dataclass(slots=True)
class ReceiverCounters:
    """Monotonic operational counters for one receiver instance."""

    datagrams_received: int = 0
    samples_published: int = 0
    datagrams_rejected: int = 0
    handler_failures: int = 0


class _StatusDatagramProtocol(asyncio.DatagramProtocol):
    def __init__(self, receiver: "Ka9qStatusReceiver") -> None:
        self._receiver = receiver

    def datagram_received(self, data: bytes, addr: tuple[str, int]) -> None:
        self._receiver._schedule_datagram(data, addr)

    def error_received(self, exc: Exception) -> None:
        self._receiver._schedule_transport_error(exc)


class Ka9qStatusReceiver:
    """Receive, decode, and publish normalized KA9Q status samples.

    One malformed datagram or failing consumer is isolated and must not stop the
    receiver. ``start`` and ``close`` are idempotent with respect to receiver
    state; starting an already-started receiver is rejected to avoid duplicate
    multicast subscriptions.
    """

    def __init__(
        self,
        endpoint: MulticastEndpoint,
        decoder: StatusDatagramDecoder,
        on_sample: SampleHandler,
        *,
        on_error: ErrorHandler | None = None,
        loop: asyncio.AbstractEventLoop | None = None,
    ) -> None:
        if not isinstance(decoder, StatusDatagramDecoder):
            raise TypeError("decoder must implement StatusDatagramDecoder")
        self.endpoint = endpoint
        self.decoder = decoder
        self.on_sample = on_sample
        self.on_error = on_error
        self.counters = ReceiverCounters()
        self._loop = loop
        self._transport: asyncio.DatagramTransport | None = None
        self._tasks: set[asyncio.Task[None]] = set()

    @property
    def is_running(self) -> bool:
        return self._transport is not None

    async def start(self) -> None:
        if self.is_running:
            raise RuntimeError("receiver is already running")
        loop = self._loop or asyncio.get_running_loop()
        sock = self._create_multicast_socket()
        try:
            transport, _ = await loop.create_datagram_endpoint(
                lambda: _StatusDatagramProtocol(self),
                sock=sock,
            )
        except Exception:
            sock.close()
            raise
        self._transport = transport

    async def close(self) -> None:
        transport = self._transport
        self._transport = None
        if transport is not None:
            transport.close()
        if self._tasks:
            await asyncio.gather(*tuple(self._tasks), return_exceptions=True)

    async def process_datagram(
        self,
        datagram: bytes,
        source: tuple[str, int] | None = None,
        *,
        received_at_utc: datetime | None = None,
    ) -> StatusSample | None:
        """Process one datagram; public for replay, integration tests, and HIL."""
        self.counters.datagrams_received += 1
        if not datagram or len(datagram) > self.endpoint.max_datagram_bytes:
            await self._reject(
                StatusDecodeError("datagram size is outside the accepted range"),
                datagram,
                source,
            )
            return None

        timestamp = received_at_utc or datetime.now(timezone.utc)
        try:
            sample = self.decoder.decode(
                datagram,
                received_at_utc=timestamp,
                source=source,
            )
        except Exception as exc:
            await self._reject(exc, datagram, source)
            return None

        try:
            result = self.on_sample(sample)
            if result is not None:
                await result
        except Exception as exc:
            self.counters.handler_failures += 1
            await self._notify_error(exc, datagram, source)
            return None

        self.counters.samples_published += 1
        return sample

    def _create_multicast_socket(self) -> socket.socket:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, self.endpoint.receive_buffer_bytes)
        sock.bind(("", self.endpoint.port))
        membership = socket.inet_aton(self.endpoint.group) + socket.inet_aton(
            self.endpoint.interface
        )
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, membership)
        sock.setblocking(False)
        return sock

    def _schedule_datagram(self, datagram: bytes, source: tuple[str, int]) -> None:
        task = asyncio.create_task(self.process_datagram(datagram, source))
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    def _schedule_transport_error(self, exc: Exception) -> None:
        task = asyncio.create_task(self._notify_error(exc, b"", None))
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    async def _reject(
        self,
        exc: Exception,
        datagram: bytes,
        source: tuple[str, int] | None,
    ) -> None:
        self.counters.datagrams_rejected += 1
        await self._notify_error(exc, datagram, source)

    async def _notify_error(
        self,
        exc: Exception,
        datagram: bytes,
        source: tuple[str, int] | None,
    ) -> None:
        if self.on_error is None:
            return
        try:
            result = self.on_error(exc, datagram, source)
            if result is not None:
                await result
        except Exception:
            # Error reporting must never terminate datagram processing.
            return
