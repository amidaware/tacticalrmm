from django.core.management.base import BaseCommand, CommandError
import sys
import os

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
        
        # Set environment variable to force stdout to be unbuffered
        os.environ['PYTHONUNBUFFERED'] = '1'
        
        # Print environment info for debugging
        self.stdout.write("=== STARTING AGENT LISTENER ===")
        self.stdout.write(f"REDIS_HOST: {os.environ.get('REDIS_HOST', 'Not set')}")
        self.stdout.write(f"Current directory: {os.getcwd()}")
        self.stdout.write(f"Python executable: {sys.executable}")
        self.stdout.write(f"Running in {'foreground' if foreground else 'background'} mode")
        
        try:
            # Start the listener with appropriate daemon setting
            thread = start_listener(daemon=not foreground)
            
            if foreground:
                self.stdout.write(self.style.SUCCESS("Listener started in foreground mode. Press Ctrl+C to exit."))
                self.stdout.write("Keeping main thread alive. Messages will appear below:")
                try:
                    # Keep the main thread alive
                    thread.join()
                except KeyboardInterrupt:
                    self.stdout.write(self.style.SUCCESS("Listener stopped due to keyboard interrupt."))
            else:
                self.stdout.write(self.style.SUCCESS("Listener started in background mode."))
                self.stdout.write("NOTE: In background mode, logs will go to the Django log file.")
                
        except Exception as e:
            error_msg = f"Failed to start listener: {str(e)}"
            self.stderr.write(self.style.ERROR(error_msg))
            self.stderr.write(self.style.ERROR("Check Redis connection and make sure the REDIS_HOST environment variable is set correctly."))
            raise CommandError(error_msg) 