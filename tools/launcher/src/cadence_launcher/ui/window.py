from __future__ import annotations

import time
from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import QEasingCurve, Qt, QThreadPool, QTimer, QVariantAnimation
from PySide6.QtGui import QIcon, QShowEvent
from PySide6.QtSvgWidgets import QSvgWidget
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStackedLayout,
    QVBoxLayout,
    QWidget,
)

from ..i18n import get_locale, tr
from ..runtime import (
    AppStatus,
    ServiceStatus,
    cancel_streaming_command,
    check_prerequisites,
    collect_status,
    open_in_browser,
    persist_language,
    start_stack,
    stop_stack,
    stopped_status,
)
from ..workers import Worker
from .constants import (
    MAX_ACTIVITY_TEXT,
    MAX_ELAPSED_TEXT,
    MAX_HEADER_STATUS,
    PROGRESS_BLEND,
    PROGRESS_SNAP,
    SERVICE_ROW_HEIGHT,
    SERVICES_PADDING,
    SHELL_GAP,
    STATE_ICON,
    WINDOW_HEIGHT,
    WINDOW_WIDTH,
)
from .widgets import (
    ActivityRevealer,
    AnimatedProgressBar,
    ServiceWidgets,
    SpinnerWidget,
    clipped_label,
    truncate_text,
)


class LauncherWindow(QMainWindow):
    def __init__(self, repo_root: Path) -> None:
        super().__init__()
        self.repo_root = repo_root
        self.thread_pool = QThreadPool.globalInstance()

        self.current_mode = "stopped"
        self.web_ready = False
        self.busy = False
        self.started = False
        self.startup_ready = {"check": False, "status": False}
        self.status_fetch_inflight = False

        self.action_started_at: float | None = None
        self.current_action: str | None = None
        self.activity_heading = ""
        self.last_step_text = ""
        self.last_status_text = ""
        self.last_progress = 0.0
        self.target_progress = 0.0

        self.service_widgets: dict[str, ServiceWidgets] = {}
        self.service_pulse_timers: dict[str, QTimer] = {}

        self.progress_anim_timer: QTimer | None = None
        self.loading_tick_timer: QTimer | None = None
        self.status_poll_timer: QTimer | None = None
        self.action_status_timer: QTimer | None = None
        self.scrim_fade_timer: QTimer | None = None
        self.resize_anim: QVariantAnimation | None = None
        self.finish_action_timer: QTimer | None = None
        self._closing = False
        self._screen_placed = False
        self._startup_spinner_started = False

        self.setWindowTitle("Cadence")
        self.setFixedSize(WINDOW_WIDTH, WINDOW_HEIGHT)
        icon_path = Path(__file__).resolve().parent.parent / "assets" / "cadence.svg"
        self.setWindowIcon(QIcon(str(icon_path)))

        shell = QWidget(objectName="ShellRoot")
        self.setCentralWidget(shell)

        root_layout = QStackedLayout(shell)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setStackingMode(QStackedLayout.StackAll)

        self.main_shell = QWidget()
        self.shell_layout = QVBoxLayout(self.main_shell)
        self.shell_layout.setContentsMargins(14, 14, 14, 14)
        self.shell_layout.setSpacing(10)

        self.status_label = clipped_label("…", max_chars=MAX_HEADER_STATUS)
        self.toggle_btn = QPushButton(tr("btn.start"))
        self.toggle_btn.setProperty("variant", "start")
        self.toggle_btn.setEnabled(False)
        self.toggle_btn.clicked.connect(self.on_toggle)

        self.open_btn = QPushButton(tr("btn.open"))
        self.open_btn.setProperty("variant", "open")
        self.open_btn.setEnabled(False)
        self.open_btn.clicked.connect(self.on_open)

        self.shell_layout.addWidget(self.build_header(icon_path))
        self.shell_layout.addWidget(self.build_actions())
        self.shell_layout.addWidget(self.build_services(), 1)

        self.activity_panel = self.build_activity_panel()
        self.activity_revealer = ActivityRevealer(self.activity_panel)
        self.shell_layout.addWidget(self.activity_revealer)

        self.loading_overlay = self.build_loading_overlay()
        self.set_scrim_opacity(1.0)
        root_layout.addWidget(self.main_shell)
        root_layout.addWidget(self.loading_overlay)

        self.begin_startup()

    def center_on_screen(self) -> None:
        screen = self.screen() or QApplication.primaryScreen()
        if screen is None:
            return
        available = screen.availableGeometry()
        self.move(
            available.x() + (available.width() - self.width()) // 2,
            available.y() + (available.height() - self.height()) // 2,
        )

    def showEvent(self, event: QShowEvent) -> None:
        super().showEvent(event)
        if not self._screen_placed:
            self.center_on_screen()
            self._screen_placed = True
        if not self._startup_spinner_started:
            self.startup_spinner.start()
            self._startup_spinner_started = True

    def run_worker(
        self,
        task: Callable[[Callable[[str], None]], object],
        *,
        finished: Callable[[object], None],
        failed: Callable[[str], None] | None = None,
        progress: Callable[[str], None] | None = None,
    ) -> None:
        if self._closing:
            return
        worker = Worker(task)
        worker.signals.setParent(self)
        worker.signals.finished.connect(finished, Qt.ConnectionType.QueuedConnection)
        if failed is not None:
            worker.signals.failed.connect(failed, Qt.ConnectionType.QueuedConnection)
        if progress is not None:
            worker.signals.progress.connect(
                progress,
                Qt.ConnectionType.QueuedConnection,
            )
        self.thread_pool.start(worker)

    def stop_timers(self) -> None:
        for timer in (
            self.progress_anim_timer,
            self.loading_tick_timer,
            self.status_poll_timer,
            self.action_status_timer,
            self.scrim_fade_timer,
            self.finish_action_timer,
        ):
            if timer is not None:
                timer.stop()
        for timer in self.service_pulse_timers.values():
            timer.stop()
        self.service_pulse_timers.clear()
        if self.resize_anim is not None:
            self.resize_anim.stop()
        if self.activity_revealer._animation is not None:
            self.activity_revealer._animation.stop()

    def closeEvent(self, event) -> None:
        self._closing = True
        cancel_streaming_command()
        self.stop_timers()
        self.startup_spinner.stop()
        self.action_spinner.stop()
        self.thread_pool.waitForDone(5000)
        super().closeEvent(event)

    def build_header(self, icon_path: Path) -> QWidget:
        card = QFrame()
        card.setProperty("panel", True)
        layout = QHBoxLayout(card)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(12)

        icon = QSvgWidget(str(icon_path), card)
        icon.setFixedSize(40, 40)
        layout.addWidget(icon)

        text = QVBoxLayout()
        text.setSpacing(2)
        title = QLabel("Cadence")
        title.setProperty("role", "title")
        text.addWidget(title)

        self.status_label.setProperty("role", "status")
        text.addWidget(self.status_label)
        layout.addLayout(text, 1)
        layout.addWidget(self.build_language_switch())
        return card

    def build_language_switch(self) -> QWidget:
        box = QWidget()
        row = QHBoxLayout(box)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(4)

        self.lang_en_btn = QPushButton("EN")
        self.lang_en_btn.setProperty("variant", "lang")
        self.lang_en_btn.clicked.connect(lambda: self.set_language("en"))

        self.lang_ru_btn = QPushButton("RU")
        self.lang_ru_btn.setProperty("variant", "lang")
        self.lang_ru_btn.clicked.connect(lambda: self.set_language("ru"))

        row.addWidget(self.lang_en_btn)
        row.addWidget(self.lang_ru_btn)
        self.sync_language_buttons()
        return box

    def sync_language_buttons(self) -> None:
        current = get_locale()
        for code, button in (("en", self.lang_en_btn), ("ru", self.lang_ru_btn)):
            button.setProperty("active", current == code)
            button.style().unpolish(button)
            button.style().polish(button)

    def set_language(self, language: str) -> None:
        if self.busy or language == get_locale():
            return
        persist_language(language)
        self.sync_language_buttons()
        self.retranslate_ui()
        if self.started:
            self.refresh_status()

    def retranslate_ui(self) -> None:
        running = self.current_mode != "stopped"
        if self.busy:
            self.set_status_text_animated(self.header_action_status(), running=True)
        elif self.started:
            if self.current_mode == "stopped":
                text = tr("status.stopped")
                running = False
            elif self.web_ready:
                text = tr("status.running")
                running = True
            else:
                text = tr("status.starting")
                running = True
            self.set_status_text_animated(text, running=running)
        self.set_toggle_button(running)
        self.open_btn.setText(tr("btn.open"))
        self.services_head.setText(tr("services.title"))
        self.loading_title.setText(tr("loading.title"))
        if not self.startup_ready["check"]:
            self.splash_status.setText(tr("loading.check_env"))
        elif not self.startup_ready["status"]:
            self.splash_status.setText(tr("loading.read_status"))
        if self.activity_revealer.is_revealed():
            self.update_loading_labels()

    def build_actions(self) -> QWidget:
        card = QFrame()
        card.setProperty("panel", True)
        layout = QHBoxLayout(card)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(8)

        expanding = QSizePolicy.Policy.Expanding
        preferred = QSizePolicy.Policy.Preferred
        self.toggle_btn.setSizePolicy(expanding, preferred)
        self.open_btn.setSizePolicy(expanding, preferred)
        layout.addWidget(self.toggle_btn, 1)
        layout.addWidget(self.open_btn, 1)
        return card

    def build_services(self) -> QWidget:
        card = QFrame()
        card.setProperty("panel", True)
        outer = QVBoxLayout(card)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        head = QLabel(tr("services.title"))
        head.setProperty("role", "servicesHead")
        self.services_head = head
        outer.addWidget(head)

        self.services_scroller = QScrollArea(objectName="ServicesScroller")
        self.services_scroller.setWidgetResizable(True)
        self.services_scroller.setFrameShape(QFrame.Shape.NoFrame)
        self.services_scroller.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.services_scroller.setObjectName("ServicesScroller")

        self.services_container = QWidget(objectName="ServicesContainer")
        self.services_layout = QVBoxLayout(self.services_container)
        self.services_layout.setContentsMargins(14, 0, 14, 12)
        self.services_layout.setSpacing(0)
        self.services_layout.addStretch(1)

        self.services_scroller.setWidget(self.services_container)
        viewport = self.services_scroller.viewport()
        viewport.setAutoFillBackground(False)
        viewport.setStyleSheet("background-color: transparent;")
        self.services_scroller.setStyleSheet(
            "QScrollArea#ServicesScroller { background: transparent; border: none; }"
        )
        outer.addWidget(self.services_scroller, 1)
        return card

    def build_activity_panel(self) -> QWidget:
        card = QFrame()
        card.setProperty("activity", True)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(0)

        head = QHBoxLayout()
        head.setSpacing(10)

        spinner_wrap = QWidget()
        spinner_wrap.setProperty("role", "activitySpinnerWrap")
        spinner_layout = QHBoxLayout(spinner_wrap)
        spinner_layout.setContentsMargins(0, 0, 0, 0)
        self.action_spinner = SpinnerWidget(spinner_wrap, size=18)
        spinner_layout.addWidget(self.action_spinner, 0, Qt.AlignmentFlag.AlignCenter)
        head.addWidget(spinner_wrap)

        text_col = QVBoxLayout()
        text_col.setSpacing(2)
        self.activity_title = clipped_label(max_chars=MAX_ACTIVITY_TEXT)
        self.activity_title.setProperty("role", "activityTitle")
        text_col.addWidget(self.activity_title)
        self.activity_detail = clipped_label(max_chars=MAX_ACTIVITY_TEXT)
        self.activity_detail.setProperty("role", "activityDetail")
        text_col.addWidget(self.activity_detail)
        head.addLayout(text_col, 1)

        self.activity_percent = QLabel("0%")
        self.activity_percent.setProperty("role", "activityPercent")
        self.activity_percent.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
        )
        head.addWidget(self.activity_percent)
        layout.addLayout(head)
        layout.addSpacing(8)

        self.progress_bar = AnimatedProgressBar()
        self.progress_bar.setTextVisible(False)
        layout.addWidget(self.progress_bar)
        layout.addSpacing(6)

        self.activity_elapsed = clipped_label(
            tr("activity.elapsed", elapsed=0),
            max_chars=MAX_ELAPSED_TEXT,
        )
        self.activity_elapsed.setProperty("role", "activityElapsed")
        layout.addWidget(self.activity_elapsed)
        return card

    def build_loading_overlay(self) -> QWidget:
        overlay = QWidget(objectName="LoadingOverlay")
        layout = QVBoxLayout(overlay)
        layout.setContentsMargins(0, 0, 0, 0)

        center = QVBoxLayout()
        center.addStretch(1)

        card = QFrame()
        card.setProperty("overlayCard", True)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(36, 28, 36, 28)
        card_layout.setSpacing(12)

        self.startup_spinner = SpinnerWidget(card, size=40)
        card_layout.addWidget(self.startup_spinner, 0, Qt.AlignmentFlag.AlignHCenter)

        title = QLabel(tr("loading.title"))
        title.setProperty("role", "overlayTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.loading_title = title
        card_layout.addWidget(title)

        self.splash_status = QLabel(tr("loading.check_env"))
        self.splash_status.setProperty("role", "overlaySubtitle")
        self.splash_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(self.splash_status)

        center.addWidget(card, 0, Qt.AlignmentFlag.AlignHCenter)
        center.addStretch(1)
        layout.addLayout(center)

        self.scrim_opacity = 1.0
        return overlay

    def begin_startup(self) -> None:
        def task(_progress: Callable[[str], None]) -> None:
            check_prerequisites(self.repo_root)

        self.run_worker(task, finished=self.on_check_ok, failed=self.on_check_error)

    def on_check_ok(self, _: object) -> None:
        if self._closing:
            return
        self.startup_ready["check"] = True
        self.splash_status.setText(tr("loading.read_status"))
        self.fetch_startup_status()

    def on_check_error(self, message: str) -> None:
        self.startup_spinner.stop()
        QMessageBox.critical(self, tr("msg.cadence_unavailable"), message)
        self.close()

    def fetch_startup_status(self) -> None:
        if self.status_fetch_inflight:
            return
        self.status_fetch_inflight = True

        def task(_progress: Callable[[str], None]) -> AppStatus:
            return collect_status(self.repo_root)

        self.run_worker(
            task,
            finished=self.on_startup_status,
            failed=self.on_startup_status_error,
        )

    def on_startup_status(self, status: AppStatus) -> None:
        if self._closing:
            return
        self.status_fetch_inflight = False
        self.startup_ready["status"] = True
        self.apply_status(status, initial=True)
        self.finish_startup()

    def on_startup_status_error(self, message: str) -> None:
        self.status_fetch_inflight = False
        self.startup_spinner.stop()
        QMessageBox.critical(self, tr("msg.status_load_failed"), message)
        self.close()

    def finish_startup(self) -> None:
        if not (self.startup_ready["check"] and self.startup_ready["status"]):
            return
        self.started = True
        self.startup_spinner.stop()
        self.collapse_activity_panel()
        self.fade_out_scrim()

    def set_scrim_opacity(self, opacity: float) -> None:
        self.scrim_opacity = max(0.0, min(1.0, opacity))
        alpha = int(self.scrim_opacity * 140)
        self.loading_overlay.setStyleSheet(
            "QWidget#LoadingOverlay {"
            f" background-color: rgba(232, 235, 241, {alpha});"
            " }"
        )

    def fade_out_scrim(self) -> None:
        if self.scrim_fade_timer is not None:
            self.scrim_fade_timer.stop()

        def tick() -> None:
            next_opacity = self.scrim_opacity - 0.12
            if next_opacity <= 0.0:
                self.set_scrim_opacity(0.0)
                self.loading_overlay.hide()
                self.update_buttons()
                self.start_status_poll()
                if self.scrim_fade_timer is not None:
                    self.scrim_fade_timer.stop()
                return
            self.set_scrim_opacity(next_opacity)

        self.scrim_fade_timer = QTimer(self)
        self.scrim_fade_timer.setInterval(16)
        self.scrim_fade_timer.timeout.connect(tick)
        self.scrim_fade_timer.start()

    def start_status_poll(self) -> None:
        if self.status_poll_timer is not None:
            self.status_poll_timer.stop()
        self.status_poll_timer = QTimer(self)
        self.status_poll_timer.setInterval(3000)
        self.status_poll_timer.timeout.connect(self.refresh_status)
        self.status_poll_timer.start()

    def refresh_status(self, initial: bool = False) -> None:
        if self.status_fetch_inflight or self._closing:
            return
        self.status_fetch_inflight = True

        def task(_progress: Callable[[str], None]) -> AppStatus:
            return collect_status(self.repo_root)

        self.run_worker(
            task,
            finished=lambda status: self.on_status_ready(status, initial=initial),
            failed=self.on_status_error,
        )

    def on_status_ready(self, status: AppStatus, *, initial: bool = False) -> None:
        if self._closing:
            self.status_fetch_inflight = False
            return
        self.status_fetch_inflight = False
        self.apply_status(status, initial=initial)

    def on_status_error(self, message: str) -> None:
        self.status_fetch_inflight = False
        if self.started and not self.busy:
            self.set_status_text_animated(
                tr("status.error", message=message),
                running=False,
            )

    def apply_status(self, status: AppStatus, *, initial: bool = False) -> None:
        self.current_mode = status.mode
        self.web_ready = status.web_ready
        running = status.mode != "stopped"

        if self.busy:
            self.set_status_text_animated(self.header_action_status(), running=True)
        else:
            self.set_status_text_animated(self.status_text(status), running=running)

        self.set_toggle_button(running)
        self.render_services(status.services, initial=initial)
        self.last_progress = self.progress_value(status)

        if self.busy:
            self.animate_progress_to(self.last_progress)
            if self.activity_revealer.is_revealed():
                self.update_loading_labels()

        if self.started:
            self.update_buttons()

    def status_text(self, status: AppStatus) -> str:
        if status.mode == "stopped":
            return tr("status.stopped")
        if status.api_ready and status.web_ready:
            return tr("status.running")
        return tr("status.starting")

    def header_action_status(self) -> str:
        if self.current_action == "stop":
            return tr("status.stopping")
        return tr("status.starting")

    def set_toggle_button(self, running: bool) -> None:
        if running:
            self.toggle_btn.setText(tr("btn.stop"))
            self.toggle_btn.setProperty("variant", "stop")
        else:
            self.toggle_btn.setText(tr("btn.start"))
            self.toggle_btn.setProperty("variant", "start")
        self.toggle_btn.style().unpolish(self.toggle_btn)
        self.toggle_btn.style().polish(self.toggle_btn)
        if self.busy:
            self.toggle_btn.setEnabled(False)

    def set_status_text_animated(self, text: str, running: bool) -> None:
        text = truncate_text(text, MAX_HEADER_STATUS)
        if text == self.last_status_text:
            self.status_label.setProperty("running", running)
            self.status_label.style().unpolish(self.status_label)
            self.status_label.style().polish(self.status_label)
            return

        self.last_status_text = text
        self.status_label.setText(text)
        self.status_label.setProperty("running", running)
        self.status_label.style().unpolish(self.status_label)
        self.status_label.style().polish(self.status_label)

    def render_services(
        self,
        services: list[ServiceStatus],
        *,
        initial: bool = False,
    ) -> None:
        seen: set[str] = set()
        for index, service in enumerate(services):
            seen.add(service.name)
            widgets = self.service_widgets.get(service.name)
            if widgets is None:
                row, badge = self.service_line(service)
                if initial:
                    row.setVisible(False)
                    QTimer.singleShot(40 + index * 35, row.show)
                self.services_layout.insertWidget(self.services_layout.count() - 1, row)
                widgets = ServiceWidgets(row=row, badge=badge, state=service.state)
                self.service_widgets[service.name] = widgets
            elif widgets.state != service.state:
                self.set_badge_state(widgets.badge, service.state, animate=True)
                self.pulse_service_row(service.name, widgets.row)
                widgets.state = service.state

        for name in list(self.service_widgets):
            if name in seen:
                continue
            widgets = self.service_widgets.pop(name)
            widgets.row.deleteLater()

        self.sync_services_scroller()

    def service_line(self, service: ServiceStatus) -> tuple[QFrame, QLabel]:
        row = QFrame()
        row.setProperty("service", True)
        row.setFixedHeight(SERVICE_ROW_HEIGHT)
        layout = QHBoxLayout(row)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(8)

        name = QLabel(service.label)
        name.setProperty("role", "serviceName")
        name.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        layout.addWidget(name)

        badge = QLabel()
        badge.setProperty("role", "badge")
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.set_badge_state(badge, service.state)
        layout.addWidget(badge)
        return row, badge

    def set_badge_state(
        self,
        badge: QLabel,
        state: str,
        *,
        animate: bool = False,
    ) -> None:
        badge.setText(STATE_ICON.get(state, "○"))
        badge.setProperty("state", state)
        badge.setProperty("flash", False)
        badge.style().unpolish(badge)
        badge.style().polish(badge)

        if not animate:
            return

        badge.setProperty("flash", True)
        badge.style().unpolish(badge)
        badge.style().polish(badge)
        QTimer.singleShot(240, lambda: self.clear_badge_flash(badge))

    def clear_badge_flash(self, badge: QLabel) -> None:
        badge.setProperty("flash", False)
        badge.style().unpolish(badge)
        badge.style().polish(badge)

    def pulse_service_row(self, service_name: str, row: QFrame) -> None:
        row.setProperty("pulse", True)
        row.style().unpolish(row)
        row.style().polish(row)
        timer = self.service_pulse_timers.get(service_name)
        if timer is not None:
            timer.stop()
        timer = QTimer(self)
        timer.setSingleShot(True)
        timer.setInterval(320)
        timer.timeout.connect(lambda: self.clear_service_pulse(service_name, row))
        self.service_pulse_timers[service_name] = timer
        timer.start()

    def clear_service_pulse(self, service_name: str, row: QFrame) -> None:
        row.setProperty("pulse", False)
        row.style().unpolish(row)
        row.style().polish(row)
        timer = self.service_pulse_timers.pop(service_name, None)
        if timer is not None:
            timer.stop()

    def sync_services_scroller(self) -> None:
        count = max(len(self.service_widgets), 1)
        self.services_scroller.setMinimumHeight(
            count * SERVICE_ROW_HEIGHT + SERVICES_PADDING,
        )

    def progress_value(self, status: AppStatus) -> float:
        services = status.services
        if not services:
            return 0.0
        total = len(services)
        if self.current_action == "stop":
            stopped = sum(1 for item in services if item.state == "stopped")
            return stopped / total

        score = 0.0
        for item in services:
            state = item.state
            if state in {"healthy", "running"}:
                score += 1.0
            elif state == "starting":
                score += 0.5
            elif state not in {"stopped", "unknown"}:
                score += 0.25
        return score / total

    def animate_progress_to(self, target: float) -> None:
        self.target_progress = max(0.0, min(1.0, target))
        if self.progress_anim_timer is not None:
            self.progress_anim_timer.stop()

        def tick() -> None:
            current = self.progress_bar.fraction
            if abs(current - self.target_progress) < PROGRESS_SNAP:
                self.progress_bar.fraction = self.target_progress
                self.activity_percent.setText(f"{int(self.target_progress * 100)}%")
                if self.progress_anim_timer is not None:
                    self.progress_anim_timer.stop()
                return
            next_value = current + (self.target_progress - current) * PROGRESS_BLEND
            self.progress_bar.fraction = next_value
            self.activity_percent.setText(f"{int(next_value * 100)}%")

        self.progress_anim_timer = QTimer(self)
        self.progress_anim_timer.setInterval(16)
        self.progress_anim_timer.timeout.connect(tick)
        self.progress_anim_timer.start()

    def aggregate_stop_text(self) -> str:
        total = len(self.service_widgets)
        if total == 0:
            return tr("activity.stopping_services")
        stopped = sum(
            1 for item in self.service_widgets.values() if item.state == "stopped"
        )
        return tr("activity.stopped_count", stopped=stopped, total=total)

    def aggregate_start_text(self) -> str:
        total = len(self.service_widgets)
        if total == 0:
            return tr("activity.starting_services")
        ready = sum(
            1
            for item in self.service_widgets.values()
            if item.state in {"healthy", "running"}
        )
        return tr("activity.ready_count", ready=ready, total=total)

    def activity_detail_text(self) -> str:
        if self.current_action == "stop":
            return self.aggregate_stop_text()
        return self.aggregate_start_text()

    def activity_elapsed_text(self, elapsed: int) -> str:
        if self.last_step_text:
            return tr(
                "activity.elapsed_step",
                step=self.last_step_text,
                elapsed=elapsed,
            )
        return tr("activity.elapsed", elapsed=elapsed)

    def update_loading_labels(self) -> None:
        if self.action_started_at is None:
            return
        elapsed = int(time.monotonic() - self.action_started_at)
        self.activity_title.setText(
            truncate_text(self.activity_heading, MAX_ACTIVITY_TEXT),
        )
        self.activity_detail.setText(
            truncate_text(self.activity_detail_text(), MAX_ACTIVITY_TEXT),
        )
        self.activity_elapsed.setText(
            truncate_text(self.activity_elapsed_text(elapsed), MAX_ELAPSED_TEXT),
        )
        self.set_status_text_animated(self.header_action_status(), running=True)
        self.animate_progress_to(self.last_progress)

    def show_activity(self, title: str) -> None:
        self.update_buttons()
        self.activity_heading = title
        self.action_started_at = time.monotonic()
        self.last_progress = 0.0
        self.target_progress = 0.0
        self.last_step_text = ""
        self.activity_title.setText(truncate_text(title, MAX_ACTIVITY_TEXT))
        if self.current_action == "stop":
            self.activity_detail.setText(tr("activity.prep_stop"))
        else:
            self.activity_detail.setText(tr("activity.prep_start"))
        self.activity_elapsed.setText(tr("activity.elapsed", elapsed=0))
        self.activity_percent.setText("0%")
        self.progress_bar.fraction = 0.0
        self.activity_revealer.reveal()
        self.action_spinner.start()
        self.set_status_text_animated(self.header_action_status(), running=True)
        self.expand_for_activity()
        self.start_action_status_poll()

        if self.loading_tick_timer is not None:
            self.loading_tick_timer.stop()
        self.loading_tick_timer = QTimer(self)
        self.loading_tick_timer.setInterval(500)
        self.loading_tick_timer.timeout.connect(self.update_loading_labels)
        self.loading_tick_timer.start()

    def hide_activity(self) -> None:
        if self.loading_tick_timer is not None:
            self.loading_tick_timer.stop()
            self.loading_tick_timer = None
        self.stop_action_status_poll()
        self.action_started_at = None
        self.current_action = None
        self.activity_revealer.hide_reveal()
        self.action_spinner.stop()
        self.services_scroller.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        self.sync_services_scroller()
        self.animate_window_height(WINDOW_HEIGHT)

    def collapse_activity_panel(self) -> None:
        if self.activity_revealer._animation is not None:
            self.activity_revealer._animation.stop()
        self.activity_revealer._revealed = False
        self.activity_revealer.setMaximumHeight(0)
        self.action_spinner.stop()
        self.setFixedSize(WINDOW_WIDTH, WINDOW_HEIGHT)

    def expanded_window_height(self) -> int:
        return (
            WINDOW_HEIGHT
            + self.activity_revealer.content_height()
            + SHELL_GAP
            + SERVICE_ROW_HEIGHT
        )

    def expand_for_activity(self) -> None:
        self.services_scroller.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.sync_services_scroller()
        self.animate_window_height(self.expanded_window_height())

    def animate_window_height(self, target: int) -> None:
        if self.resize_anim is not None:
            self.resize_anim.stop()
        self.resize_anim = QVariantAnimation(self)
        self.resize_anim.setStartValue(self.height())
        self.resize_anim.setEndValue(target)
        self.resize_anim.setDuration(280)
        self.resize_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.resize_anim.valueChanged.connect(
            lambda value: self.setFixedSize(WINDOW_WIDTH, int(value))
        )
        self.resize_anim.start()

    def start_action_status_poll(self) -> None:
        self.stop_action_status_poll()
        self.refresh_status()
        self.action_status_timer = QTimer(self)
        self.action_status_timer.setInterval(2000)
        self.action_status_timer.timeout.connect(self.refresh_status)
        self.action_status_timer.start()

    def stop_action_status_poll(self) -> None:
        if self.action_status_timer is not None:
            self.action_status_timer.stop()
            self.action_status_timer = None

    def update_buttons(self) -> None:
        actions_enabled = self.started and not self.busy
        running = self.current_mode != "stopped"
        self.toggle_btn.setEnabled(actions_enabled)
        self.open_btn.setEnabled(actions_enabled and running and self.web_ready)
        self.lang_en_btn.setEnabled(not self.busy)
        self.lang_ru_btn.setEnabled(not self.busy)

    def pulse_button(self, button: QPushButton) -> None:
        button.setProperty("pulse", True)
        button.style().unpolish(button)
        button.style().polish(button)
        QTimer.singleShot(180, lambda: self.clear_button_pulse(button))

    def clear_button_pulse(self, button: QPushButton) -> None:
        button.setProperty("pulse", False)
        button.style().unpolish(button)
        button.style().polish(button)

    def on_toggle(self) -> None:
        if self.busy or not self.started:
            return
        self.set_busy(True)
        self.pulse_button(self.toggle_btn)
        if self.current_mode == "stopped":
            self.run_action("start", tr("status.starting"))
            return
        self.run_action("stop", tr("status.stopping"))

    def on_open(self) -> None:
        if self.busy or not self.started:
            return
        self.set_busy(True)
        self.pulse_button(self.open_btn)

        def task(_progress: Callable[[str], None]) -> None:
            open_in_browser(self.repo_root)

        self.run_worker(
            task,
            finished=lambda _: self.on_open_done(),
            failed=self.on_open_error,
        )

    def on_open_done(self) -> None:
        if not self._closing:
            self.set_busy(False)

    def on_open_error(self, message: str) -> None:
        if self._closing:
            return
        self.set_busy(False)
        QMessageBox.critical(self, tr("msg.browser_failed"), message)

    def set_busy(self, busy: bool) -> None:
        self.busy = busy
        self.update_buttons()

    def run_action(self, action: str, title: str) -> None:
        if not self.busy:
            self.set_busy(True)
        self.current_action = action
        self.show_activity(title)

        def task(progress: Callable[[str], None]) -> int:
            if action == "stop":
                stop_stack(self.repo_root, progress)
                return 0
            start_stack(self.repo_root, progress)
            return 0

        self.run_worker(
            task,
            finished=lambda _: self.on_action_success(),
            failed=self.on_action_error,
            progress=self.on_action_progress,
        )

    def on_action_progress(self, text: str) -> None:
        if self._closing:
            return
        if text:
            self.last_step_text = text
        self.update_loading_labels()

    def on_action_success(self) -> None:
        if self._closing:
            return
        self.last_step_text = (
            tr("activity.all_ready")
            if self.current_action == "start"
            else tr("activity.all_stopped")
        )
        self.last_progress = 1.0
        self.update_loading_labels()
        if self.finish_action_timer is not None:
            self.finish_action_timer.stop()
        self.finish_action_timer = QTimer(self)
        self.finish_action_timer.setSingleShot(True)
        self.finish_action_timer.setInterval(1800)
        self.finish_action_timer.timeout.connect(self.finish_action_ok)
        self.finish_action_timer.start()

    def on_action_error(self, message: str) -> None:
        failed_action = self.current_action
        self.hide_activity()
        self.set_busy(False)
        if failed_action == "start":
            self.apply_status(stopped_status(self.repo_root))
        QMessageBox.critical(self, tr("msg.action_failed"), message)
        self.refresh_status()

    def finish_action_ok(self) -> None:
        self.hide_activity()
        self.set_busy(False)
        self.refresh_status()
