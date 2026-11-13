# Complete feature reference

## Connections and runtime

- USB-C and Windows Bluetooth HID use the same bridge and mappings.
- The bridge authenticates the controller, renews the session when needed and
  reconnects automatically after sleep or a temporary disconnect.
- A single-instance guard prevents two background bridges from competing for the device.
- DaVinci Resolve must be closed because the HID interface is exclusive.
- Input is sent to Premiere through a local named pipe; no cloud service is used.

## Jog wheel

| Mode | Behavior |
|---|---|
| Jog | Relative, continuous, frame-accurate movement without an artificial end stop. Speed is adjustable from `0.05×` to `3.00×`. |
| Shuttle | Direction and playback speed follow the wheel position around its center point. |
| Scroll | High-gear native navigation for covering longer timeline distances. |

The bridge normalizes the Speed Editor encoder values before sending them to
Premiere. This avoids the large jumps and one-direction lockup that occur when
raw HID values are treated as ordinary mouse-wheel ticks.

## Button mapping

Every physical button listed below has two independent assignments: **single
press** and **double press**. Each assignment can be set to:

- **Premiere command** — uses the native Control Surface API and does not depend
  on the active keyboard-layout preset.
- **Keyboard shortcut** — sends a user-entered Premiere shortcut such as `ctrl+k`.
  Comma-separated values create sequences, for example `end, comma`.
- **Disabled** — ignores that press without delaying the single-press action.

Supported buttons:

`Smart Insert`, `Append`, `Ripple Overwrite`, `Close Up`, `Place on Top`,
`Source Overwrite`, `In`, `Out`, `Trim In`, `Trim Out`, `Roll`, `Slip Source`,
`Slip Destination`, `Transition Duration`, `Cut`, `Dissolve`, `Smooth Cut`,
`Source`, `Timeline`, `Sync Bin`, `Transition`, `Video Only`, `Audio Only`,
`Ripple Delete`, `Audio Level`, `Full View`, `Snap`, `Split`, `Live Overwrite`,
`Esc`, `Camera 1-9`, and `Stop/Play`.

Native actions exposed by the panel include Smart Insert, Source Overwrite,
Set/Clear In, Set/Clear Out, Trim In/Out, Roll, Slide, Slip Source/Destination,
Cut/Add Edit, Source Monitor focus, Timeline focus, Transition, Video Only,
Audio Only, Ripple Delete, Audio Gain, Full View, Review, Snap, Play/Stop, Undo,
Marker, transition-duration setup, Camera 1-9 and Select Camera 1-9.

## Default Resolve-style behavior

- `Source` focuses the Source Monitor and `Timeline` focuses the open timeline.
- `Split` invokes Cut/Add Edit on the timeline.
- The In/Out and Trim In/Trim Out assignments use the requested swapped layout.
- Double-press `Esc` performs Undo.
- Camera buttons retain native multicamera actions and separate double-press
  camera-selection actions.
- Jog speed starts with the tuned profile from the tested Premiere integration.

## Configuration panel

The UXP panel is available from **Window > UXP Plugins > Speed Editor**. Changes
are written to `%LOCALAPPDATA%\SpeedEditorPremiere\premiere_mapping.json` and
reloaded live by the bridge. Updating the package preserves this user file.

## Installer and compatibility

- Installs the native surface into every detected Premiere Pro 2025-2027 folder.
- Installs the UXP panel through Adobe Unified Plugin Installer Agent (UPIA).
- Ships a standalone Windows executable; Python is not required by end users.
- Re-running the installer updates program files without overwriting mappings.
- The uninstaller removes only this project's files and preserves settings by default.
