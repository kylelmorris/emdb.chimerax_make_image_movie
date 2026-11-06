# ChimeraX Auto-Rendering Utility

A command-line tool for generating publication-quality movies and images from cryo-EM density maps using UCSF ChimeraX. This script supports automatic contour selection, map colouring, background control, transparent rendering, command logging, and ChimeraX scene scripts.

---

## 🔍 Features

### ✔ Automatic contour estimation  
Supported methods:

- `rmsd` — mean + k·σ  
- `p99` — 99th percentile  
- `hybrid` — min(RMSD contour, percentile contour)  
- `3sig`, `6sig`, `9sig` — sigma-based thresholds  
- `abs30` — 30% of max density  
- **`MIT` — Uses the external ChimeraX calc_level plugin:**  
  https://github.com/mariacarreira/calc_level_ChimeraX  
  This mode uses the ChimeraX command: 'volume calc_level #1`

---

## 🎨 Rendering Options

- Generate **image**, **movie**, or **both**
- Colour themes: `kelly`, `blue`, `emdb`, `rainbow`, `rainbowr`, `chain`
- Backgrounds including Bluesky dark mode (`#161f28`)
- Optional transparent PNG rendering
- Optional ChimeraX scene script export
- New colour gradients are defined once in `COLOUR_SPECS` inside the Python script and appear in `--help` automatically.

---

## 📁 Output Files

Given an output base name `OUTBASE`, the script creates:

- `OUTBASE_chimerax_movie.mov`
- `OUTBASE_chimerax_movie_script.cxc`
- `OUTBASE_chimerax_movie_session_script.cxc`
- `OUTBASE_chimerax_image.png`
- `OUTBASE_chimerax_image_script.cxc`
- `OUTBASE_chimerax_image_session_script.cxc`
- `OUTBASE_summary.txt` (records the exact command used and a summary of outputs)

---

## 🚀 Example Usage

### Basic movie + image
```
python emdb.chimerax_make_image_movie.py --mrc map.mrc --format both
```

### Headless production environment
Use the auto-headless entrypoint when running on servers, containers, or other environments without a display:
```
python emdb.chimerax_make_image_movie_auto_headless.py --mrc emd_XXXX.map --format movie --movie-format apng --quality web2
```
This mode detects a headless session and runs ChimeraX with offscreen rendering. The `web2` quality profile is tuned for lightweight production output, and this example writes an APNG movie asset.

### 3 sigma auto-contour mode and image
```
python emdb.chimerax_make_image_movie.py --mrc map.mrc --format image --auto_contour 3sig
```

### Custom output directory + prefix
```
python emdb.chimerax_make_image_movie.py --mrc map.mrc --outdir results/ --outname EMD-123456
```

### Transparent background image
```
python emdb.chimerax_make_image_movie.py --mrc map.mrc --transparent
```

### Camera orientation
```
python emdb.chimerax_make_image_movie.py --mrc map.mrc --turnxz 90,-30
```
The default is `--turnxz -90,0`. Both render and interactive CXC scripts use the specified X and Z turns.

### Corner label with EMD and PDB IDs
```
python emdb.chimerax_make_image_movie.py --mrc map.mrc --model model.pdb --label
```
This adds a bottom-right 2D label in the generated ChimeraX script. If no model is provided, the label falls back to the map EMD-ID only.

### Save a ChimeraX render script
```
python emdb.chimerax_make_image_movie.py --mrc map.mrc --format image --save-script
```
This renders the image and writes the render scene `*.cxc` script.

### Open ChimeraX interactively
```
python emdb.chimerax_make_image_movie.py --mrc map.mrc --format image --save-session
```
This writes a second `*.cxc` script that sets up the same scene but does not save the rendered image and does not exit.

### Disable either script
```
python emdb.chimerax_make_image_movie.py --mrc map.mrc --no-save-session
python emdb.chimerax_make_image_movie.py --mrc map.mrc --no-save-script
```

### Chain-specific colouring
```
python emdb.chimerax_make_image_movie.py --mrc map.mrc --model model.pdb --colour chain --chain-colours "all:green A:orange B:cyan C:lightblue D:purple"
```
In `chain` mode, `all:<colour>` sets the default model colour first, then any per-chain entries override specific chains before `color zone #1 near #2` is applied.

### Write scripts only (no ChimeraX execution) for spin movie
```
python emdb.chimerax_make_image_movie.py --mrc map.mrc --format movie --script-only
```

### Disable summary output
```
python emdb.chimerax_make_image_movie.py --mrc map.mrc --no-summary
```

---

## 📦 Requirements

- Python 3
- UCSF ChimeraX
- `numpy`
- `mrcfile`

MIT contour mode additionally requires:
https://github.com/mariacarreira/calc_level_ChimeraX
Credit: Davis lab - MIT

---

## 📝 Notes

- `.gz` input (map or model) is automatically decompressed.
- When `--script-only` is used, ChimeraX is not launched and only a script for running ChimeraX is produced.
- `--save-script` is enabled by default and writes the normal render scene `*.cxc`.
- `--save-session` is enabled by default and writes an additional interactive `*.cxc` without saving output or exiting.
- All outputs are placed in `--outdir` or beside the MRC file by default.
- Summary output is enabled by default; use `--no-summary` to skip writing `OUTBASE_summary.txt`.

---

## 📄 License

Apache license

---

## 👤 Author

Kyle Morris, EMBL‑EBI
GPT-5 assisted
