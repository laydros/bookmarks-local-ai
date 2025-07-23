import builtins
from unittest.mock import patch

from core.progress_tracker import ProgressTracker


def test_format_time():
    tracker = ProgressTracker(total=1, show_progress_bar=False)
    assert tracker._format_time(30) == "30s"
    assert tracker._format_time(90) == "1m30s"
    assert tracker._format_time(3700) == "1h01m"


def test_finish_prints_summary():
    with patch("core.progress_tracker.time.time") as mock_time:
        mock_time.return_value = 0
        tracker = ProgressTracker(total=2, description="Proc", show_progress_bar=True)
        mock_time.return_value = 1
        tracker.update()
        mock_time.return_value = 2
        tracker.update()
        mock_time.return_value = 3
        with patch.object(builtins, "print") as mock_print:
            tracker.finish()
            # The final print call should include description and successful count
            assert any(
                "Proc complete" in str(call.args[0])
                for call in mock_print.call_args_list
            )


def test_set_description():
    tracker = ProgressTracker(total=1, show_progress_bar=False)
    tracker.set_description("New desc")
    assert tracker.description == "New desc"
