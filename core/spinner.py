import sys
import threading
import time
import itertools


class Spinner:
    """A simple spinner class to show activity for long-running tasks."""

    def __init__(self, message: str = "Processing..."):
        """
        Initialize the spinner.
        Args:
            message: The message to display next to the spinner.
        """
        self.spinner_chars = itertools.cycle(
            ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        )
        self.delay = 0.08
        self.busy = False
        self.spinner_thread = None
        self.message = message

    def start(self):
        """Start the spinner."""
        self.busy = True
        self.spinner_thread = threading.Thread(target=self._spin)
        self.spinner_thread.start()

    def stop(self):
        """Stop the spinner."""
        self.busy = False
        if self.spinner_thread:
            self.spinner_thread.join()
        # Clear the line
        sys.stdout.write("\r" + " " * (len(self.message) + 5) + "\r")
        sys.stdout.flush()

    def _spin(self):
        """The actual spinning logic."""
        while self.busy:
            sys.stdout.write(f"\r{next(self.spinner_chars)} {self.message}")
            sys.stdout.flush()
            time.sleep(self.delay)

    def __enter__(self):
        """Context manager start."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Context manager stop."""
        self.stop()
