"""Tkinter-based graphical interface for the Mac organizer."""
from __future__ import annotations

import contextlib
import importlib
import importlib.util
import io
import queue
import threading
from pathlib import Path
from typing import Any

tk: Any | None = None
ttk: Any | None = None
filedialog: Any | None = None
messagebox: Any | None = None

from .core import DEFAULT_ROOT_NAME, Organizer


def _ensure_tk() -> None:
    """Load tkinter modules on demand."""

    global tk, ttk, filedialog, messagebox
    if tk is not None:
        return
    if importlib.util.find_spec("tkinter") is None:
        raise RuntimeError("Tkinter is not available on this system. Install tkinter to use the GUI.")
    tk_module = importlib.import_module("tkinter")
    ttk_module = importlib.import_module("tkinter.ttk")
    filedialog_module = importlib.import_module("tkinter.filedialog")
    messagebox_module = importlib.import_module("tkinter.messagebox")
    tk = tk_module
    ttk = ttk_module
    filedialog = filedialog_module
    messagebox = messagebox_module


class _QueueWriter(io.TextIOBase):
    """File-like object that sends writes to a queue for UI consumption."""

    def __init__(self, event_queue: "queue.Queue[_GuiEvent]") -> None:
        self._queue = event_queue

    def write(self, text: str) -> int:  # pragma: no cover - simple delegation
        if text:
            self._queue.put(_GuiEvent("log", text))
        return len(text)

    def flush(self) -> None:  # pragma: no cover - nothing to do
        return None


class _GuiEvent:
    def __init__(self, kind: str, payload: str | None = None) -> None:
        self.kind = kind
        self.payload = payload


class OrganizerApp:
    """Encapsulates the Tkinter UI and orchestrates organizer runs."""

    def __init__(self, root: Any) -> None:
        _ensure_tk()
        self.root = root
        self.root.title("Mac Organizer")
        self.event_queue: "queue.Queue[_GuiEvent]" = queue.Queue()
        self._build_ui()
        self._poll_events()

    def _build_ui(self) -> None:
        padding = {"padx": 12, "pady": 6}

        container = ttk.Frame(self.root)
        container.grid(row=0, column=0, sticky="nsew")
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        target_label = ttk.Label(container, text="Target folder:")
        target_label.grid(row=0, column=0, sticky="w", **padding)

        self.target_var = tk.StringVar()
        self.target_entry = ttk.Entry(container, textvariable=self.target_var, width=50)
        self.target_entry.grid(row=0, column=1, sticky="ew", **padding)
        container.columnconfigure(1, weight=1)

        browse_button = ttk.Button(container, text="Browse…", command=self._choose_directory)
        browse_button.grid(row=0, column=2, sticky="ew", **padding)

        self.apply_var = tk.BooleanVar(value=False)
        self.dry_run_var = tk.BooleanVar(value=False)
        self.remove_duplicates_var = tk.BooleanVar(value=True)

        apply_check = ttk.Checkbutton(container, text="Apply changes (move files)", variable=self.apply_var)
        apply_check.grid(row=1, column=0, columnspan=2, sticky="w", **padding)

        dry_run_check = ttk.Checkbutton(
            container,
            text="Force dry run (preview only)",
            variable=self.dry_run_var,
        )
        dry_run_check.grid(row=2, column=0, columnspan=2, sticky="w", **padding)

        remove_dupes_check = ttk.Checkbutton(
            container,
            text="Relocate duplicates to Organized/Duplicates",
            variable=self.remove_duplicates_var,
        )
        remove_dupes_check.grid(row=3, column=0, columnspan=2, sticky="w", **padding)

        self.run_button = ttk.Button(container, text="Run Organizer", command=self._run_organizer)
        self.run_button.grid(row=4, column=0, columnspan=3, sticky="ew", **padding)

        log_label = ttk.Label(container, text="Output:")
        log_label.grid(row=5, column=0, sticky="w", **padding)

        self.log_widget = tk.Text(container, height=18, wrap="word", state="disabled")
        self.log_widget.grid(row=6, column=0, columnspan=3, sticky="nsew", padx=12, pady=(0, 12))
        container.rowconfigure(6, weight=1)

        scrollbar = ttk.Scrollbar(container, orient="vertical", command=self.log_widget.yview)
        scrollbar.grid(row=6, column=3, sticky="ns", pady=(0, 12))
        self.log_widget["yscrollcommand"] = scrollbar.set

    def _choose_directory(self) -> None:
        path = filedialog.askdirectory()
        if path:
            self.target_var.set(path)

    def _append_log(self, message: str) -> None:
        self.log_widget.configure(state="normal")
        self.log_widget.insert("end", message)
        self.log_widget.see("end")
        self.log_widget.configure(state="disabled")

    def _run_organizer(self) -> None:
        target_text = self.target_var.get().strip()
        if not target_text:
            messagebox.showerror("Missing target", "Please choose a folder to organize.")
            return

        target = Path(target_text).expanduser()

        self.run_button.configure(state="disabled")
        self.log_widget.configure(state="normal")
        self.log_widget.delete("1.0", "end")
        self.log_widget.configure(state="disabled")
        self.event_queue.put(_GuiEvent("log", "Starting organizer…\n"))

        thread = threading.Thread(
            target=self._execute_organizer,
            args=(target, self.apply_var.get(), self.dry_run_var.get(), self.remove_duplicates_var.get()),
            daemon=True,
        )
        thread.start()

    def _execute_organizer(
        self,
        target: Path,
        apply_changes: bool,
        dry_run: bool,
        remove_duplicates: bool,
    ) -> None:
        writer = _QueueWriter(self.event_queue)
        try:
            organizer = Organizer(
                target,
                apply_changes=apply_changes,
                dry_run=dry_run,
                remove_duplicates=remove_duplicates,
                root_name=DEFAULT_ROOT_NAME,
            )
            with contextlib.redirect_stdout(writer), contextlib.redirect_stderr(writer):
                organizer.run()
        except Exception as exc:  # pragma: no cover - surfaced via GUI
            self.event_queue.put(_GuiEvent("error", str(exc)))
        finally:
            self.event_queue.put(_GuiEvent("done"))

    def _poll_events(self) -> None:
        try:
            while True:
                event = self.event_queue.get_nowait()
                if event.kind == "log":
                    self._append_log(event.payload or "")
                elif event.kind == "error":
                    messagebox.showerror("Organizer error", event.payload or "Unknown error")
                elif event.kind == "done":
                    self.run_button.configure(state="normal")
        except queue.Empty:
            pass
        finally:
            self.root.after(100, self._poll_events)


def launch() -> None:
    """Launch the graphical organizer application."""

    _ensure_tk()
    assert tk is not None  # For type checkers
    root = tk.Tk()
    OrganizerApp(root)
    root.mainloop()


__all__ = ["launch", "OrganizerApp"]
