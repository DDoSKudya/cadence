from __future__ import annotations

import platform
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

APP_NAME = "CadenceLauncher"


def platform_tag(system: str) -> str:
    if system == "Windows":
        return "windows"
    if system == "Darwin":
        return "macos"
    return "linux"


def data_separator(system: str) -> str:
    return ";" if system == "Windows" else ":"


def resolve_icon(project_root: Path, system: str) -> Path | None:
    assets_dir = project_root / "src" / "cadence_launcher" / "assets"
    icon_candidates = {
        "Windows": [assets_dir / "cadence.ico"],
        "Darwin": [assets_dir / "cadence.icns", assets_dir / "cadence.png"],
        "Linux": [assets_dir / "cadence.png", assets_dir / "cadence.svg"],
    }
    for candidate in icon_candidates.get(system, []):
        if candidate.exists():
            return candidate
    return None


def bundle_path(dist_dir: Path, system: str) -> Path:
    if system == "Darwin":
        return dist_dir / f"{APP_NAME}.app"
    if system == "Windows":
        return dist_dir / f"{APP_NAME}.exe"
    return dist_dir / APP_NAME


def archive_bundle(bundle: Path, archive_base: Path) -> Path:
    archive_base.parent.mkdir(parents=True, exist_ok=True)
    if bundle.is_dir():
        archive_path = shutil.make_archive(
            str(archive_base),
            "zip",
            root_dir=bundle.parent,
            base_dir=bundle.name,
        )
        return Path(archive_path)

    with tempfile.TemporaryDirectory() as temp_dir:
        staging_dir = Path(temp_dir) / bundle.stem
        staging_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(bundle, staging_dir / bundle.name)
        archive_path = shutil.make_archive(
            str(archive_base),
            "zip",
            root_dir=staging_dir.parent,
            base_dir=staging_dir.name,
        )
    return Path(archive_path)


def build_command(
    project_root: Path,
    dist_dir: Path,
    build_dir: Path,
    spec_dir: Path,
) -> list[str]:
    system = platform.system()
    entrypoint = project_root / "src" / "cadence_launcher" / "__main__.py"
    assets_dir = project_root / "src" / "cadence_launcher" / "assets"
    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--windowed",
        "--name",
        APP_NAME,
        "--distpath",
        str(dist_dir),
        "--workpath",
        str(build_dir),
        "--specpath",
        str(spec_dir),
        "--paths",
        str(project_root / "src"),
        "--hidden-import",
        "PySide6.QtSvgWidgets",
        "--hidden-import",
        "cadence_launcher.ui.window",
        "--hidden-import",
        "cadence_launcher.ui.widgets",
        "--hidden-import",
        "cadence_launcher.ui.styles",
        "--hidden-import",
        "cadence_launcher.workers",
        "--hidden-import",
        "cadence_launcher.friendly_action",
        "--hidden-import",
        "cadence_launcher.i18n",
        "--hidden-import",
        "cadence_launcher.runtime",
        "--add-data",
        f"{assets_dir}{data_separator(system)}cadence_launcher/assets",
        str(entrypoint),
    ]
    icon = resolve_icon(project_root, system)
    if icon is not None:
        command.extend(["--icon", str(icon)])
    return command


def main() -> int:
    project_root = Path(__file__).resolve().parents[1]
    dist_dir = project_root / "dist"
    build_dir = project_root / "build"
    spec_dir = project_root / "pyinstaller"
    spec_dir.mkdir(parents=True, exist_ok=True)

    for target in (dist_dir, build_dir):
        if target.exists():
            shutil.rmtree(target)

    command = build_command(project_root, dist_dir, build_dir, spec_dir)
    result = subprocess.run(command, cwd=project_root, check=False)  # noqa: S603
    if result.returncode != 0:
        return result.returncode

    system = platform.system()
    bundle = bundle_path(dist_dir, system)
    if not bundle.exists():
        raise SystemExit(f"Expected bundle was not created: {bundle}")

    archive_name = f"{APP_NAME}-{platform_tag(system)}"
    archive = archive_bundle(bundle, dist_dir / archive_name)
    print(f"Built archive: {archive}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
