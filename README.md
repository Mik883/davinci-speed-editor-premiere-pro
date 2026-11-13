# DaVinci Speed Editor for Adobe Premiere Pro

Unofficial Windows integration that turns the Blackmagic Design DaVinci Resolve
Speed Editor into a native Adobe Premiere Pro control surface. It supports both
USB-C and Bluetooth HID connections, a Resolve-like jog/shuttle/scroll wheel and
a UXP configuration panel inside Premiere.

> This project is independent and is not affiliated with or endorsed by
> Blackmagic Design or Adobe.

## Features

- Native Premiere Pro Control Surface plug-in for Premiere Pro 2025, 2026 and 2027.
- USB-C and Bluetooth support with automatic reconnect.
- Relative, frame-accurate Jog without end stops or runaway acceleration.
- Shuttle and high-speed Scroll modes.
- In-Premiere UXP panel to adjust Jog speed.
- Per-button mapping for single and double presses.
- Each press can invoke a native Premiere command, a Premiere keyboard shortcut,
  or be disabled.
- Resolve-style Source and Timeline focus buttons.
- Split mapped to Add Edit/Cut; configurable In/Out and Trim In/Trim Out behavior.
- Background companion starts automatically when the surface is enabled.
- User mappings are reloaded live and preserved across updates.

## Installation

1. Download the current Windows package from Releases.
2. Close Premiere Pro and DaVinci Resolve.
3. Connect or pair the Speed Editor, then run `Install-SpeedEditor.cmd`.
4. In Premiere open **Edit > Preferences > Control Surface > Add** and choose
   **DaVinci Speed Editor**.
5. Open **Window > UXP Plugins > Speed Editor** for Jog speed and button mapping.

See `README-INSTALLAZIONE.txt` in the Windows package for Italian instructions.
The exhaustive option and behavior list is in [FEATURES.md](FEATURES.md).

## Architecture

The project consists of three parts:

1. A HID companion that authenticates the Speed Editor and normalizes its input.
2. A native Premiere Control Surface binary that receives events through a local
   named pipe and calls Premiere transport/command APIs.
3. A UXP panel that edits the live JSON configuration in `%LOCALAPPDATA%`.

The Adobe Premiere Pro SDK itself and Adobe-confidential sample source are not
included in this repository. The distributable Control Surface binary is built
against the SDK; rebuilding that component requires obtaining the SDK from Adobe.

## Similar and related projects

- [jameslost/Speed-Editor-BMD-vs-Premiere-Pro](https://github.com/jameslost/Speed-Editor-BMD-vs-Premiere-Pro)
  is an older request/proof-of-interest repository without an implementation.
- [BaukeWestendorp/bmdse](https://github.com/BaukeWestendorp/bmdse) is a Rust HID
  library for the Speed Editor.
- [smunaut/blackmagic-misc](https://github.com/smunaut/blackmagic-misc) documents
  the Blackmagic HID challenge-response used by this project under Apache-2.0.
- [JamesBalazs/speed-editor-client](https://github.com/JamesBalazs/speed-editor-client)
  is another community Speed Editor client.

## Compatibility

- Windows 10/11 x64
- Adobe Premiere Pro 2025-2027
- Blackmagic Design DaVinci Resolve Speed Editor over USB-C or Bluetooth

Only one application can own the HID device at a time, so DaVinci Resolve must
be closed while using the controller in Premiere.

## License

Original project code is licensed under the [Apache License 2.0](LICENSE).
The native Control Surface binary built against the Adobe Premiere Pro SDK is
excluded from that license and remains subject to the applicable Adobe terms.
Third-party attributions are documented in `NOTICE` and `THIRD_PARTY_NOTICES.md`.

## Security and privacy

The companion communicates only with the local Premiere plug-in through a Windows
named pipe. It does not send controller data or project information over the network.
