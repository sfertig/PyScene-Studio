# PyScene Studio

PyScene Studio is a visual editor for creating 2D games with
[PyScene](https://github.com/sfertig/PyScene). Create projects, arrange scenes
and objects, import assets, and switch to script mode when you want to edit
scene code directly.

## Requirements

- Python 3.12 or newer
- `pip`
- PyScene and Pygame Community Edition

Install the runtime packages:

```bash
python -m pip install PyScene pygame-ce
```

To use the export options, install the corresponding build tools:

```bash
python -m pip install pyinstaller pygbag
```

## Start the editor

Clone or download this repository, open a terminal in its root folder, then run:

```bash
python main.py
```

The project manager lets you create a project or open one already in your
PyScene Studio projects directory. Project files are stored in
`~/.pyscene_studio_projects` (on Windows, in your user home directory).

## Create and run a game

1. Choose **+ Create** in the project manager and enter a project name.
2. Open the project and create or select a scene in **Tab Manager**.
3. Use **+ Add Obj** to add PyScene objects or your own custom objects to the
   scene. Select an object to edit its properties.
4. Arrange objects in **Visual Mode**. Use **Move** or **Scale** to choose a
   tool. Move and scale snap to the grid by default; toggle snapping and grid
   visibility in the viewport toolbar. Choose a grid size from the **Grid**
   dropdown. Drag empty space to pan, scroll to zoom, and press **F** to center
   the game view. Switch to **Script Mode** to edit scene functions directly.
5. Add source files and asset definitions in the **Assets** tab.
6. Press **F5** to build and run the project, or **F6** to build without
   launching it.
7. In **Settings**, choose a window background color or export a Windows or
   web build.

The editor saves project changes as you work. You can also save manually with
**F1** or **Ctrl+S**.

## Export

The **Settings** tab includes a background color picker and export controls.
Exports are copied to a uniquely named folder in your Downloads directory;
temporary build files are removed when the export finishes.

- **Windows** — builds a one-file `.exe` with PyInstaller. Windows exports
  must be built on Windows. The **Use --windowed** checkbox controls whether
  the executable hides its console window.
- **Web** — generates an asyncio-based entry point and builds it with pygbag.
  The resulting web files can be hosted as a static site; use a web server
  rather than opening the page directly from the filesystem.

Install PyInstaller, pygbag, and the project's runtime dependencies into the
same Python environment used to launch the editor.

## Assets

The **Assets** tab imports image, sound, and font files into the project. It
also lets you define named assets that scenes can use:

- **Image** — an image with optional scale and crop settings.
- **Animation** — a horizontal sprite sheet with a frame size, frame rate, and
  loop setting.
- **Tilemap** — a tileset sliced using the configured tile width and height.
- **Font** — a font file and point size.
- **Sound** — a sound file.

In a scene, the PyScene **Image**, **Text**, **Animation**, and **Tilemap**
objects have asset-aware properties. Choose an image for an Image or Animation,
a font for Text, and a tileset for a Tilemap. Tilemap layouts are saved in the
project and reused when the game runs.

Imported files and the asset manifest are stored under
`_python/assets/`. The build step generates the asset loader and scene Python
files in `_python/`.

## Editor shortcuts

| Shortcut | Action |
| --- | --- |
| **F1** or **Ctrl+S** | Save |
| **Ctrl+A** | Add an object to the current scene |
| **F5** | Build and run the project |
| **F6** or **Ctrl+B** | Build the project |
| **W / R** (Visual Mode) | Move / Scale tool |
| **G / H** (Visual Mode) | Toggle grid snapping / grid visibility |
| **[ / ]** (Visual Mode) | Decrease / increase grid size |
| **F** (Visual Mode) | Center the game view |

Buttons in the editor provide alternatives to the shortcuts where available.

## Project layout

```text
MyGame/
├── project.json          # Window and project settings
├── scenes/               # Scene data edited by the studio
├── objects/              # Custom object definitions
└── _python/
    ├── assets/           # Imported files and asset manifest
    ├── data/             # Generated scene and object Python modules
    ├── .pyscene/
    │   └── tilemaps/     # Saved tilemap layouts
    └── main.py           # Generated game entry point
```

Generated files under `_python/` are maintained by the build process. Use the
editor's scene and object tools rather than relying on manual edits to
generated files.

## PyScene

PyScene Studio builds on the [PyScene Python package](https://github.com/sfertig/PyScene).
Refer to its repository for engine APIs and examples.
