from django.core.management.base import BaseCommand, CommandError

from core.agent_updater import start_listener


class Command(BaseCommand):
    help = 'Start the Redis listener for agent updates to synchronize NATS configuration across services'

    def add_arguments(self, parser):
        parser.add_argument(
            '--foreground',
            action='store_true',
            help='Run in non-daemon mode (foreground with continuous output)',
        )

    def handle(self, *args, **options):
        foreground = options.get('foreground', False)
        
        self.stdout.write("Starting agent update listener...")
        
        try:
            thread = start_listener(daemon=not foreground)
            
            if foreground:
                self.stdout.write(self.style.SUCCESS("Listener started in foreground mode. Press Ctrl+C to exit."))
                try:
                    # Keep the main thread alive
                    thread.join()
                except KeyboardInterrupt:
                    self.stdout.write(self.style.SUCCESS("Listener stopped."))
            else:
                self.stdout.write(self.style.SUCCESS("Listener started in background mode."))
                
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Failed to start listener: {str(e)}"))
            raise CommandError(f"Failed to start listener: {str(e)}") 