from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import Property, QEasingCurve, QPropertyAnimation, Qt, QTimer
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QProgressBar,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from .constants import ACTIVITY_HEIGHT_FALLBACK


def truncate_text(text: str, max_len: int) -> str:
    compact = " ".join(str(text).split())
    if len(compact) <= max_len:
        return compact
    return compact[: max_len - 1] + "…"


def clipped_label(text: str = "", *, max_chars: int = 40) -> QLabel:
    label = QLabel(truncate_text(text, max_chars))
    label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
    return label


class SpinnerWidget(QWidget):
    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        color: str = "#5b6ee8",
        size: int = 40,
    ) -> None:
        super().__init__(parent)
        self._angle = 0
        self._running = False
        self._color = QColor(color)
        self._timer = QTimer(self)
        self._timer.setInterval(16)
        self._timer.timeout.connect(self._tick)
        self.setFixedSize(size, size)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._timer.start()
        self.update()

    def stop(self) -> None:
        self._running = False
        self._timer.stop()
        self.update()

    def _tick(self) -> None:
        self._angle = (self._angle + 12) % 360
        self.update()

    def paintEvent(self, _event) -> None:
        if not self._running:
            return
        side = min(self.width(), self.height())
        if side <= 0:
            return

        painter = QPainter(self)
        if not painter.isActive():
            return

        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen_width = max(2, side // 8)
        margin = pen_width / 2 + 1
        rect = self.rect().adjusted(
            int(margin),
            int(margin),
            -int(margin),
            -int(margin),
        )

        round_cap = Qt.PenCapStyle.RoundCap
        track = QPen(
            QColor("#d8dcf0"),
            pen_width,
            Qt.PenStyle.SolidLine,
            round_cap,
        )
        painter.setPen(track)
        painter.drawArc(rect, 0, 360 * 16)

        arc = QPen(self._color, pen_width, Qt.PenStyle.SolidLine, round_cap)
        painter.setPen(arc)
        painter.drawArc(rect, -self._angle * 16, 90 * 16)
        painter.end()


class AnimatedProgressBar(QProgressBar):
    def __init__(self) -> None:
        super().__init__()
        self._fraction = 0.0

    def get_fraction(self) -> float:
        return self._fraction

    def set_fraction(self, value: float) -> None:
        self._fraction = max(0.0, min(1.0, value))
        self.setValue(int(self._fraction * 100))

    fraction = Property(float, get_fraction, set_fraction)


@dataclass(slots=True)
class ServiceWidgets:
    row: QFrame
    badge: QLabel
    state: str


class ActivityRevealer(QWidget):
    def __init__(self, content: QWidget, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._content = content
        self._revealed = False
        self._animation: QPropertyAnimation | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(content)

        self.setMaximumHeight(0)
        content.setVisible(True)

    def is_revealed(self) -> bool:
        return self._revealed

    def reveal(self, *, duration: int = 240) -> None:
        self._revealed = True
        target = max(self._content.sizeHint().height(), ACTIVITY_HEIGHT_FALLBACK)
        self._animate_height(target, duration)

    def hide_reveal(self, *, duration: int = 240) -> None:
        self._revealed = False
        self._animate_height(0, duration)

    def content_height(self) -> int:
        if self.height() > 0:
            return self.height()
        return max(self._content.sizeHint().height(), ACTIVITY_HEIGHT_FALLBACK)

    def _animate_height(self, target: int, duration: int) -> None:
        if self._animation is not None:
            self._animation.stop()
        if duration <= 0:
            self.setMaximumHeight(target)
            return
        self._animation = QPropertyAnimation(self, b"maximumHeight", self)
        self._animation.setDuration(duration)
        self._animation.setStartValue(self.maximumHeight())
        self._animation.setEndValue(target)
        self._animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._animation.start()
