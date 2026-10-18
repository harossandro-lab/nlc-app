"""Team sync in the window: a status label in the top bar (click it to sign in or sync now), a timer that syncs in a
background thread, and the sign-in dialog. The work itself lives in nlc/sync/service.py."""
from datetime import datetime

from PySide6.QtCore import QObject, QRunnable, Qt, QThreadPool, QTimer, Signal
from PySide6.QtWidgets import (QApplication, QDialog, QDialogButtonBox, QFormLayout, QLabel, QLineEdit, QVBoxLayout)

from ..sync import service
from ..sync.supabase import AuthError, SupabaseRemote

INTERVAL_MS = 30_000


class _Worker(QRunnable):
    def __init__(self, db_path, remote, done):
        super().__init__()
        self.db_path, self.remote, self.done = db_path, remote, done

    def run(self):
        self.done.emit(service.run_sync(self.db_path, self.remote))


class SyncController(QObject):
    """Owns the status text. `data_changed` fires when other people's edits were pulled in."""
    status_changed = Signal(str, str)        # text, tone: ok | warn | off
    data_changed = Signal()
    _finished = Signal(object)

    def __init__(self, db_path, parent=None):
        super().__init__(parent)
        self.db_path = str(db_path)
        self.remote = service.make_remote()
        self.busy = False
        self._finished.connect(self._on_finished)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.sync_now)

    def start(self) -> None:
        self.reload_remote()
        self.timer.start(INTERVAL_MS)
        self.sync_now()

    def reload_remote(self) -> None:
        self.remote = service.make_remote()
        if self.remote is None:
            self.status_changed.emit("Team sync: not set up", "off")
        elif not self.remote.logged_in:
            self.status_changed.emit("Team sync: sign in", "warn")

    def sync_now(self) -> None:
        if self.busy or self.remote is None or not self.remote.logged_in:
            return
        self.busy = True
        self.status_changed.emit("Syncing…", "ok")
        QThreadPool.globalInstance().start(_Worker(self.db_path, self.remote, self._finished))

    def _on_finished(self, res) -> None:
        self.busy = False
        if res.status == "ok":
            when = datetime.now().strftime("%H:%M")
            tail = f" · {res.pending} pending" if res.pending else ""
            self.status_changed.emit(f"Synced {when}{tail}", "ok")
            if res.pulled:
                self.data_changed.emit()
        elif res.status == "login":
            self.status_changed.emit("Team sync: sign in", "warn")
        elif res.status == "offline":
            n = f" ({res.pending} waiting)" if res.pending else ""
            self.status_changed.emit(f"Offline{n} — will retry", "warn")

    def stop(self) -> None:
        self.timer.stop()


class SyncDialog(QDialog):
    """Project address + public key (once per computer) and the person's own e-mail and password."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Team sync")
        cfg = service.load_config() or {}
        self.url = QLineEdit(cfg.get("url", ""))
        self.url.setPlaceholderText("https://xxxx.supabase.co")
        self.key = QLineEdit(cfg.get("anon_key", ""))
        self.key.setPlaceholderText("anon public key")
        self.email = QLineEdit()
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.Password)
        self.error = QLabel("")
        self.error.setStyleSheet("color: #B23A2E;")
        self.error.setWordWrap(True)
        form = QFormLayout()
        form.addRow("Project URL", self.url)
        form.addRow("Anon key", self.key)
        form.addRow("E-mail", self.email)
        form.addRow("Password", self.password)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("Sign in")
        buttons.accepted.connect(self._sign_in)
        buttons.rejected.connect(self.reject)
        lay = QVBoxLayout(self)
        note = QLabel("Ask the administrator for the project URL and key. Your password is never saved.")
        note.setObjectName("hint")
        note.setWordWrap(True)
        lay.addWidget(note)
        lay.addLayout(form)
        lay.addWidget(self.error)
        lay.addWidget(buttons)
        self.setMinimumWidth(440)

    def _sign_in(self) -> None:
        url, key = self.url.text().strip(), self.key.text().strip()
        if not url.startswith("http") or not key or not self.email.text().strip() or not self.password.text():
            self.error.setText("Fill in all four fields.")
            return
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            SupabaseRemote(url, key).sign_in(self.email.text().strip(), self.password.text())
        except AuthError as e:
            self.error.setText(str(e))
            return
        except ConnectionError:
            self.error.setText("Could not reach the server. Check the URL and your internet.")
            return
        finally:
            QApplication.restoreOverrideCursor()
        service.save_config(url, key)
        self.accept()
