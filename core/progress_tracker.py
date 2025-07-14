"""
Progress tracking and reporting utilities.
"""

import time
import sys
from typing import Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class ProgressStats:
    """Statistics for progress tracking."""

    total: int
    completed: int
    successful: int
    failed: int
    skipped: int
    start_time: float
    current_time: float

    @property
    def elapsed_seconds(self) -> float:
        """Total elapsed time in seconds."""
        return self.current_time - self.start_time

    @property
    def completion_rate(self) -> float:
        """Completion percentage (0-1)."""
        return self.completed / self.total if self.total > 0 else 0

    @property
    def success_rate(self) -> float:
        """Success rate of completed items (0-1)."""
        return self.successful / self.completed if self.completed > 0 else 0

    @property
    def items_per_second(self) -> float:
        """Processing speed in items per second."""
        return self.completed / self.elapsed_seconds if self.elapsed_seconds > 0 else 0

    @property
    def estimated_total_seconds(self) -> float:
        """Estimated total time to completion."""
        if self.items_per_second > 0:
            return self.total / self.items_per_second
        return 0

    @property
    def estimated_remaining_seconds(self) -> float:
        """Estimated remaining time in seconds."""
        remaining_items = self.total - self.completed
        if self.items_per_second > 0:
            return remaining_items / self.items_per_second
        return 0


class ProgressTracker:
    """Tracks and displays progress for long-running operations."""

    def __init__(
        self,
        total: int,
        description: str = "Processing",
        show_progress_bar: bool = True,
        update_interval: float = 1.0,
    ):
        """
        Initialize progress tracker.

        Args:
            total: Total number of items to process
            description: Description of the operation
            show_progress_bar: Whether to show visual progress bar
            update_interval: How often to update display (seconds)
        """
        self.total = total
        self.description = description
        self.show_progress_bar = show_progress_bar
        self.update_interval = update_interval

        self.completed = 0
        self.successful = 0
        self.failed = 0
        self.skipped = 0
        self.start_time = time.time()
        self.last_update = 0

        self._last_message_length = 0

        if self.show_progress_bar:
            print(f"\n{self.description}: 0/{self.total} (0.0%)")

    def update(
        self,
        success: bool = True,
        skip: bool = False,
        current_item: Optional[str] = None,
    ):
        """
        Update progress with completion of one item.

        Args:
            success: Whether the item was processed successfully
            skip: Whether the item was skipped
            current_item: Name/description of current item being processed
        """
        self.completed += 1

        if skip:
            self.skipped += 1
        elif success:
            self.successful += 1
        else:
            self.failed += 1

        current_time = time.time()

        # Update display if enough time has passed or if completed
        if (
            current_time - self.last_update >= self.update_interval
            or self.completed >= self.total
        ):
            if self.show_progress_bar:
                self._update_display(current_item)

            self.last_update = current_time

    def _update_display(self, current_item: Optional[str] = None):
        """Update the progress display."""
        stats = self.get_stats()

        # Build progress message
        percentage = stats.completion_rate * 100
        elapsed_str = self._format_time(stats.elapsed_seconds)

        message_parts = [
            f"\r{self.description}: {self.completed}/{self.total}",
            f"({percentage:.1f}%)",
            f"✓{self.successful}",
        ]

        if self.failed > 0:
            message_parts.append(f"✗{self.failed}")

        if self.skipped > 0:
            message_parts.append(f"⏭{self.skipped}")

        message_parts.extend([f"[{elapsed_str}", f"{stats.items_per_second:.1f}/s"])

        # Add ETA if we have enough data and not completed
        if (
            stats.items_per_second > 0
            and self.completed < self.total
            and stats.elapsed_seconds > 5
        ):
            eta_str = self._format_time(stats.estimated_remaining_seconds)
            message_parts.append(f"ETA:{eta_str}")

        message_parts.append("]")

        # Add current item if provided
        if current_item:
            # Truncate long item names
            if len(current_item) > 40:
                current_item = current_item[:37] + "..."
            message_parts.append(f"- {current_item}")

        message = " ".join(message_parts)

        # Clear previous message and print new one
        if self._last_message_length > len(message):
            # Clear extra characters from previous longer message
            print(" " * self._last_message_length, end="\r")

        print(message, end="", flush=True)
        self._last_message_length = len(message)

    def _format_time(self, seconds: float) -> str:
        """Format time duration in human-readable format."""
        if seconds < 60:
            return f"{seconds:.0f}s"
        elif seconds < 3600:
            minutes = int(seconds / 60)
            secs = int(seconds % 60)
            return f"{minutes}m{secs:02d}s"
        else:
            hours = int(seconds / 3600)
            minutes = int((seconds % 3600) / 60)
            return f"{hours}h{minutes:02d}m"

    def get_stats(self) -> ProgressStats:
        """Get current progress statistics."""
        return ProgressStats(
            total=self.total,
            completed=self.completed,
            successful=self.successful,
            failed=self.failed,
            skipped=self.skipped,
            start_time=self.start_time,
            current_time=time.time(),
        )

    def finish(self, final_message: Optional[str] = None):
        """Complete the progress tracking and show final stats."""
        if self.show_progress_bar:
            # Clear the progress line
            print(" " * self._last_message_length, end="\r")

            # Show final summary
            stats = self.get_stats()
            elapsed_str = self._format_time(stats.elapsed_seconds)

            if final_message:
                print(final_message)
            else:
                print(
                    f"{self.description} complete: {self.successful}/{self.total} "
                    f"successful in {elapsed_str} "
                    f"({stats.items_per_second:.1f} items/sec)"
                )

    def set_description(self, description: str):
        """Update the operation description."""
        self.description = description
