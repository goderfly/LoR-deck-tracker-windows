"""
Automated Build Pipeline for Legends of Runeterra Deck Tracker.

Compiles the standalone Windows executable (.exe) with embedded assets,
Windows Version Resource metadata, and PyInstaller bundling into release/.
"""

import argparse
import os
import shutil
import subprocess
import sys
import zipfile

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT_DIR, "data")
RELEASE_DIR = os.path.join(ROOT_DIR, "release")
DIST_DIR = os.path.join(ROOT_DIR, "dist")
BUILD_DIR = os.path.join(ROOT_DIR, "build")
SCRIPTS_DIR = os.path.join(ROOT_DIR, "scripts")

VERSION_INFO_TEMPLATE = """# UTF-8
#
# Windows File Version Info for PyInstaller
#
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=(1, 0, 0, 0),
    prodvers=(1, 0, 0, 0),
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo(
      [
        StringTable(
          '040904B0',
          [
            StringStruct('CompanyName', 'LoR Deck Tracker Community'),
            StringStruct('FileDescription', 'Legends of Runeterra Deck Tracker Overlay'),
            StringStruct('FileVersion', '1.0.0.0'),
            StringStruct('InternalName', 'LoRDeckTracker'),
            StringStruct('LegalCopyright', 'Copyright (C) 2026 LoR Deck Tracker Contributors. All rights reserved.'),
            StringStruct('OriginalFilename', 'LoRDeckTracker.exe'),
            StringStruct('ProductName', 'Legends of Runeterra Deck Tracker'),
            StringStruct('ProductVersion', '1.0.0.0')
          ]
        )
      ]
    ),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
"""


def clean():
    """Remove previous build caches."""
    print("[*] Cleaning build artifacts...")
    for folder in [BUILD_DIR, DIST_DIR]:
        if os.path.exists(folder):
            try:
                shutil.rmtree(folder, ignore_errors=True)
            except Exception as e:
                print(f"    Warning cleaning {folder}: {e}")

    # Remove stale exe in root if present
    root_exe = os.path.join(ROOT_DIR, "LoRDeckTracker.exe")
    if os.path.exists(root_exe):
        try:
            os.remove(root_exe)
        except Exception:
            pass


def check_dependencies():
    """Validate required build tools."""
    print("[*] Checking build dependencies...")
    try:
        import PyInstaller
        print(f"    PyInstaller version: {PyInstaller.__version__}")
    except ImportError:
        print("[!] PyInstaller is not installed. Installing via pip...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])


def build(debug_console=False, make_zip=False):
    clean()
    check_dependencies()

    os.makedirs(RELEASE_DIR, exist_ok=True)
    os.makedirs(SCRIPTS_DIR, exist_ok=True)

    version_file = os.path.join(SCRIPTS_DIR, "file_version_info.txt")
    with open(version_file, "w", encoding="utf-8") as f:
        f.write(VERSION_INFO_TEMPLATE)

    icon_path = os.path.join(DATA_DIR, "icons", "app_icon.ico")
    if not os.path.exists(icon_path):
        raise FileNotFoundError(f"Missing application icon: {icon_path}")

    main_script = os.path.join(ROOT_DIR, "main.py")

    datas = [
        (os.path.join(DATA_DIR, "cards_cache_ru.json"), "data"),
        (os.path.join(DATA_DIR, "cards_cache_ru_ru.json"), "data"),
        (os.path.join(DATA_DIR, "globals_ru.json"), "data"),
        (os.path.join(DATA_DIR, "globals_ru_ru.json"), "data"),
        (os.path.join(DATA_DIR, "settings.json"), "data"),
        (os.path.join(DATA_DIR, "icons"), "data/icons"),
        (os.path.join(ROOT_DIR, "lor"), "lor"),
    ]

    datas_args = []
    for src, dst in datas:
        if os.path.exists(src):
            datas_args.extend(["--add-data", f"{src};{dst}"])

    hidden_imports = [
        "PyQt6",
        "PyQt6.QtCore",
        "PyQt6.QtGui",
        "PyQt6.QtWidgets",
        "requests",
        "urllib3",
        "win32service",
        "win32gui",
        "win32con",
        "win32process",
        "PIL",
        "lor",
        "lor.manager",
        "lor.panels",
        "lor.advisor",
        "lor.preview",
        "lor.settings",
        "lor.theme",
        "lor.widgets",
        "lor.win32ext",
        "lor.card_db",
        "lor.tracker_engine",
        "lor.advisor_engine",
    ]

    hidden_args = []
    for h in hidden_imports:
        hidden_args.extend(["--hidden-import", h])

    cmd = [
        sys.executable,
        "-m", "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onefile",
        "--name", "LoRDeckTracker",
        "--icon", icon_path,
        "--version-file", version_file,
    ]

    if not debug_console:
        cmd.append("--noconsole")

    cmd.extend(datas_args)
    cmd.extend(hidden_args)
    cmd.append(main_script)

    print("[*] Running PyInstaller command:")
    print("    " + " ".join(cmd[:10]) + " ...")

    subprocess.check_call(cmd, cwd=ROOT_DIR)

    dist_exe = os.path.join(DIST_DIR, "LoRDeckTracker.exe")
    if not os.path.exists(dist_exe):
        raise RuntimeError("Build failed: Output binary not found in dist/")

    dest_exe = os.path.join(RELEASE_DIR, "LoRDeckTracker.exe")
    shutil.copy2(dist_exe, dest_exe)

    size_mb = os.path.getsize(dest_exe) / (1024 * 1024)
    print(f"\n[+] BUILD SUCCESSFUL!")
    print(f"    Release executable: {dest_exe}")
    print(f"    Size: {size_mb:.2f} MB")

    if make_zip:
        zip_path = os.path.join(RELEASE_DIR, "LoRDeckTracker-v1.0.0-windows-x64.zip")
        print(f"[*] Packaging into {zip_path}...")
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.write(dest_exe, arcname="LoRDeckTracker.exe")
            for doc in ["README.md", "LICENSE", "CHANGELOG.md"]:
                doc_path = os.path.join(ROOT_DIR, doc)
                if os.path.exists(doc_path):
                    zf.write(doc_path, arcname=doc)
        print(f"[+] Zip package created: {zip_path}")


def main():
    parser = argparse.ArgumentParser(description="Build LoRDeckTracker.exe")
    parser.add_argument("--clean", action="store_true", help="Clean caches before build")
    parser.add_argument("--debug", action="store_true", help="Keep console window for debugging")
    parser.add_argument("--zip", action="store_true", help="Create release zip archive")
    args = parser.parse_args()

    build(debug_console=args.debug, make_zip=args.zip)


if __name__ == "__main__":
    main()
