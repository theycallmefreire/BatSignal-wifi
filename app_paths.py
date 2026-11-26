"""Stable resource and data paths for source and frozen Windows builds."""

import os
import sys
from pathlib import Path


def resource_path(name: str) -> Path:
    return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent)) / name


def data_directory() -> Path:
    override = os.environ.get("BATSIGNAL_DATA_DIR")
    if override:
        return Path(override).expanduser().resolve()
    if getattr(sys, "frozen", False):
        return Path(os.environ.get("LOCALAPPDATA", Path.home())) / "BatSignal" / "dados"
    return Path(__file__).resolve().parent / "dados"
