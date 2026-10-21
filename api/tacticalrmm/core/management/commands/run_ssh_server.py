import asyncio
import logging
import signal

from asgiref.sync import sync_to_async
from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone as djangotime

from tacticalrmm.gateway import start_gateway, _active_connections
from core.utils import get_core_settings

logger = logging.getLogger("trmm")


@sync_to_async
def _cleanup_orphan_sessions():
    from accounts.models import SSHSession
    count = SSHSession.objects.filter(closed_at__isnull=True).update(
        closed_at=djangotime.now()
    )
    if count:
        logger.info("Gateway: closed %d orphaned session(s) from previous run", count)
    return count


async def _stats_loop(shutdown_event):
    while not shutdown_event.is_set():
        try:
            await asyncio.wait_for(shutdown_event.wait(), timeout=300)
        except asyncio.TimeoutError:
            logger.info("Gateway: %d active connection(s)", _active_connections)


class Command(BaseCommand):
    help = "Start the Tactical RMM gateway server"

    def add_arguments(self, parser):
        parser.add_argument(
            "--port",
            type=int,
            default=getattr(settings, "SSH_SERVER_PORT", 2222),
            help="Gateway port (default: 2222)",
        )
        parser.add_argument(
            "--host",
            type=str,
            default=getattr(settings, "SSH_SERVER_HOST", "0.0.0.0"),
            help="Gateway bind address (default: 0.0.0.0)",
        )

    def handle(self, *args, **options):
        core = get_core_settings()
        if not core.ssh_gateway_enabled:
            self.stderr.write(
                self.style.ERROR("Gateway is disabled in global settings. "
                                  "Enable 'Enable SSH gateway' in Global Settings > General.")
            )
            return

        host = options["host"]
        port = options["port"]

        self.stdout.write(self.style.SUCCESS(f"Starting gateway on {host}:{port}"))

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        shutdown_event = asyncio.Event()
        server_ref = []

        def _on_signal():
            asyncio.ensure_future(self._shutdown(server_ref, loop, shutdown_event))

        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, _on_signal)

        try:
            loop.run_until_complete(_cleanup_orphan_sessions())
            server = loop.run_until_complete(start_gateway(host=host, port=port))
            server_ref.append(server)
            self.stdout.write(
                self.style.SUCCESS(f"Gateway running on {host}:{port}")
            )
            loop.create_task(_stats_loop(shutdown_event))
            loop.run_forever()
        except KeyboardInterrupt:
            pass
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Failed to start gateway: {e}"))
            raise
        finally:
            self._do_shutdown(server_ref, loop, shutdown_event)

    async def _shutdown(self, server_ref, loop, shutdown_event):
        logger.info("Gateway shutting down (signal)...")
        shutdown_event.set()
        if server_ref and server_ref[0]:
            server_ref[0].close()
            await server_ref[0].wait_closed()
        for t in asyncio.all_tasks(loop):
            t.cancel()
        loop.stop()

    def _do_shutdown(self, server_ref, loop, shutdown_event):
        if shutdown_event.is_set():
            return
        logger.info("Gateway shutting down...")
        shutdown_event.set()
        if server_ref and server_ref[0]:
            server_ref[0].close()
            loop.run_until_complete(server_ref[0].wait_closed())
        loop.close()
