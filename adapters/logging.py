"""
jays_logger.py
--------------
A decorator-based function logger with coloured output, execution timing,
call-count tracking, warning/error detection, custom messages, and optional
log persistence to JSONL.

Quick start
-----------
    from jays_logger import JaysLogger

    logger = JaysLogger(track_time=True, track_call_count=True)

    @logger.log(msg="migrating the database")
    def migrate_db(keep_backups: bool = True) -> str:
        ...

Log line format
---------------
    [slug] - <custom msg> - EXECUTING fn(args)          # before call
    [slug] - <custom msg> - SUCCESS  fn(args) -> [T=v]  # after call (green)
    [slug] - <custom msg> - WARNING  fn(args) -> [T=v]  # after call (yellow)
    [slug] - <custom msg> - ERROR    fn(args) ExcType:.. # after call (red)

Dependencies
------------
    pip install colorama
"""

from __future__ import annotations

import atexit
import functools
import inspect
import json
import re
import time
import warnings
from pprint import pformat
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Literal

from colorama import Fore, Style, init as colorama_init
from jays_tools.json_database import JsonDatabase, MigratableModel
from pydantic import Field

colorama_init(autoreset=True)


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _format_name(qualname: str) -> str:
    """
    Convert a Python qualified name to a human-readable kebab-case slug.

    The slug is used as the ``[label]`` that prefixes every log line.
    Each dot-separated segment of the qualified name is converted
    independently, so class methods retain their hierarchy.

    Conversion rules
    ~~~~~~~~~~~~~~~~
    * Underscores → hyphens
    * CamelCase humps → hyphenated (``MyClass`` → ``my-class``)
    * Everything is lowercased

    Parameters
    ----------
    qualname:
        The value of ``func.__qualname__``, e.g. ``"MyClass.my_method"``.

    Returns
    -------
    str
        Kebab-case slug, e.g. ``"my-class.my-method"``.

    Examples
    --------
    >>> _format_name("migrate_db")
    'migrate-db'
    >>> _format_name("MyClass.my_method")
    'my-class.my-method'
    >>> _format_name("myFuncName")
    'my-func-name'
    """
    parts = qualname.split(".")
    result = []
    for part in parts:
        # Insert a hyphen before any uppercase letter that follows a lowercase
        # letter or digit — this handles camelCase and PascalCase.
        s = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "-", part)
        result.append(s.replace("_", "-").lower())
    return ".".join(result)


def _format_call(func: Callable, args: tuple, kwargs: dict) -> str:
    """
    Build a readable call-signature string that mirrors Python source syntax.

    Uses :func:`inspect.signature` to bind positional and keyword arguments
    to their parameter names (including defaults for omitted parameters),
    then formats them as ``name=value`` pairs.  ``self`` and ``cls`` are
    excluded so that instance/class methods print cleanly.

    Falls back to a simpler positional/keyword representation if binding
    fails (e.g. for C-extension functions whose signatures are opaque).

    Parameters
    ----------
    func:
        The decorated callable.
    args:
        Positional arguments passed to the call.
    kwargs:
        Keyword arguments passed to the call.

    Returns
    -------
    str
        E.g. ``"migrate_db(keep_backups=True, debug=False)"``.
    """
    try:
        sig = inspect.signature(func)
        bound = sig.bind(*args, **kwargs)
        bound.apply_defaults()
        params_str = ", ".join(
            f"{k}={v!r}" for k, v in bound.arguments.items() if k not in ("self", "cls")
        )
    except (TypeError, ValueError):
        params_str = ", ".join(
            [repr(a) for a in args] + [f"{k}={v!r}" for k, v in kwargs.items()]
        )
    return f"{func.__name__}({params_str})"


def _repr_result(value: Any, max_len: int = 80) -> str:
    """
    Return a compact, type-annotated repr of a function's return value.

    The format is ``TypeName=repr`` so that the type is always visible even
    when the value itself is truncated.  Long reprs are truncated with an
    ellipsis to keep log lines readable.

    Parameters
    ----------
    value:
        Any return value.
    max_len:
        Maximum character length for the ``repr`` portion before truncation.
        Defaults to ``80``.

    Returns
    -------
    str
        E.g. ``"str='hello'"``, ``"list=[1, 2, 3]"``,
        ``"dict={'key': 'a very lon..."``.
    """
    type_name = type(value).__name__
    # Prefer pprint output for nested structures so logs stay readable.
    raw = pformat(value, compact=True, width=80)
    if len(raw) > max_len:
        raw = raw[: max_len - 3] + "..."
    return f"{type_name}={raw}"


def _format_elapsed(elapsed: float) -> str:
    """Format elapsed seconds as '<m>m <s>s <ms>ms' for readability."""
    total_ms = int(round(elapsed * 1000))
    minutes, remainder_ms = divmod(total_ms, 60_000)
    seconds, milliseconds = divmod(remainder_ms, 1000)
    return f"{minutes}m {seconds}s {milliseconds}ms"


# ---------------------------------------------------------------------------
# Log entry dataclass
# ---------------------------------------------------------------------------

SaveOnOption = Literal["success", "warning", "error"]
SaveBackend = Literal["jsonl", "json_database"]
"""
Valid values for the ``save_on`` parameter of :class:`JaysLogger`.

* ``"success"`` – persist entries where the function returned normally.
* ``"warning"`` – persist entries where a :mod:`warnings` warning was raised.
* ``"error"``   – persist entries where an unhandled exception was raised.
"""


@dataclass
class LogEntry:
    """
    A structured record of a single decorated-function call.

    Instances are created internally by :class:`JaysLogger` and are
    accessible via :meth:`JaysLogger.get_logs` and
    :meth:`JaysLogger.get_logs_for`.  They are also the objects serialised
    to JSONL when ``log_file`` is set.

    Attributes
    ----------
    slug:
        Kebab-case identifier derived from the function's qualified name,
        e.g. ``"data-pipeline.run"``.
    func_name:
        The raw ``__qualname__`` of the function, e.g. ``"DataPipeline.run"``.
    call_signature:
        Human-readable call string including argument values,
        e.g. ``"run(dry_run=False)"``.
    status:
        One of ``"success"``, ``"warning"``, or ``"error"``.
    timestamp:
        ISO-8601 timestamp of when the call *started*, with millisecond
        precision, e.g. ``"2024-03-15T09:42:01.123"``.
    elapsed_s:
        Wall-clock execution time in seconds (``None`` if
        ``track_time=False``).
    call_count:
        How many times this function has been called in the current process.
    return_repr:
        The :func:`_repr_result` string of the return value,
        or ``None`` if the call raised an exception.
    custom_msg:
        The ``msg`` string supplied to the ``@logger.log`` decorator,
        or an empty string if none was given.
    warnings_raised:
        List of string representations of any :mod:`warnings` warnings
        emitted during execution.
    error:
        ``repr(exception)`` if the function raised, otherwise ``None``.
    """

    slug: str
    func_name: str
    call_signature: str
    status: str
    timestamp: str
    elapsed_s: float | None
    call_count: int
    return_repr: str | None
    custom_msg: str
    warnings_raised: list[str]
    error: str | None


class LoggerLogEntryV1(MigratableModel):
    slug: str
    func_name: str
    call_signature: str
    status: str
    timestamp: str
    elapsed_s: float | None
    call_count: int
    return_repr: str | None
    custom_msg: str
    warnings_raised: list[str]
    error: str | None


CurrentLoggerLogEntry = LoggerLogEntryV1


class LoggerLogStoreV1(MigratableModel):
    entries: list[CurrentLoggerLogEntry] = Field(default_factory=list)


CurrentLoggerLogStore = LoggerLogStoreV1


# ---------------------------------------------------------------------------
# Main logger
# ---------------------------------------------------------------------------


class JaysLogger:
    """
    A decorator-based function logger with coloured terminal output,
    execution timing, call-count tracking, and optional log persistence.

    Create one shared instance per application (or per module) and apply
    ``@logger.log`` to any function or method you want to observe.

    Parameters
    ----------
    track_time : bool
        When ``True`` (default), measure wall-clock execution time with
        :func:`time.perf_counter` and include it in the post-call log line
        as ``TIME: 0.123s``.
    track_call_count : bool
        When ``True`` (default), maintain a per-function counter that
        increments on every call and display it as ``CALL COUNT: N``.
        Counters persist for the lifetime of the :class:`JaysLogger` instance.
    save_logs : bool
        When ``True``, accumulate :class:`LogEntry` objects in memory.
        Access them with :meth:`get_logs` or :meth:`get_logs_for`.
        Defaults to ``False``.
    save_on : list[SaveOnOption] | None
        Filter which statuses are persisted when ``save_logs=True``.

        * ``None`` or ``[]`` → save **every** call.
        * ``["error"]``           → save only calls that raised an exception.
        * ``["error", "warning"]`` → save failures and soft warnings.
        * ``["success"]``         → save only clean runs (rarely useful alone).

    log_file : str | Path | None
        If provided and ``save_logs=True``, the accumulated
        :class:`LogEntry` objects are written as `JSONL
        <https://jsonlines.org/>`_ (one JSON object per line) to this path
        when the Python interpreter exits.  The file is opened in **append**
        mode, so repeated runs accumulate entries rather than overwriting.
        Parent directories are created automatically.

    Examples
    --------
    Minimal setup — just coloured output::

        logger = JaysLogger()

        @logger.log
        def fetch_user(user_id: int) -> dict: ...

    Full setup with persistence::

        logger = JaysLogger(
            track_time=True,
            track_call_count=True,
            save_logs=True,
            save_on=["error", "warning"],
            log_file="logs/app.jsonl",
        )

    Notes
    -----
    * A single :class:`JaysLogger` instance can decorate functions across
      multiple modules — just import and reuse the same object.
    * Call counts are **per-slug per-instance**.  If you create two loggers
      they maintain independent counters.
    * The ``log_file`` flush is registered with :mod:`atexit`, so it runs on
      normal interpreter shutdown.  It will **not** run if the process is
      killed with ``SIGKILL`` or ``os._exit()``.
    """

    def __init__(
        self,
        track_time: bool = True,
        track_call_count: bool = True,
        save_logs: bool = False,
        save_on: list[SaveOnOption] | None = None,
        log_file: str | Path | None = None,
        save_backend: SaveBackend = "jsonl",
        suppress_success_below_s: float | None = None,
    ) -> None:
        self.track_time = track_time
        self.track_call_count = track_call_count
        self.save_logs = save_logs
        self.save_on: list[str] = [s.lower() for s in (save_on or [])]
        self.log_file = Path(log_file) if log_file else None
        self.save_backend = save_backend
        self.suppress_success_below_s = suppress_success_below_s

        self._call_counts: dict[str, int] = {}
        self._log_entries: list[LogEntry] = []

        if self.save_logs and self.log_file:
            atexit.register(self._flush_logs)

    def _should_print_post(self, status: str, elapsed: float | None) -> bool:
        if status != "success":
            return True

        if self.suppress_success_below_s is None:
            return True

        if elapsed is None:
            return True

        return elapsed >= self.suppress_success_below_s

    # ------------------------------------------------------------------
    # Public decorator
    # ------------------------------------------------------------------

    def log(
        self,
        func: Callable | None = None,
        *,
        msg: str = "",
        running_msg: str = "",
        success_msg: str = "",
        error_msg: str = "",
        warning_msg: str = "",
    ) -> Callable:
        """
        Decorator that wraps a function or method with structured logging.

        Prints a **pre-call** line when the function is entered and a
        **post-call** line once it returns (or raises), coloured by outcome.

        Calling styles
        --------------
        All three forms below are equivalent in behaviour::

            # 1. Bare — no parentheses, no custom messages
            @logger.log
            def fn(): ...

            # 2. Empty call — parentheses but no arguments
            @logger.log()
            def fn(): ...

            # 3. With custom messages
            @logger.log(msg="context label", error_msg="something went wrong")
            def fn(): ...

        Parameters
        ----------
        func : Callable | None
            Passed automatically when the decorator is used without
            parentheses (style 1).  Do **not** supply this yourself.
        msg : str
            A context label shown on **every** log line regardless of
            outcome.  Rendered in **cyan** so it stands out from the
            structural parts of the line.  If a status-specific message
            (``success_msg``, ``error_msg``, ``warning_msg``) is also
            provided, that takes precedence on the post-call line.
        running_msg : str
            Overrides ``msg`` on the **pre-call** line only.  Useful when
            you want different wording for "starting" vs "done"::

                @logger.log(running_msg="connecting…", success_msg="connected")
                def connect(): ...

        success_msg : str
            Replaces ``msg`` on the post-call line when the function
            returns without errors or warnings.
        error_msg : str
            Replaces ``msg`` on the post-call line when the function raises
            an unhandled exception.
        warning_msg : str
            Replaces ``msg`` on the post-call line when the function emits
            one or more :mod:`warnings` warnings but does not raise.

        Returns
        -------
        Callable
            The wrapped function (or a decorator waiting for a function).

        Notes
        -----
        * **Warnings** are detected via :func:`warnings.catch_warnings`.
          Inside the decorated function, call ``warnings.warn("msg")``
          (not ``raise``) for non-fatal issues.
        * **Exceptions** are re-raised after logging, so callers still
          receive them normally — the logger never swallows errors.
        * ``self`` / ``cls`` are automatically stripped from the logged
          argument list so method calls look clean.
        * The decorator preserves the original function's ``__name__``,
          ``__doc__``, and signature via :func:`functools.wraps`.

        Examples
        --------
        ::

            # Bare decorator on a free function
            @logger.log
            def ping(host: str) -> bool: ...

            # Bare decorator on a method
            class DB:
                @logger.log
                def connect(self, host: str) -> None: ...

            # With all custom messages
            @logger.log(
                msg="user lookup",
                running_msg="querying DB…",
                success_msg="found user",
                warning_msg="user data incomplete",
                error_msg="query failed",
            )
            def get_user(user_id: int) -> dict: ...
        """

        def decorator(f: Callable) -> Callable:
            slug = _format_name(f.__qualname__)
            self._call_counts.setdefault(slug, 0)

            if inspect.iscoroutinefunction(f):

                @functools.wraps(f)
                async def async_wrapper(*args, **kwargs):
                    return await self._execute_async(
                        f,
                        slug,
                        args,
                        kwargs,
                        msg=msg,
                        running_msg=running_msg,
                        success_msg=success_msg,
                        error_msg=error_msg,
                        warning_msg=warning_msg,
                    )

                return async_wrapper

            @functools.wraps(f)
            def wrapper(*args, **kwargs):
                return self._execute(
                    f,
                    slug,
                    args,
                    kwargs,
                    msg=msg,
                    running_msg=running_msg,
                    success_msg=success_msg,
                    error_msg=error_msg,
                    warning_msg=warning_msg,
                )

            return wrapper

        # Style 1: @logger.log — Python passes the function directly
        if func is not None:
            return decorator(func)

        # Styles 2 & 3: @logger.log() / @logger.log(msg="...")
        return decorator

    # ------------------------------------------------------------------
    # Core execution logic
    # ------------------------------------------------------------------

    def _execute(
        self,
        func: Callable,
        slug: str,
        args: tuple,
        kwargs: dict,
        *,
        msg: str,
        running_msg: str,
        success_msg: str,
        error_msg: str,
        warning_msg: str,
    ) -> Any:
        """
        Orchestrate a single decorated-function call.

        This is the internal engine behind every ``@logger.log``-wrapped
        call.  It is not part of the public API — use the ``log`` decorator
        instead.

        Execution order
        ~~~~~~~~~~~~~~~
        1. Increment the call counter and build the call-signature string.
        2. Print the **pre-call** line.
        3. Run the function inside ``warnings.catch_warnings`` so that any
           ``warnings.warn()`` calls are captured without suppressing them
           for other warning filters later.
        4. Determine the outcome status (``"success"``, ``"warning"``, or
           ``"error"``).
        5. Print the **post-call** line, including timing and count suffixes.
        6. Optionally persist a :class:`LogEntry` based on ``save_on``.
        7. Re-raise any exception so the caller is unaffected.
        """
        self._call_counts[slug] += 1
        count = self._call_counts[slug]
        call_sig = _format_call(func, args, kwargs)
        timestamp = datetime.now().isoformat(timespec="milliseconds")
        pre_printed = False

        if self.suppress_success_below_s is None:
            self._print_pre(slug, call_sig, msg=msg, running_msg=running_msg)
            pre_printed = True

        caught_warnings: list[warnings.WarningMessage] = []
        error: Exception | None = None
        result: Any = None
        start = time.perf_counter() if self.track_time else None

        try:
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                result = func(*args, **kwargs)
                caught_warnings = list(w)
        except Exception as exc:
            error = exc
        finally:
            elapsed = (time.perf_counter() - start) if start is not None else None

        if error is not None:
            status = "error"
        elif caught_warnings:
            status = "warning"
        else:
            status = "success"

        should_print_post = self._should_print_post(status, elapsed)

        if should_print_post and not pre_printed:
            self._print_pre(slug, call_sig, msg=msg, running_msg=running_msg)
            pre_printed = True

        if should_print_post:
            self._print_post(
                slug,
                call_sig,
                status,
                result=result,
                elapsed=elapsed,
                count=count,
                caught_warnings=caught_warnings,
                error=error,
                msg=msg,
                success_msg=success_msg,
                error_msg=error_msg,
                warning_msg=warning_msg,
            )

        if self.save_logs:
            should_save = (not self.save_on) or (status in self.save_on)
            if should_save:
                entry = LogEntry(
                    slug=slug,
                    func_name=func.__qualname__,
                    call_signature=call_sig,
                    status=status,
                    timestamp=timestamp,
                    elapsed_s=round(elapsed, 6) if elapsed is not None else None,
                    call_count=count,
                    return_repr=_repr_result(result) if error is None else None,
                    custom_msg=msg,
                    warnings_raised=[str(w.message) for w in caught_warnings],
                    error=repr(error) if error else None,
                )
                self._log_entries.append(entry)

        if error is not None:
            raise error

        return result

    async def _execute_async(
        self,
        func: Callable,
        slug: str,
        args: tuple,
        kwargs: dict,
        *,
        msg: str,
        running_msg: str,
        success_msg: str,
        error_msg: str,
        warning_msg: str,
    ) -> Any:
        self._call_counts[slug] += 1
        count = self._call_counts[slug]
        call_sig = _format_call(func, args, kwargs)
        timestamp = datetime.now().isoformat(timespec="milliseconds")
        pre_printed = False

        if self.suppress_success_below_s is None:
            self._print_pre(slug, call_sig, msg=msg, running_msg=running_msg)
            pre_printed = True

        caught_warnings: list[warnings.WarningMessage] = []
        error: Exception | None = None
        result: Any = None
        start = time.perf_counter() if self.track_time else None

        try:
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                result = await func(*args, **kwargs)
                caught_warnings = list(w)
        except Exception as exc:
            error = exc
        finally:
            elapsed = (time.perf_counter() - start) if start is not None else None

        if error is not None:
            status = "error"
        elif caught_warnings:
            status = "warning"
        else:
            status = "success"

        should_print_post = self._should_print_post(status, elapsed)

        if should_print_post and not pre_printed:
            self._print_pre(slug, call_sig, msg=msg, running_msg=running_msg)
            pre_printed = True

        if should_print_post:
            self._print_post(
                slug,
                call_sig,
                status,
                result=result,
                elapsed=elapsed,
                count=count,
                caught_warnings=caught_warnings,
                error=error,
                msg=msg,
                success_msg=success_msg,
                error_msg=error_msg,
                warning_msg=warning_msg,
            )

        if self.save_logs:
            should_save = (not self.save_on) or (status in self.save_on)
            if should_save:
                entry = LogEntry(
                    slug=slug,
                    func_name=func.__qualname__,
                    call_signature=call_sig,
                    status=status,
                    timestamp=timestamp,
                    elapsed_s=round(elapsed, 6) if elapsed is not None else None,
                    call_count=count,
                    return_repr=_repr_result(result) if error is None else None,
                    custom_msg=msg,
                    warnings_raised=[str(w.message) for w in caught_warnings],
                    error=repr(error) if error else None,
                )
                self._log_entries.append(entry)

        if error is not None:
            raise error

        return result

    # ------------------------------------------------------------------
    # Printing helpers
    # ------------------------------------------------------------------

    def _custom_part(self, msg: str) -> str:
        """
        Render the cyan custom-message segment that appears between the slug
        and the status verb on a log line.

        Returns an empty string when ``msg`` is falsy so callers can
        unconditionally concatenate without producing stray separators.
        """
        if not msg:
            return ""
        return f" {Fore.CYAN}{Style.BRIGHT}- {msg}{Style.RESET_ALL}"

    def _print_pre(
        self, slug: str, call_sig: str, *, msg: str, running_msg: str
    ) -> None:
        """
        Print the pre-call log line in blue.

        ``running_msg`` takes precedence over ``msg`` here so callers can
        have distinct "starting" vs "done" wording.

        Example output (colours stripped)::

            [migrate-db] - seeding the database - EXECUTING migrate_db(keep_backups=True)
        """
        label = running_msg or msg
        custom = self._custom_part(label)
        slug_part = f"{Fore.WHITE}{Style.BRIGHT}[{slug}]{Style.RESET_ALL}"
        exec_part = f"{Fore.BLUE}EXECUTING{Style.RESET_ALL} {call_sig}"
        print(f"{slug_part}{custom} - {exec_part}")

    def _print_post(
        self,
        slug: str,
        call_sig: str,
        status: str,
        *,
        result: Any,
        elapsed: float | None,
        count: int,
        caught_warnings: list,
        error: Exception | None,
        msg: str,
        success_msg: str,
        error_msg: str,
        warning_msg: str,
    ) -> None:
        """
        Print the post-call log line, coloured by outcome.

        Colour scheme
        ~~~~~~~~~~~~~
        * **Green**   — SUCCESS: function returned without issues.
        * **Yellow**  — WARNING: function returned but emitted warnings.
        * **Red**     — ERROR: function raised an unhandled exception.

        The status-specific message (``success_msg``, ``warning_msg``,
        ``error_msg``) overrides the generic ``msg`` so you can surface
        meaningful context for each outcome.

        Any captured :mod:`warnings` warnings are printed as indented lines
        immediately below the main log line.

        Example output (colours stripped)::

            [migrate-db] - seeding the database - SUCCESS migrate_db(...) -> [str=''] | TIME: 0.051s | CALL COUNT: 2
              ⚠  UserWarning: Some records were skipped
        """
        if status == "error":
            status_color = Fore.RED
            status_label = "ERROR"
            custom_label = error_msg or msg
        elif status == "warning":
            status_color = Fore.YELLOW
            status_label = "WARNING"
            custom_label = warning_msg or msg
        else:
            status_color = Fore.GREEN
            status_label = "SUCCESS"
            custom_label = success_msg or msg

        custom = self._custom_part(custom_label)
        slug_part = f"{Fore.WHITE}{Style.BRIGHT}[{slug}]{Style.RESET_ALL}"

        if error is not None:
            detail = f"{Fore.RED}{type(error).__name__}: {error}{Style.RESET_ALL}"
        else:
            detail = f"-> [{_repr_result(result)}]"

        suffix_parts = [
            f"{status_color}{Style.BRIGHT}{status_label}{Style.RESET_ALL} "
            f"{call_sig} {detail}"
        ]
        if elapsed is not None:
            suffix_parts.append(
                f"{Fore.MAGENTA}TIME: {_format_elapsed(elapsed)}{Style.RESET_ALL}"
            )
        if self.track_call_count:
            suffix_parts.append(f"{Fore.CYAN}CALL COUNT: {count}{Style.RESET_ALL}")

        print(f"{slug_part}{custom} - {' | '.join(suffix_parts)}")

        for w in caught_warnings:
            print(
                f"  {Fore.YELLOW}⚠  {w.category.__name__}: {w.message}{Style.RESET_ALL}"
            )

    # ------------------------------------------------------------------
    # Convenience standalone printers
    # ------------------------------------------------------------------

    @staticmethod
    def success(msg: str) -> None:
        """
        Print a standalone green success message.

        Use this for one-off status lines that don't belong to a specific
        decorated function, e.g. at the end of a pipeline::

            logger.success("All migrations applied.")
        """
        print(f"{Fore.GREEN}✔{Style.RESET_ALL}  {msg}")

    @staticmethod
    def error(msg: str) -> None:
        """
        Print a standalone red error message.

        Use for top-level error reporting outside of decorated functions::

            logger.error("Config file not found — aborting.")
        """
        print(f"{Fore.RED}✘{Style.RESET_ALL}  {msg}")

    @staticmethod
    def warning(msg: str) -> None:
        """
        Print a standalone yellow warning message.

        Use for advisory messages that don't correspond to a specific
        function call::

            logger.warning("PROD_KEY is not set, falling back to dev key.")
        """
        print(f"{Fore.YELLOW}⚠{Style.RESET_ALL}  {msg}")

    # ------------------------------------------------------------------
    # Saved logs access
    # ------------------------------------------------------------------

    def get_logs(self) -> list[LogEntry]:
        """
        Return a copy of all accumulated :class:`LogEntry` objects.

        Only populated when ``save_logs=True``.  The list is filtered by
        ``save_on`` at write-time, so entries here already match whatever
        filter was configured.

        Returns
        -------
        list[LogEntry]
            Entries in chronological order (oldest first).

        Example
        -------
        ::

            for entry in logger.get_logs():
                print(entry.slug, entry.status, entry.elapsed_s)
        """
        return list(self._log_entries)

    def get_logs_for(self, slug: str) -> list[LogEntry]:
        """
        Return accumulated :class:`LogEntry` objects for one specific function.

        Parameters
        ----------
        slug:
            The kebab-case slug of the function, e.g. ``"migrate-db"`` or
            ``"data-pipeline.run"``.  This is the same string shown inside
            the ``[brackets]`` on log lines.

        Returns
        -------
        list[LogEntry]
            All saved entries whose ``slug`` matches, in chronological order.

        Example
        -------
        ::

            errors = [e for e in logger.get_logs_for("connect") if e.status == "error"]
        """
        return [e for e in self._log_entries if e.slug == slug]

    # ------------------------------------------------------------------
    # Internal: file persistence
    # ------------------------------------------------------------------

    def _flush_logs(self) -> None:
        if self.save_backend == "json_database":
            self._flush_to_json_database()
            return

        self._flush_to_file()

    def _flush_to_file(self) -> None:
        """
        Append all accumulated :class:`LogEntry` objects to ``log_file`` as JSONL.

        Called automatically by :mod:`atexit` on normal interpreter exit when
        both ``save_logs=True`` and ``log_file`` are set.  Each entry is
        serialised via :func:`dataclasses.asdict` and written as one JSON
        object per line.

        The file is opened in **append** mode (``"a"``), so multiple runs
        accumulate entries rather than overwriting previous ones.  Parent
        directories are created if they do not exist.

        This method is a no-op if ``_log_entries`` is empty.
        """
        if not self._log_entries or not self.log_file:
            return
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        with self.log_file.open("a", encoding="utf-8") as f:
            for entry in self._log_entries:
                f.write(json.dumps(asdict(entry)) + "\n")
        print(
            f"{Fore.CYAN}[jays-logger] Wrote {len(self._log_entries)} "
            f"entries -> {self.log_file}{Style.RESET_ALL}"
        )

    def _flush_to_json_database(self) -> None:
        if not self._log_entries or not self.log_file:
            return

        self.log_file.parent.mkdir(parents=True, exist_ok=True)

        db = JsonDatabase(self.log_file, models=CurrentLoggerLogStore)
        with db as log_store:
            for entry in self._log_entries:
                log_store.entries.append(CurrentLoggerLogEntry(**asdict(entry)))

            db.set(log_store)

        print(
            f"{Fore.CYAN}[jays-logger] Wrote {len(self._log_entries)} "
            f"entries to JsonDatabase -> {self.log_file}{Style.RESET_ALL}"
        )


# ---------------------------------------------------------------------------
# Example / smoke test  (python jays_logger.py)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logger = JaysLogger(
        track_time=True,
        track_call_count=True,
        save_logs=True,
        save_on=["error", "warning"],
        log_file="jays_logger_output.jsonl",
    )

    @logger.log(msg="seeding the database")
    def migrate_db(keep_backups: bool = True, debug: bool = False) -> str:
        time.sleep(0.05)
        return ""

    @logger.log(msg="crunching numbers", warning_msg="non-critical issue detected")
    def process_data(records: int) -> list:
        warnings.warn("Some records were skipped", UserWarning)
        return [1, 2, 3]

    @logger.log(msg="connecting to DB", error_msg="connection refused")
    def connect(host: str, port: int = 5432) -> None:
        raise ConnectionRefusedError(f"Cannot reach {host}:{port}")

    class DataPipeline:
        @logger.log
        def run(self, dry_run: bool = False) -> dict:
            time.sleep(0.02)
            return {"processed": 42}

    print("\n" + "=" * 60)
    print("  JaysLogger demo")
    print("=" * 60 + "\n")

    migrate_db(keep_backups=True, debug=False)
    print()
    migrate_db(keep_backups=False)
    print()
    process_data(records=500)
    print()
    try:
        connect("prod-db.internal")
    except ConnectionRefusedError:
        pass
    print()
    DataPipeline().run(dry_run=True)
    print()

    print(f"Saved {len(logger.get_logs())} log entries (errors + warnings only).")
