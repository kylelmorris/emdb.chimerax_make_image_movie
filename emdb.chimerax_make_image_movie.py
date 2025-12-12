#!/Users/kyle/anaconda3/bin/python
#

import subprocess
import argparse
import shutil
import sys
import os
import gzip
import shlex
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

def write_chimerax_script_movie(
    mrc_file, pdb_file, output_movie, output_session, quality,
    colour, background, contour, exit=True, save=False
):
    commands = [
        f"open {shlex.quote(mrc_file)}",
        "windowsize 750 750",
        "volume calc_level #1",
    ]

    # Contour block
    if contour == "MIT":
        commands.append("volume calc_level #1")
    elif contour is not None:
        commands.append(f"volume #1 level {contour}")

    # Map colours
    if colour == "kelly":
        commands.append("volume #1 color cornflowerblue")
        commands.append("volume #1 transparency 0.1")
    elif colour == "blue":
        commands.append("color radial #1 center #1 palette #045a8d:#2b8cbe:#74a9cf:#bdc9e1:#f1eef6")
        commands.append("volume #1 transparency 0.1")
    elif colour == "emdb":
        commands.append("color radial #1 center #1 palette #AD2447:#EA3861:#38B249:#90CB8A:#CFE7CB")
        commands.append("volume #1 transparency 0.1")
    elif colour == "rainbow":
        commands.append("color radial #1 center #1 palette #DC504D:#E37F4F:#EDEB7E:#71B86D:#5BB6E7:#4263AA")
        commands.append("volume #1 transparency 0.1")
    elif colour == "rainbowr":
        commands.append("color radial #1 center #1 palette #4263AA:#5BB6E7:#71B86D:#EDEB7E:#E37F4F:#DC504D")
        commands.append("volume #1 transparency 0.1")

    # Background colour
    if background:
        commands.append(f"set bgColor {background}")

    # Model block
    if pdb_file:
        commands.append(f"open {shlex.quote(pdb_file)}")
        commands.append("view #1")

        if colour == "kelly":
            commands.append("color #2 royalblue target c")
        else:
            commands.append("color #2 grey")

        commands.extend(["hide #2 atoms", "show #2 cartoons"])
    else:
        commands.append("volume #1 transparency 0")

    # Movie camera + render
    commands.extend([
        "graphics silhouettes true width 2",
        "lighting soft",
        "view #1",
        "zoom 0.8",
        "turn x 90",
        "turn z -30",
        "turn y 0.5 720",
    ])

    if quality == "publication":
        commands.append("movie record supersample 4 size 1400,1400 transparentBackground true format png",)
    elif quality == "onscreen":
        commands.append("movie record supersample 3 size 750,750 transparentBackground true format png",)
    elif quality == "web":
        commands.append("movie record supersample 2 size 750,750 transparentBackground true format png",)

    commands.extend([
        "wait 720",
    ])

    if quality == "publication":
        commands.append(f"movie encode output {shlex.quote(output_movie)} framerate 30 quality highest",)
    elif quality == "onscreen":
        commands.append(f"movie encode output {shlex.quote(output_movie)} framerate 30 quality highest",)   
    elif quality == "web":
        commands.append(f"movie encode output {shlex.quote(output_movie)} framerate 30 quality higher",) 

    commands.extend([
        "stop",
    ])

    if save:
        commands.append(f"save {shlex.quote(output_session)}")
    if exit:
        commands.append("exit")

    basename = os.path.splitext(os.path.basename(output_movie))[0]
    script_name = f"{basename}_script.cxc"
    script_path = os.path.join(os.path.dirname(os.path.abspath(output_movie)), script_name)

    with open(script_path, "w") as out:
        out.write("\n".join(commands))

    return script_path

def write_chimerax_script_image(
    mrc_file, pdb_file, output_image, output_session,
    colour, background, transparent_background, contour, exit=True, save=False
):
    commands = [
        f"open {shlex.quote(mrc_file)}",
        "windowsize 750 750",
        "volume calc_level #1",
    ]

    if contour == "MIT":
        commands.append("volume calc_level #1")
    elif contour is not None:
        commands.append(f"volume #1 level {contour}")

    if colour == "kelly":
        commands.append("volume #1 color cornflowerblue")
        commands.append("volume #1 transparency 0.1")
    elif colour == "blue":
        commands.append("color radial #1 center #1 palette #045a8d:#2b8cbe:#74a9cf:#bdc9e1:#f1eef6")
        commands.append("volume #1 transparency 0.1")
    elif colour == "emdb":
        commands.append("color radial #1 center #1 palette #AD2447:#EA3861:#38B249:#90CB8A:#CFE7CB")
        commands.append("volume #1 transparency 0.1")
    elif colour == "rainbow":
        commands.append("color radial #1 center #1 palette #DC504D:#E37F4F:#EDEB7E:#71B86D:#5BB6E7:#4263AA")
        commands.append("volume #1 transparency 0.1")
    elif colour == "rainbowr":
        commands.append("color radial #1 center #1 palette #4263AA:#5BB6E7:#71B86D:#EDEB7E:#E37F4F:#DC504D")
        commands.append("volume #1 transparency 0.1")

    # Background colour
    if background:
        commands.append(f"set bgColor {background}")

    if pdb_file:
        commands.append(f"open {shlex.quote(pdb_file)}")
        commands.append("view #1")

        if colour == "kelly":
            commands.append("color #2 royalblue target c")
        else:
            commands.append("color #2 grey")

        commands.extend(["hide #2 atoms", "show #2 cartoons"])
    else:
        commands.append("volume #1 transparency 0")

    commands.extend([
        "graphics silhouettes true width 2",
        "lighting soft",
        "view #1",
        "zoom 0.8",
        "turn x -90",
        f"save {shlex.quote(output_image)} format png supersample 4 transparentBackground {transparent_background}",
    ])

    if save:
        commands.append(f"save {shlex.quote(output_session)}")
    if exit:
        commands.append("exit")

    basename = os.path.splitext(os.path.basename(output_image))[0]
    script_name = f"{basename}_script.cxc"
    script_path = os.path.join(os.path.dirname(os.path.abspath(output_image)), script_name)

    with open(script_path, "w") as out:
        out.write("\n".join(commands))

    return script_path


# ======================
# Runner
# ======================

def run_chimerax(script_path):
    subprocess.run(["chimerax", "--script", shlex.quote(script_path)])

# ======================
# CLI
# ======================

def main():

    parser = argparse.ArgumentParser(
        description="Generate ChimeraX movies or images",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
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
        choices=['publication', 'onscreen', 'web'],
        default='onscreen', help="quality to use in rendering"
    )

    group_render.add_argument(
        '--colour', '--color',
        choices=['kelly', 'blue', 'emdb', 'rainbow', 'rainbowr'],
        default='blue', help="Colour scheme for map and model"
    )

    group_render.add_argument(
        '--background',
        choices=['white', 'black','#FFFFFF', '#181818', '#2A2A2A', '#161f28'],
        default='#161f28', help="Background colour (Default is blueksy dark mode)"
    )

    group_render.add_argument(
        '--transparent', action='store_true', help="Use transparent background for image output"
    )

    # -------------------------------
    # GROUP: Output Options
    # -------------------------------
    group_out = parser.add_argument_group("Output Options")

    group_out.add_argument('--outname', help="Base prefix for output files")
    group_out.add_argument('--outdir', help="Output directory")

    group_out.add_argument('--save-session', action='store_true')
    group_out.add_argument('--script-only', action='store_true')
    group_out.add_argument('--no-exit', action='store_true')

    # -------------------------------
    # GROUP: Execution Control
    # -------------------------------
    group_exec = parser.add_argument_group("Execution Control Options")
    group_exec.add_argument('--ignore-check', action='store_true')

    args = parser.parse_args()

    # ChimeraX PATH check
    if not args.script_only and not args.ignore_check and not shutil.which("chimerax"):
        sys.exit("ChimeraX not found in PATH")

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
        outdir = args.outdir
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
    command_log_path = f"{outbase}_command.txt"

    try:
        with open(command_log_path, "w") as cmd_out:
            cmd_out.write("Command used to run this script:\n")
            cmd_out.write(" ".join(shlex.quote(a) for a in sys.argv))
            cmd_out.write("\n")
        print(f"Command log written → {command_log_path}")
    except Exception as e:
        print(f"Warning: could not write command log file: {e}")

    # ============================
    # MOVIE
    # ============================

    if args.format in ("movie", "both"):
        output_movie = f"{outbase}_chimerax_movie.mov"
        output_session = f"{outbase}_chimerax_movie_session.cxs"

        script_path = write_chimerax_script_movie(
            mrc, pdb, output_movie, output_session, args.quality, 
            args.colour, args.background, contour_value,
            save=args.save_session,
            exit=not args.no_exit
        )

        print(f"Movie script → {script_path}")

        if not args.script_only:
            run_chimerax(script_path)
            print(f"Movie created → {output_movie}")

    # ============================
    # IMAGE
    # ============================

    if args.format in ("image", "both"):
        output_image = f"{outbase}_chimerax_image.png"
        output_session = f"{outbase}_chimerax_image_session.cxs"

        script_path = write_chimerax_script_image(
            mrc, pdb, output_image, output_session,
            args.colour, args.background, args.transparent, contour_value,
            save=args.save_session,
            exit=not args.no_exit
        )

        print(f"Image script → {script_path}")

        if not args.script_only:
            run_chimerax(script_path)
            print(f"Image created → {output_image}")

    # Cleanup
    if args.mrc.endswith(".gz"):
        os.remove(mrc)
    if args.model and args.model.endswith(".gz"):
        os.remove(pdb)


if __name__ == "__main__":
    main()
