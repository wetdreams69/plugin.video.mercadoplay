# MercadoPlay Plugin for Kodi (`plugin.video.mercadoplay`)

[![Kodi version](https://img.shields.io/badge/kodi%20versions-19+-blue)](https://kodi.tv/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## Disclaimer

This plugin is **not officially commissioned or endorsed by Mercado Libre S.A.**  
"Mercado Libre", "MercadoPlay" and associated logos are trademarks of their respective owners.

**Important**

- **This addon does not promote or support piracy.**
- This addon simply provides an alternative way to access publicly available content from [MercadoPlay](https://play.mercadolibre.com.ar).

**ONLY WORKS WITH KODI 19 (Matrix) OR LATER**

---

## Supported Features

- **MPEG-DASH & SSAI Support**: Full support for Server-Side Ad Insertion (SSAI) streams.
- **Ad Skipping**: Integrated with `script.module.adskipper` to automatically detect and skip advertisement periods in DASH streams.
- **Dynamic Navigation**: Browse content by category (Movies, Series, Kids, etc.).
- **Metadata Extraction**: Improved extraction logic using robust HTML/JSON parsing.
- **Cache Management**: SQLite-based cache system for fast browsing.
- **DRM Support**: Widevine L3 support for protected content (forced 480p for maximum compatibility).

---

## Configuration

### AdSkipper
You can enable or disable automatic ad skipping in the addon settings. When enabled, the addon will monitor the playback and perform a `seek` to jump past detected ad slots in the MPEG-DASH manifest.

---

## Changelog

### v1.4.0
- **New Feature**: Integration with `script.module.adskipper` for automatic ad skipping.
- **New Feature**: Added setting flag to enable/disable AdSkipper.
- **Fix**: Improved MPEG-DASH handshake for SSAI streams.
- **Fix**: Enhanced resolution filtering to stabilize playback on various devices.
- **Refactor**: Cleaned up internal logic to follow SOLID principles.

### v1.3.0
- Initial stable release with full metadata extraction and Widevine support.

---

## Installation

### From ZIP file

1. Download the `.zip` file from the repository.
2. Open Kodi and navigate to `Add-ons` > `Install from zip file`.
3. Select the downloaded file.
4. Access the plugin from the `Video Add-ons` section.

### Requirements

- Kodi 19 or later
- `inputstream.adaptive` (enabled)
- `script.module.adskipper` (dependency)

---

## Regional Limitation

This plugin is configured by default for **Argentina**. To use it in other countries where MercadoPlay is available, you may need to update the `BASE_URL` and `API_URL` in `constants.py`.

---

## Credits

Developed by: `wetdreams69`
