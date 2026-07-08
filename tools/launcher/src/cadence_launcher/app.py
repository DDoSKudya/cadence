from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox

from .i18n import init_locale, tr
from .runtime import LauncherError, discover_repo_root, load_config, select_repo_root
from .ui.styles import STYLE
from .ui.window import LauncherWindow


def apply_light_palette(app: QApplication) -> None:
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor("#e8ebf1"))
    palette.setColor(QPalette.ColorRole.WindowText, QColor("#161b26"))
    palette.setColor(QPalette.ColorRole.Base, QColor("#ffffff"))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor("#f4f6f9"))
    palette.setColor(QPalette.ColorRole.Text, QColor("#161b26"))
    palette.setColor(QPalette.ColorRole.Button, QColor("#ffffff"))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor("#161b26"))
    app.setPalette(palette)


def resolve_repo_root() -> Path | None:
    repo_root = discover_repo_root()
    if repo_root is not None:
        return repo_root

    QMessageBox.information(
        None,
        "Cadence Launcher",
        tr("msg.repo_not_found"),
    )
    selected = QFileDialog.getExistingDirectory(None, tr("dialog.select_repo"))
    if not selected:
        return None
    root = Path(selected).resolve()
    try:
        select_repo_root(root)
    except LauncherError as error:
        QMessageBox.critical(None, tr("msg.invalid_folder"), str(error))
        return None
    return root


def run() -> int:
    config = load_config()
    init_locale(config.language)
    app = QApplication(sys.argv)
    app.setApplicationName("Cadence Launcher (alpha)")
    app.setStyle("Fusion")
    apply_light_palette(app)
    app.setStyleSheet(STYLE)

    repo_root = resolve_repo_root()
    if repo_root is None:
        return 1

    window = LauncherWindow(repo_root)
    window.show()
    return app.exec()
