# v1.5.11 Release Notes / リリースノート

Release date: 2026-03-26

## Summary / 概要

v1.5.11 focuses on non-developer environment stability, especially for ComfyUI Portable style usage.

v1.5.11 は、ComfyUI Portable 運用に合わせた非開発環境での安定性強化を目的としたリリースです。

## Included in v1.5.11 / 反映内容

- Launcher scripts now prioritize bundled Python (`python_embeded\python.exe`) and fall back to system Python only when needed.
- Added Anima2 workflow templates to minimal distribution workflows.
- Standardized bundled workflow set to four files:
  - `image_anima_preview.json`
  - `image_anima_preview_Lora4.json`
  - `image_anima2_preview.json`
  - `image_anima2_preview_Lora4.json`
- Updated visible version labels to `v1.5.11` in app and docs.

## Compatibility / 互換性

- Existing settings and presets remain compatible.
- Node IDs for bundled Anima1/Anima2 templates stay aligned with default values (`11`, `12`, `19`) in this release.
