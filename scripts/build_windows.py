"""Build a portable Windows folder and ZIP using the current virtual environment."""

import shutil
import subprocess
import sys
from importlib.metadata import distribution
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def collect_notices():
    target = ROOT / "build" / "THIRD_PARTY_NOTICES.txt"
    target.parent.mkdir(parents=True, exist_ok=True)
    chunks = ["Third-party software notices for the BatSignal Windows distribution.\n"]
    packages = (
        "matplotlib",
        "numpy",
        "Pillow",
        "openpyxl",
        "contourpy",
        "cycler",
        "fonttools",
        "kiwisolver",
        "packaging",
        "pyparsing",
        "python-dateutil",
        "tzdata",
        "et-xmlfile",
    )
    for name in packages:
        package = distribution(name)
        chunks.append(f"\n{'=' * 72}\n{name} {package.version}\n")
        for item in package.files or []:
            if any(word in item.name.lower() for word in ("license", "copying", "notice")):
                path = Path(package.locate_file(item))
                if path.is_file() and path.suffix.lower() not in (".py", ".pyc", ".so", ".pyd"):
                    chunks.append(f"\n--- {item} ---\n")
                    chunks.append(path.read_text(encoding="utf-8", errors="replace"))
    python_license = Path(sys.base_prefix) / "LICENSE.txt"
    if python_license.exists():
        chunks.append("\nPython runtime license\n" + python_license.read_text(encoding="utf-8"))
    target.write_text("\n".join(chunks), encoding="utf-8")


def main():
    if sys.platform != "win32":
        raise SystemExit("Build the Windows executable on Windows.")
    collect_notices()
    subprocess.run(
        [sys.executable, "-m", "PyInstaller", "--noconfirm", str(ROOT / "BatSignal.spec")],
        cwd=ROOT,
        check=True,
    )
    folder = ROOT / "dist" / "BatSignal"
    for source in (
        ROOT / "LICENSE",
        ROOT / "NOTICE",
        ROOT / "README.md",
        ROOT / "CONTRIBUTING.md",
        ROOT / "ROADMAP.md",
        ROOT / "build" / "THIRD_PARTY_NOTICES.txt",
    ):
        shutil.copy2(source, folder / source.name)
    for name in ("imagens", "examples"):
        shutil.copytree(ROOT / name, folder / name, dirs_exist_ok=True)
    shutil.make_archive(
        str(ROOT / "dist" / "BatSignal-Windows"),
        "zip",
        root_dir=ROOT / "dist",
        base_dir="BatSignal",
    )
    print(ROOT / "dist" / "BatSignal-Windows.zip")


if __name__ == "__main__":
    main()
