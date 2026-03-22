from pathlib import Path

from adapters.logging import JaysLogger

# Shared logger used across usecases/repositories for consistent diagnostics.
app_logger = JaysLogger(
    track_time=True,
    track_call_count=True,
    save_logs=True,
    save_on=["warning", "error"],
    log_file=Path(".data/runtime_logs.json"),
    save_backend="json_database",
    suppress_success_below_s=0.250,
)
