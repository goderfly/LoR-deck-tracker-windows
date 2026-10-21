# Changelog

All notable changes to **Legends of Runeterra Deck Tracker** will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-10-21

### Added
- **Hearthstone Deck Tracker Architecture**:
  - Three distinct modular HUD surfaces: `PlayerPanel` (left edge), `OpponentPanel` (right edge), and `AdvisorBar` (top center).
  - Floating HDT-style card preview tooltip on hover with high-resolution artwork and remaining deck counts.
- **Riot Games DataDragon Russian Localization**:
  - Full Russian client localization covering 2,512 cards across Sets 1-9 and `set6cde`.
  - Localized keywords, spell speeds (Взрывное, Быстрое, Медленное), and rarity gems.
  - Official high-resolution SVG/PNG region crests for all 11 Runeterra factions.
- **Tactical Threat Advisor**:
  - Live opponent mana tracking including unit mana and spell-bank calculation.
  - Combat trick and board-wipe warning engine ranking lethal removal (Возмездие, Погибель, Отрицание, etc.).
- **Windows Integration & Taskbar Support**:
  - Custom Hextech Mana Crystal application icon (embedded `.ico` with sizes 16x16 to 256x256).
  - Windows Taskbar integration with `WS_EX_APPWINDOW` and custom process AppUserModelID.
  - Windows System Tray icon (`QSystemTrayIcon`) with live match status, quick settings, test mode, and graceful shutdown.
  - Native Windows crash reporting dialog and log handler.
- **Anti-Flicker State Machine**:
  - Permanent `CardID` tracking prevents cards from bouncing back into the remaining deck when played or destroyed.
  - 3-second debounce window absorbs mid-animation client redraw blanks.
- **Build Pipeline**:
  - 1-click Windows build script (`build.bat` and `scripts/build_exe.py`).
  - Self-contained standalone `.exe` output with embedded resources and Windows Version Resource metadata.

### Changed
- Reorganized codebase into a modular `lor` Python package (`manager`, `panels`, `advisor`, `preview`, `theme`, `widgets`, `win32ext`, `card_db`, `tracker_engine`, `advisor_engine`).
- Moved compiled binaries from root directory to dedicated `release/` and `dist/` folders.
- Relocated test suites to `tests/` and developer mocks to `tools/`.
- Archived legacy Tkinter and Flask prototypes to `legacy/`.

### Fixed
- Fixed unhandled `NameError: name 'BLOOD_DIM' is not defined` causing silent startup exit.
- Fixed `WS_EX_NOACTYLE` typo in `win32ext.py`.
- Fixed Russian spell detection in threat catalog where spells were classified as `"Заклинание"` rather than English `"Spell"`.
- Fixed 34-second startup hang caused by synchronous region icon downloads in `_index_globals()`.
