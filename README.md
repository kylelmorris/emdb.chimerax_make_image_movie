# ChimeraX Auto-Rendering Utility

A command-line tool for generating publication-quality movies and images from cryo-EM density maps using UCSF ChimeraX. This script supports automatic contour selection, map colouring, background control, transparent rendering, command logging, and session export.

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
- Colour themes: `kelly`, `blue`, `emdb`
- Backgrounds including Bluesky dark mode (`#161f28`)
- Optional transparent PNG rendering
- Optional ChimeraX session `.cxs` export

---

## 📁 Output Files

Given an output base name `OUTBASE`, the script creates:

- `OUTBASE_chimerax_movie.mov`
- `OUTBASE_chimerax_movie_script.cxc`
- `OUTBASE_chimerax_image.png`
- `OUTBASE_chimerax_image_script.cxc`
- `OUTBASE_chimerax_movie_session.cxs` *(optional)*
- `OUTBASE_chimerax_image_session.cxs` *(optional)*
- `OUTBASE_command.txt` (records the exact command used)

---

## 🚀 Example Usage

### Basic movie + image
```
python emdb.chimerax_make_image_movie.py --mrc map.mrc --format both
```

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

### Write scripts only (no ChimeraX execution) for spin movie
```
python emdb.chimerax_make_image_movie.py --mrc map.mrc --format movie --script-only
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
- All outputs are placed in `--outdir` or beside the MRC file by default.

---

## 📄 License

MIT License.

---

## 👤 Author

Kyle Morris, EMBL‑EBI
