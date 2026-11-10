import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

import PyScene

from .Build import Build
from .utils.files import get_save_dir_path


class ExportError(RuntimeError):
    pass


def _downloads_path() -> Path:
    downloads = Path.home() / "Downloads"
    downloads.mkdir(parents=True, exist_ok=True)
    return downloads


def _unique_export_path(project_name: str, target: str) -> Path:
    downloads = _downloads_path()
    base = downloads / f"{project_name}-{target}"
    candidate = base
    suffix = 2
    while candidate.exists():
        candidate = downloads / f"{base.name}-{suffix}"
        suffix += 1
    return candidate


def _copy_project(project_name: str, destination: Path) -> None:
    source = Path(get_save_dir_path()) / project_name
    if not source.is_dir():
        raise ExportError(f"Project folder was not found: {source}")

    python_folder = source / "_python"

    def ignore_transients(folder, names):
        ignored = {name for name in names if name in {".git", "__pycache__"}}
        if Path(folder) == python_folder:
            ignored.update(name for name in names if name in {"build", "dist"})
        return ignored

    shutil.copytree(source, destination, ignore=ignore_transients)


def _run_command(command: list[str], cwd: Path, tool_name: str) -> None:
    result = subprocess.run(
        command,
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode:
        details = (result.stderr or result.stdout).strip()
        if details:
            print(f"[Export] - {tool_name} failed:\n{details}")
        final_line = details.splitlines()[-1] if details else "No error details were returned."
        raise ExportError(f"{tool_name} failed: {final_line}")


def export_windows(project_name: str, windowed: bool) -> Path:
    if os.name != "nt":
        raise ExportError("Windows exports must be built on Windows.")
    if importlib.util.find_spec("PyInstaller") is None:
        raise ExportError(
            "PyInstaller is not installed. Install it with: python -m pip install pyinstaller"
        )

    final_path = _unique_export_path(project_name, "windows")
    with tempfile.TemporaryDirectory(
        prefix=f".{project_name}-windows-", dir=_downloads_path()
    ) as temporary_directory:
        copied_project = Path(temporary_directory) / project_name
        _copy_project(project_name, copied_project)
        Build(project_name, project_path=str(copied_project), is_export=True)

        python_folder = copied_project / "_python"
        command = [
            sys.executable,
            "-m",
            "PyInstaller",
            "--noconfirm",
            "--clean",
            "--onefile",
            "--name",
            project_name,
            "--distpath",
            str(Path(temporary_directory) / "dist"),
            "--workpath",
            str(Path(temporary_directory) / "build"),
            "--specpath",
            temporary_directory,
            "--add-data",
            f"{python_folder / 'assets'}{os.pathsep}assets",
        ]
        tilemaps_folder = python_folder / ".pyscene"
        if tilemaps_folder.is_dir():
            command.extend(
                ["--add-data", f"{tilemaps_folder}{os.pathsep}.pyscene"]
            )
        if windowed:
            command.append("--windowed")
        command.append(str(python_folder / "main.py"))
        _run_command(command, python_folder, "PyInstaller")

        built_executable = Path(temporary_directory) / "dist" / f"{project_name}.exe"
        if not built_executable.is_file():
            raise ExportError(
                f"PyInstaller did not create the expected executable: {built_executable}"
            )
        final_path.mkdir()
        shutil.copy2(built_executable, final_path / built_executable.name)

    return final_path


def export_web(project_name: str) -> Path:
    if importlib.util.find_spec("pygbag") is None:
        raise ExportError(
            "pygbag is not installed. Install it with: python -m pip install pygbag"
        )

    final_path = _unique_export_path(project_name, "web")
    with tempfile.TemporaryDirectory(
        prefix=f".{project_name}-web-", dir=_downloads_path()
    ) as temporary_directory:
        copied_project = Path(temporary_directory) / project_name
        _copy_project(project_name, copied_project)
        Build(
            project_name,
            project_path=str(copied_project),
            web=True,
            is_export=True,
        )

        python_folder = copied_project / "_python"
        engine_source = Path(PyScene.__file__).parent
        engine_destination = python_folder / "PyScene"
        if engine_destination.exists():
            raise ExportError(
                "The project's _python folder already contains a PyScene path; "
                "cannot bundle the engine for web export."
            )
        shutil.copytree(
            engine_source,
            engine_destination,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
        )

        _run_command(
            [
                sys.executable,
                "-m",
                "pygbag",
                "--build",
                "--title",
                project_name,
                str(python_folder),
            ],
            python_folder,
            "pygbag",
        )

        web_build = python_folder / "build" / "web"
        if not web_build.is_dir():
            raise ExportError(f"pygbag did not create the expected web build: {web_build}")
        shutil.copytree(web_build, final_path)

    return final_path
