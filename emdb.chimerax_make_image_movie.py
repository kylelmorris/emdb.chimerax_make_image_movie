#!/Users/kyle/anaconda3/bin/python
#

import subprocess
import argparse
import shutil
import sys
import os
import gzip
import shlex
import math
import re
import numpy as np
import mrcfile


# =========================
# Auto-contour calculations
# =========================

def estimate_contour_rmsd(data, k=3.0):
    """Return RMSD-based contour level = mean + k * sigma."""
    mean = data.mean()
    rmsd = data.std()
    return mean + k * rmsd


def estimate_contour_percentile(data, p=99.0):
    """Return percentile-based contour level."""
    return np.percentile(data, p)


def estimate_contour_hybrid(data):
    """Hybrid auto contour = min(mean + 3·RMSD, 99th percentile)."""
    t_rmsd = estimate_contour_rmsd(data, k=3.0)
    t_p99 = estimate_contour_percentile(data, p=99.0)
    return min(t_rmsd, t_p99)


def estimate_contour_3sig(data):
    return 3.0 * data.std()

def estimate_contour_6sig(data):
    return 6.0 * data.std()

def estimate_contour_9sig(data):
    return 9.0 * data.std()

def estimate_contour_abs30(data):
    return 0.3 * data.max()


def compute_auto_contour(path, method):
    """Load MRC data and compute contour threshold."""
    if method == "MIT":
        return "MIT"

    with mrcfile.open(path) as m:
        data = m.data.astype(np.float32)

    if method == "rmsd":
        return estimate_contour_rmsd(data)
    elif method == "p99":
        return estimate_contour_percentile(data)
    elif method == "hybrid":
        return estimate_contour_hybrid(data)
    elif method == "3sig":
        return estimate_contour_3sig(data)
    elif method == "6sig":
        return estimate_contour_6sig(data)
    elif method == "9sig":
        return estimate_contour_9sig(data)
    elif method == "abs30":
        return estimate_contour_abs30(data)
    else:
        raise ValueError(f"Unknown auto contour method: {method}")


# ===========================================
# ChimeraX script writers
# ===========================================

COLOUR_SPECS = {
    # Map + model colour schemes
    "kelly": {
        "map_commands": [
            "volume #1 color cornflowerblue",
            "volume #1 transparency 0.1",
        ],
        "model_commands": [
            "color #2 royalblue target c",
        ],
    },
    "blue": {
        "map_commands": [
            "color radial #1 center #1 palette #045a8d:#2b8cbe:#74a9cf:#bdc9e1:#f1eef6",
            "volume #1 transparency 0.1",
        ],
        "model_commands": [
            "color #2 grey",
        ],
    },
    "emdb": {
        "map_commands": [
            "color radial #1 center #1 palette #AD2447:#EA3861:#38B249:#90CB8A:#CFE7CB",
            "volume #1 transparency 0.1",
        ],
        "model_commands": [
            "color #2 grey",
        ],
    },
    "rainbow": {
        "map_commands": [
            "color radial #1 center #1 palette #DC504D:#E37F4F:#EDEB7E:#71B86D:#5BB6E7:#4263AA",
            "volume #1 transparency 0.1",
        ],
        "model_commands": [
            "color #2 grey",
        ],
    },
    "rainbowr": {
        "map_commands": [
            "color radial #1 center #1 palette #4263AA:#5BB6E7:#71B86D:#EDEB7E:#E37F4F:#DC504D",
            "volume #1 transparency 0.1",
        ],
        "model_commands": [
            "color #2 grey",
        ],
    },
    "sunrise": {
        "map_commands": [
            "color radial #1 center #1 palette #ED8A35:#F5C573:#F2E7B5:#D4E2D0:#99CCD3:#6BADCB:#4E8DBF:#2356A8",
            "volume #1 transparency 0.1",
        ],
        "model_commands": [
            "color #2 grey",
        ],
    },
    # Special chain colouring mode: the defaults come from --chain-colours.
    "chain": {
        "kind": "chain",
        "requires_model": True,
        "requires_chain_colours": True,
    },
}


def available_colour_choices():
    """Return CLI colour choices from the registry."""
    return tuple(COLOUR_SPECS.keys())


def get_colour_spec(colour):
    try:
        return COLOUR_SPECS[colour]
    except KeyError as exc:
        raise ValueError(f"Unknown colour scheme: {colour}") from exc


def validate_colour_registry():
    """Fail fast if a registry entry is malformed."""
    for colour_name, spec in COLOUR_SPECS.items():
        if spec.get("kind") == "chain":
            continue

        if "map_commands" not in spec or not isinstance(spec["map_commands"], list):
            raise ValueError(f"Colour '{colour_name}' must define a map_commands list")
        if "model_commands" not in spec or not isinstance(spec["model_commands"], list):
            raise ValueError(f"Colour '{colour_name}' must define a model_commands list")


def validate_colour_selection(colour, model, chain_colours, parser):
    """Validate command-line dependencies for the selected colour."""
    spec = get_colour_spec(colour)

    if spec.get("requires_model") and not model:
        parser.error(f"--colour {colour} requires --model to be specified")

    if spec.get("requires_chain_colours") and not chain_colours:
        parser.error(f"--colour {colour} requires --chain-colours")

    if chain_colours and not spec.get("requires_chain_colours"):
        parser.error("--chain-colours can only be used with --colour chain")


def parse_chain_colours(chain_colours):
    """Parse 'chain:colour chain:colour' strings into (chain, colour) pairs."""
    parsed = []
    seen_chain_ids = set()
    chain_pattern = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")

    for token in chain_colours.split():
        if ":" not in token:
            raise ValueError(
                f"Invalid --chain-colours entry '{token}'. Expected format chain:colour"
            )

        chain_id, colour = token.split(":", 1)
        if not chain_id or not colour:
            raise ValueError(
                f"Invalid --chain-colours entry '{token}'. Expected format chain:colour"
            )
        if not chain_pattern.match(chain_id):
            raise ValueError(
                f"Invalid chain ID '{chain_id}' in --chain-colours entry '{token}'. "
                "Use an alphanumeric chain ID with optional . _ - characters."
            )
        if any(ch.isspace() for ch in colour) or ":" in colour or "/" in colour:
            raise ValueError(
                f"Invalid colour '{colour}' in --chain-colours entry '{token}'. "
                "Use a ChimeraX colour name or hex value without spaces, ':' or '/'."
            )
        if chain_id in seen_chain_ids:
            raise ValueError(
                f"Duplicate chain ID '{chain_id}' in --chain-colours. "
                "Specify each chain only once."
            )

        parsed.append((chain_id, colour))
        seen_chain_ids.add(chain_id)

    if not parsed:
        raise ValueError(
            "No chain colours provided. Expected at least one entry in --chain-colours"
        )

    return parsed


def extend_map_colouring_commands(commands, colour):
    """Append map colouring commands for the requested scheme."""
    spec = get_colour_spec(colour)
    for line in spec.get("map_commands", []):
        commands.append(line)


def extend_model_colouring_commands(commands, colour, pdb_present, chain_colours=None):
    """Append model colouring commands for the requested scheme."""
    if not pdb_present:
        return

    spec = get_colour_spec(colour)

    if spec.get("kind") == "chain":
        chain_colours = chain_colours or []
        default_colour = None
        overrides = []

        for chain_id, chain_colour in chain_colours:
            if chain_id == "all":
                default_colour = chain_colour
            else:
                overrides.append((chain_id, chain_colour))

        if default_colour is not None:
            commands.append(f"color #2 {default_colour}")

        for chain_id, chain_colour in overrides:
            commands.append(f"color #2/{chain_id} {chain_colour}")
        commands.append("color zone #1 near #2")
        commands.append("volume #1 transparency 0.1")
    else:
        for line in spec.get("model_commands", []):
            commands.append(line)

def derive_emd_id(mrc_file):
    """Derive an EMD-style identifier from the input map filename."""
    base = os.path.basename(mrc_file)
    for suffix in (".map.gz", ".mrc.gz", ".map", ".mrc", ".gz"):
        if base.lower().endswith(suffix):
            base = base[: -len(suffix)]
            break
    return base


def derive_pdb_id(pdb_file):
    """Derive a PDB-style identifier from the input model filename."""
    if not pdb_file:
        return None
    base = os.path.basename(pdb_file)
    for suffix in (".pdb.gz", ".cif.gz", ".mmcif.gz", ".ent.gz", ".pdb", ".cif", ".mmcif", ".ent", ".gz"):
        if base.lower().endswith(suffix):
            base = base[: -len(suffix)]
            break
    return base


def build_label_text(mrc_file, pdb_file):
    """Format the corner label text from the input identifiers."""
    emd_id = derive_emd_id(mrc_file)
    pdb_id = derive_pdb_id(pdb_file) if pdb_file else None
    if pdb_id:
        return f"EMD-ID: {emd_id} | PDB ID: {pdb_id}"
    return f"EMD-ID: {emd_id}"


def extend_label_commands(commands, mrc_file, pdb_file):
    """Append a 2D label command for the lower-right corner."""
    label_text = build_label_text(mrc_file, pdb_file)
    # ChimeraX 2D labels are anchored in window coordinates; placing the
    # label near the lower-right corner keeps it readable in both image and
    # movie output.
    commands.extend([
        "2dlabels create emdb_id_label text " + shlex.quote(label_text),
        "2dlabels style emdb_id_label size 28 color white",
        "2dlabels anchor emdb_id_label bottom right",
        "2dlabels offset emdb_id_label -18 18",
    ])


def parse_turnxz(value):
    try:
        x, z = (float(part.strip()) for part in value.split(","))
    except (ValueError, TypeError):
        raise argparse.ArgumentTypeError("--turnxz requires two angles: X,Z (for example, 90,-30)")
    if not math.isfinite(x) or not math.isfinite(z):
        raise argparse.ArgumentTypeError("--turnxz angles must be finite numbers")
    return x, z

def write_chimerax_script_movie(
    mrc_file, pdb_file, output_movie, quality,
    colour, background, contour, movie_format, exit=True,
    label=False, session_only=False, script_suffix="script",
    chain_colours=None, turnxz=(-90, 0)
):
    window_size = "513 270" if quality in ("web", "web1", "web2", "web3") else "750 750"
    commands = [
        f"open {shlex.quote(mrc_file)}",
        f"windowsize {window_size}",
    ]

    # Contour block
    if contour == "MIT":
        commands.append("volume calc_level #1")
    elif contour is not None:
        commands.append(f"volume #1 level {contour}")

    # Map colours
    if colour != "chain":
        extend_map_colouring_commands(commands, colour)

    # Background colour
    if background:
        commands.append(f"set bgColor {background}")

    # Model block
    if pdb_file:
        commands.append(f"open {shlex.quote(pdb_file)}")
        commands.append("view #1")
        extend_model_colouring_commands(commands, colour, True, chain_colours)

        commands.extend(["hide #2 atoms", "show #2 cartoons"])
    else:
        commands.append("volume #1 transparency 0")

    if label:
        extend_label_commands(commands, mrc_file, pdb_file)

    if session_only:
        commands.extend([
            "graphics silhouettes true width 2",
            "lighting soft",
            "view #1",
            "zoom 0.8",
            f"turn x {turnxz[0]:g}",
            f"turn z {turnxz[1]:g}",
        ])
    else:
        # Movie camera + render
        if quality in ("web", "web1", "web2", "web3"):
            commands.extend([
                "graphics silhouettes true width 1",
                "lighting soft",
                "view #1",
                "zoom 0.8",
                f"turn x {turnxz[0]:g}",
                f"turn z {turnxz[1]:g}",
                "turn y 1 360",
            ])
        else:
            commands.extend([
                "graphics silhouettes true width 2",
                "lighting soft",
                "view #1",
                "zoom 0.8",
                f"turn x {turnxz[0]:g}",
                f"turn z {turnxz[1]:g}",
                "turn y 0.5 720",
            ])

        if quality == "publication":
            commands.append("movie record supersample 4 size 1400,1400",)
        elif quality == "presentation":
                    commands.append("movie record supersample 4 size 750,750",)
        elif quality == "onscreen":
            commands.append("movie record supersample 3 size 750,750",)
        elif quality == "web":
            commands.append("movie record supersample 1 size 513,270",)
        elif quality == "web1":
            commands.append("movie record supersample 2 size 513,270",)
        elif quality == "web2":
            commands.append("movie record supersample 3 size 513,270",)
        elif quality == "web3":
            commands.append("movie record supersample 4 size 513,270",)

        if quality in ("web", "web1", "web2", "web3"):
            commands.extend([
                "wait 360",
            ])
        else:
            commands.extend([
                "wait 720",
            ])

        if quality == "publication":
            commands.append(f"movie encode output {shlex.quote(output_movie)} format {movie_format} framerate 30 quality highest",)
        if quality == "presentation":
            commands.append(f"movie encode output {shlex.quote(output_movie)} format {movie_format} framerate 30 quality highest",)
        elif quality == "onscreen":
            commands.append(f"movie encode output {shlex.quote(output_movie)} format {movie_format} framerate 30 quality highest",)
        elif quality == "web":
            commands.append(f"movie encode output {shlex.quote(output_movie)} format {movie_format} framerate 25 qscale 1 ",)
        elif quality == "web1":
            commands.append(f"movie encode output {shlex.quote(output_movie)} format {movie_format} framerate 25 qscale 1 ",)
        elif quality == "web2":
            commands.append(f"movie encode output {shlex.quote(output_movie)} format {movie_format} framerate 25 qscale 1 ",)
        elif quality == "web3":
            commands.append(f"movie encode output {shlex.quote(output_movie)} format {movie_format} framerate 25 qscale 1 ",)

        commands.extend([
            "stop",
        ])

        if exit:
            commands.append("exit")

    basename = os.path.splitext(os.path.basename(output_movie))[0]
    script_name = f"{basename}_{script_suffix}.cxc"
    script_path = os.path.join(os.path.dirname(os.path.abspath(output_movie)), script_name)

    with open(script_path, "w") as out:
        out.write("\n".join(commands))

    return script_path

def write_chimerax_script_image(
    mrc_file, pdb_file, output_image,
    colour, background, transparent_background, contour, exit=True,
    label=False, session_only=False, script_suffix="script",
    chain_colours=None, turnxz=(-90, 0)
):
    commands = [
        f"open {shlex.quote(mrc_file)}",
        "windowsize 750 750",
    ]

    if contour == "MIT":
        commands.append("volume calc_level #1")
    elif contour is not None:
        commands.append(f"volume #1 level {contour}")

    if colour != "chain":
        extend_map_colouring_commands(commands, colour)

    # Background colour
    if background:
        commands.append(f"set bgColor {background}")

    if pdb_file:
        commands.append(f"open {shlex.quote(pdb_file)}")
        commands.append("view #1")
        extend_model_colouring_commands(commands, colour, True, chain_colours)

        commands.extend(["hide #2 atoms", "show #2 cartoons"])
    else:
        commands.append("volume #1 transparency 0")

    if label:
        extend_label_commands(commands, mrc_file, pdb_file)

    commands.extend([
        "graphics silhouettes true width 2",
        "lighting soft",
        "view #1",
        "zoom 0.8",
        f"turn x {turnxz[0]:g}",
        f"turn z {turnxz[1]:g}",
    ])

    if session_only:
        pass
    else:
        commands.append(
            f"save {shlex.quote(output_image)} format png supersample 4 transparentBackground {transparent_background}"
        )

        if exit:
            commands.append("exit")

    basename = os.path.splitext(os.path.basename(output_image))[0]
    script_name = f"{basename}_{script_suffix}.cxc"
    script_path = os.path.join(os.path.dirname(os.path.abspath(output_image)), script_name)

    with open(script_path, "w") as out:
        out.write("\n".join(commands))

    return script_path


def format_relative_path(path, base_dir):
    """Format path relative to base_dir for summary output."""
    if path is None:
        return "(none)"
    return os.path.relpath(path, base_dir)


def resolve_chimerax_executable(chimerax_arg=None, ignore_check=False):
    """
    Resolve ChimeraX executable.

    Priority:
    1. User-provided --chimerax path
    2. chimerax found in PATH
    """

    if chimerax_arg:
        chimerax_path = os.path.abspath(os.path.expanduser(chimerax_arg))

        if ignore_check:
            return chimerax_path

        if os.path.isfile(chimerax_path) and os.access(chimerax_path, os.X_OK):
            return chimerax_path

        sys.exit(
            f"Provided ChimeraX executable is not valid or not executable:\n"
            f"{chimerax_path}"
        )

    chimerax_in_path = shutil.which("chimerax")

    if chimerax_in_path:
        return chimerax_in_path

    if ignore_check:
        return "chimerax"

    sys.exit(
        "ChimeraX not found in PATH.\n"
        "Please provide the executable path using:\n"
        "  --chimerax /path/to/chimerax\n\n"
        "Example on macOS:\n"
        "  --chimerax /Applications/ChimeraX.app/Contents/MacOS/ChimeraX"
    )



# ======================
# Runner
# ======================

def is_headless_environment():
    """Return True when no graphical display appears to be available."""

    # On Linux/Unix clusters, GUI-capable sessions usually expose DISPLAY
    # for X11 or WAYLAND_DISPLAY for Wayland. If neither exists, treat the
    # session as headless and use ChimeraX offscreen mode.
    if sys.platform.startswith("linux") or sys.platform.startswith("freebsd"):
        return not (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))

    # macOS/Windows normally launch GUI apps without DISPLAY/WAYLAND_DISPLAY.
    # Do not force offscreen mode there unless the user is on Linux-like HPC.
    return False


def run_chimerax(script_path, chimerax_executable):
    if is_headless_environment():
        cmd = [chimerax_executable, "--offscreen", "--nogui", script_path]
        print("Detected headless environment: running ChimeraX with --offscreen --nogui")
    else:
        cmd = [chimerax_executable, script_path]
        print("Detected graphical environment: running ChimeraX without --offscreen --nogui")

    subprocess.run(cmd, check=True)

# ======================
# CLI
# ======================

def main():

    movie_extension_map = {
        "h264": ".mp4",
        "mov": ".mov",
        "avi": ".avi",
        "apng": ".apng",
    }

    parser = argparse.ArgumentParser(
        description="Generate ChimeraX movies or images",
        formatter_class=type(
            "HelpFormatter",
            (argparse.ArgumentDefaultsHelpFormatter, argparse.RawDescriptionHelpFormatter),
            {}
        ),
        epilog=(
            "Examples:\n"
            "  python emdb.chimerax_make_image_movie.py --mrc map.mrc --format both\n"
            "  python emdb.chimerax_make_image_movie.py --mrc map.mrc --model model.pdb \\\n"
            "      --colour chain --chain-colours \"A:orange B:cyan C:lightblue\"\n"
            "  python emdb.chimerax_make_image_movie.py --mrc map.mrc --model model.pdb \\\n"
            "      --colour chain --chain-colours \"all:green A:orange B:cyan\"\n"
            "  Use \"all:<colour>\" to set the default model colour before per-chain overrides.\n"
            "  python emdb.chimerax_make_image_movie.py --mrc map.mrc --model model.pdb \\\n"
            "      --colour chain --chain-colours \"A:#ff7f0e B:#00bcd4\"\n"
        )
    )

    # -------------------------------
    # GROUP: Map & Contour Options
    # -------------------------------
    group_map = parser.add_argument_group("Map & Contour Options")

    group_map.add_argument('--mrc', required=True)
    group_map.add_argument('--model')

    group_map.add_argument(
        '--auto-contour',
        choices=['rmsd', 'p99', 'hybrid', '3sig', '6sig', '9sig', 'abs30', 'MIT'],
        default='6sig',  help="Auto contour calculation method"
    )

    group_map.add_argument('--contour', type=float)

    # -------------------------------
    # GROUP: Rendering Options
    # -------------------------------
    group_render = parser.add_argument_group("Rendering Options")

    group_render.add_argument(
        '--format',
        choices=['movie', 'image', 'both'],
        default='image', help="Produce movie, image or both"
    )
    
    group_render.add_argument(
        '--quality',
        choices=['publication', 'presentation', 'onscreen', 'web', 'web1', 'web2', 'web3'],
        default='onscreen', help="quality to use in rendering"
    )

    group_render.add_argument(
        '--movie-format',
        choices=['h264', 'mov', 'avi', 'apng'],
        default='mov',
        help="Movie encoding/container format"
    )

    group_render.add_argument(
        '--colour', '--color',
        choices=available_colour_choices(),
        default='blue', help="Colour scheme for map and model; chain requires --model and --chain-colours"
    )

    group_render.add_argument(
        '--chain-colours',
        metavar='"CHAIN:COLOUR [CHAIN:COLOUR ...]"',
        help='Chain-specific colours in the format "A:orange B:cyan C:lightblue"'
    )

    group_render.add_argument(
        '--background',
        choices=['white', 'black','#FFFFFF', '#181818', '#2A2A2A', '#161f28'],
        default='#161f28', help="Background colour (Default is blueksy dark mode)"
    )

    group_render.add_argument(
        '--transparent', action='store_true', help="Use transparent background for image output"
    )
    group_render.add_argument(
        '--label',
        action='store_true',
        help='Add a bottom-right label with the EMD-ID and PDB ID'
    )
    group_render.add_argument(
        '--turnxz', type=parse_turnxz, default=(-90, 0), metavar='X,Z',
        help='Initial camera turns around X and Z (default: -90,0)'
    )

    # -------------------------------
    # GROUP: Output Options
    # -------------------------------
    group_out = parser.add_argument_group("Output Options")

    group_out.add_argument('--outname', help="Base prefix for output files")
    group_out.add_argument('--outdir', '--out-dir', help="Output directory")

    group_out.add_argument(
        '--save-script',
        action=argparse.BooleanOptionalAction,
        default=True,
        help='Generate the normal render-and-exit ChimeraX scene script'
    )
    group_out.add_argument(
        '--save-session',
        action=argparse.BooleanOptionalAction,
        default=True,
        help='Generate a ChimeraX scene script for interactive inspection without saving output or exiting'
    )
    group_out.add_argument('--script-only', action='store_true')
    group_out.add_argument('--no-exit', action='store_true')
    group_out.add_argument(
        '--summary',
        dest='summary',
        action='store_true',
        help='Write an output summary file with the command used and generated outputs'
    )
    group_out.add_argument(
        '--no-summary',
        dest='summary',
        action='store_false',
        help='Disable writing the output summary file'
    )
    parser.set_defaults(summary=True)

    # -------------------------------
    # GROUP: Execution Control
    # -------------------------------
    group_exec = parser.add_argument_group("Execution Control Options")
    group_exec.add_argument(
        '--chimerax',
        help='Path to ChimeraX executable, e.g. /Applications/ChimeraX.app/Contents/MacOS/ChimeraX'
    )
    
    group_exec.add_argument('--ignore-check', action='store_true')
    validate_colour_registry()
    args = parser.parse_args()

    validate_colour_selection(args.colour, args.model, args.chain_colours, parser)

    chain_colours = None
    if args.chain_colours:
        try:
            chain_colours = parse_chain_colours(args.chain_colours)
        except ValueError as exc:
            parser.error(str(exc))

    # ChimeraX executable resolution
    if not args.script_only:
        chimerax_executable = resolve_chimerax_executable(
            chimerax_arg=args.chimerax,
            ignore_check=args.ignore_check
        )
        print(f"Using ChimeraX executable: {chimerax_executable}")
    else:
        chimerax_executable = None


    # --- Contour ---
    contour_value = args.contour if args.contour is not None else compute_auto_contour(args.mrc, args.auto_contour)

    # --- Decompression ---
    if args.mrc.endswith(".gz"):
        uncompressed = os.path.splitext(args.mrc)[0]
        with open(uncompressed, "wb") as f_out, gzip.open(args.mrc, "rb") as f_in:
            shutil.copyfileobj(f_in, f_out)
        mrc = uncompressed
    else:
        mrc = args.mrc

    if args.model and args.model.endswith(".gz"):
        uncompressed_model = os.path.splitext(args.model)[0]
        with open(uncompressed_model, "wb") as f_out, gzip.open(args.model, "rb") as f_in:
            shutil.copyfileobj(f_in, f_out)
        pdb = uncompressed_model
    else:
        pdb = args.model

    mrc = os.path.abspath(mrc)
    if pdb:
        pdb = os.path.abspath(pdb)

    # ============================
    # Output Directory + Prefix Logic
    # ============================

    if args.outdir:
        outdir = os.path.abspath(args.outdir)
        os.makedirs(outdir, exist_ok=True)
    else:
        outdir = os.path.dirname(mrc)

    if args.outname:
        outbase = os.path.join(outdir, args.outname)
    else:
        basename = os.path.splitext(os.path.basename(mrc))[0]
        outbase = os.path.join(outdir, basename)

    # ============================
    # COMMAND LOGGING
    # ============================
    summary_path = f"{outbase}_summary.txt"
    summary_dir = os.path.dirname(summary_path)
    summary_lines = [
        "Command used to run this script:",
        " ".join(shlex.quote(a) for a in sys.argv),
        "",
        "Resolved inputs:",
        f"  MRC: {format_relative_path(mrc, summary_dir)}",
        f"  Model: {format_relative_path(pdb, summary_dir)}",
        f"  Output directory: {format_relative_path(outdir, summary_dir)}",
        f"  Output prefix: {format_relative_path(outbase, summary_dir)}",
        f"  Format: {args.format}",
        f"  Contour: {contour_value}",
    ]
    generated_outputs = []

    # ============================
    # MOVIE
    # ============================

    if args.format in ("movie", "both"):
        output_movie = f"{outbase}_chimerax_movie{movie_extension_map[args.movie_format]}"

        if args.save_script:
            script_path = write_chimerax_script_movie(
                mrc, pdb, output_movie, args.quality,
                args.colour, args.background, contour_value, args.movie_format,
                label=args.label,
                session_only=False,
                script_suffix="script",
                chain_colours=chain_colours,
                turnxz=args.turnxz,
                exit=not args.no_exit
            )

            print(f"Movie script → {script_path}")
            generated_outputs.append(f"Movie script: {format_relative_path(script_path, summary_dir)}")
            generated_outputs.append(f"Movie output: {format_relative_path(output_movie, summary_dir)}")

            if not args.script_only:
                run_chimerax(script_path, chimerax_executable)
                print(f"Movie created → {output_movie}")

        if args.save_session:
            session_script_path = write_chimerax_script_movie(
                mrc, pdb, output_movie, args.quality,
                args.colour, args.background, contour_value, args.movie_format,
                label=args.label,
                session_only=True,
                script_suffix="session_script",
                chain_colours=chain_colours,
                turnxz=args.turnxz,
                exit=False
            )

            print(f"Movie session script → {session_script_path}")
            generated_outputs.append(f"Movie session script: {format_relative_path(session_script_path, summary_dir)}")

    # ============================
    # IMAGE
    # ============================

    if args.format in ("image", "both"):
        output_image = f"{outbase}_chimerax_image.png"

        if args.save_script:
            script_path = write_chimerax_script_image(
                mrc, pdb, output_image,
                args.colour, args.background, args.transparent, contour_value,
                label=args.label,
                session_only=False,
                script_suffix="script",
                chain_colours=chain_colours,
                turnxz=args.turnxz,
                exit=not args.no_exit
            )

            print(f"Image script → {script_path}")
            generated_outputs.append(f"Image script: {format_relative_path(script_path, summary_dir)}")
            generated_outputs.append(f"Image output: {format_relative_path(output_image, summary_dir)}")

            if not args.script_only:
                run_chimerax(script_path, chimerax_executable)
                print(f"Image created → {output_image}")

        if args.save_session:
            session_script_path = write_chimerax_script_image(
                mrc, pdb, output_image,
                args.colour, args.background, args.transparent, contour_value,
                label=args.label,
                session_only=True,
                script_suffix="session_script",
                chain_colours=chain_colours,
                turnxz=args.turnxz,
                exit=False
            )

            print(f"Image session script → {session_script_path}")
            generated_outputs.append(f"Image session script: {format_relative_path(session_script_path, summary_dir)}")

    if generated_outputs:
        summary_lines.extend(["", "Generated outputs:"])
        summary_lines.extend(f"  {line}" for line in generated_outputs)

    if args.summary:
        try:
            with open(summary_path, "w") as summary_out:
                summary_out.write("\n".join(summary_lines))
                summary_out.write("\n")
            print(f"Summary written → {summary_path}")
        except Exception as e:
            print(f"Warning: could not write summary file: {e}")

    # Cleanup
    if args.mrc.endswith(".gz"):
        os.remove(mrc)
    if args.model and args.model.endswith(".gz"):
        os.remove(pdb)


if __name__ == "__main__":
    main()
