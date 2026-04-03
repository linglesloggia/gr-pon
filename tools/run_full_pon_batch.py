#!/usr/bin/env python3
"""
gr-pon/tools/run_full_pon_batch.py

Batch runner for the `full_pon_demod.py` flowgraph.

Purpose
-------
Automate processing many capture files stored in multiple folders. For each input
file the script:

  - sets environment variables so the flowgraph reads that input and writes
    outputs into the same directory (GPON_IN_FILE and GPON_OUT_DIR),
  - launches the flowgraph script as a subprocess,
  - waits until output files stop growing for a short "stabilize" period (or a
    maximum timeout),
  - terminates the flowgraph and proceeds to the next input.

This lets you run everything from the terminal and have outputs (binary + readable)
placed alongside inputs for easy automation.

Usage
-----
Example:
  python3 gr-pon/tools/run_full_pon_batch.py \
    --glob '/data/captures/**/*.f32' \
    --fg-script /home/you/projects/gr-pon/examples/full_pon_demod.py \
    --timeout 300 --stabilize 4

Options
-------
--glob        Required. Glob pattern to find input files (quotes recommended).
--fg-script   Path to the generated flowgraph runner script (full_pon_demod.py).
--timeout     Max seconds to wait per file (default 300).
--stabilize   Seconds of unchanged filesize to consider processing finished (default 3).
--python-cmd  Python interpreter to use (default: python3).
--pythonpath  Optional PYTHONPATH value to inject (useful to point to repo/python).
--headless    If set, export QT_QPA_PLATFORM=offscreen to try to avoid opening GUI windows.
--keep-running    Don't stop the FG on stabilization; continue writing until timeout (useful for streaming).
--concurrency N   (Not implemented in this script; kept for CLI compatibility.)

Notes
-----
- The script assumes the flowgraph writes:
    - a binary file named 'output' in GPON_OUT_DIR (that's how full_pon_demod.py was edited),
    - readable logs 'gpon_payloads.hex' and 'gpon_payloads.jsonl' in GPON_OUT_DIR
  (the parser block was modified to create these).
- This runner is conservative: it waits for stabilization of file sizes to
  decide processing is done. That works well for finite capture files.
"""

from __future__ import annotations

import argparse
import glob
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional, Tuple

DEFAULT_FG_SCRIPT = "gr-pon/examples/full_pon_demod.py"


def file_sizes(paths: Tuple[Path, ...]) -> Tuple[int, ...]:
    """Return sizes for each path (or -1 if missing)."""
    sizes = []
    for p in paths:
        try:
            sizes.append(p.stat().st_size)
        except Exception:
            sizes.append(-1)
    return tuple(sizes)


def wait_for_stabilization(
    proc: subprocess.Popen,
    paths: Tuple[Path, ...],
    timeout: int,
    stabilize: int,
    poll_interval: float = 1.0,
    keep_running: bool = False,
) -> None:
    """
    Wait until the file sizes in `paths` stop changing for `stabilize` seconds
    or until `timeout` seconds have elapsed, or until the child process exits.

    If keep_running is True, do not stop the process on stabilization; instead
    wait only for `timeout` or process exit.
    """
    start = time.time()
    last = file_sizes(paths)
    stable_since: Optional[float] = None

    while True:
        # If process terminated by itself, return
        ret = proc.poll()
        if ret is not None:
            print(f"[runner] Flowgraph process exited with returncode={ret}")
            return

        cur = file_sizes(paths)

        if cur == last:
            if stable_since is None:
                stable_since = time.time()
            elif not keep_running and (time.time() - stable_since) >= stabilize:
                print(f"[runner] Files stabilized for {stabilize}s: {paths}")
                return
        else:
            stable_since = None
            last = cur

        if (time.time() - start) >= timeout:
            print(f"[runner] Timeout {timeout}s reached; stopping wait")
            return

        time.sleep(poll_interval)


def run_flowgraph_for_file(
    fg_script: Path,
    in_path: Path,
    python_cmd: str,
    pythonpath: Optional[str],
    headless: bool,
    timeout: int,
    stabilize: int,
    keep_running: bool,
) -> None:
    """
    Launch the flowgraph script with environment variables set so it reads
    `in_path` and writes outputs into the same directory. Monitors outputs and
    stops the FG when done (or on timeout).
    """
    out_dir = in_path.parent.resolve()
    env = os.environ.copy()
    env["GPON_IN_FILE"] = str(in_path.resolve())
    env["GPON_OUT_DIR"] = str(out_dir)

    # If user supplied a PYTHONPATH, inject it
    if pythonpath:
        env["PYTHONPATH"] = pythonpath + os.pathsep + env.get("PYTHONPATH", "")

    # Try to avoid opening GUI windows if requested
    if headless:
        env.setdefault("QT_QPA_PLATFORM", "offscreen")
        # Also unset DISPLAY to be safe in some headless environments
        # (commented out by default; uncomment if needed)
        # env.pop("DISPLAY", None)

    # Paths the script will write (per earlier edits to flowgraph/parser)
    out_bin = out_dir / "output"
    out_hex = out_dir / "gpon_payloads.hex"
    out_jsonl = out_dir / "gpon_payloads.jsonl"

    # Prepare log files for this run
    stdout_log = out_dir / "full_pon_demod.stdout.log"
    stderr_log = out_dir / "full_pon_demod.stderr.log"

    print(f"[runner] Starting FG: {fg_script} for input: {in_path}")
    print(f"[runner] Output dir: {out_dir} (binary: {out_bin})")
    print(f"[runner] Debug logs: {out_hex} , {out_jsonl}")

    # Ensure directory exists
    out_dir.mkdir(parents=True, exist_ok=True)

    # Open logs
    stdout_fh = open(stdout_log, "ab")
    stderr_fh = open(stderr_log, "ab")

    cmd = [python_cmd, str(fg_script)]
    proc = subprocess.Popen(
        cmd, env=env, cwd=str(fg_script.parent), stdout=stdout_fh, stderr=stderr_fh
    )

    try:
        wait_for_stabilization(
            proc,
            (out_bin, out_hex, out_jsonl),
            timeout,
            stabilize,
            keep_running=keep_running,
        )
    finally:
        # Terminate process if still running
        if proc.poll() is None:
            print("[runner] Terminating flowgraph process...")
            proc.terminate()
            try:
                proc.wait(timeout=5.0)
            except Exception:
                print("[runner] Killing flowgraph process...")
                proc.kill()
        # close logs
        try:
            stdout_fh.close()
        except Exception:
            pass
        try:
            stderr_fh.close()
        except Exception:
            pass

    sizes = file_sizes((out_bin, out_hex, out_jsonl))
    print(
        f"[runner] Finished {in_path.name} -> sizes (bytes): binary={sizes[0]}, hex={sizes[1]}, jsonl={sizes[2]}"
    )


def find_input_files(pattern: str) -> list[Path]:
    """Resolve glob pattern to sorted list of Path objects."""
    matches = sorted(glob.glob(pattern, recursive=True))
    return [Path(p) for p in matches]


def handle_sigint(signum, frame):
    print("[runner] Received SIGINT, exiting.", file=sys.stderr)
    # Let the main loop handle cleanup
    raise KeyboardInterrupt()


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Batch runner for full_pon_demod flowgraph"
    )
    parser.add_argument(
        "--glob",
        required=True,
        help="Glob pattern to find input files (e.g. '/data/*/*.f32')",
    )
    parser.add_argument(
        "--fg-script",
        default=DEFAULT_FG_SCRIPT,
        help="Path to flowgraph runner script (full_pon_demod.py)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=300,
        help="Max seconds to wait per file (default: 300)",
    )
    parser.add_argument(
        "--stabilize",
        type=int,
        default=3,
        help="Seconds of stable filesize to consider finished (default: 3)",
    )
    parser.add_argument(
        "--python-cmd",
        default="python3",
        help="Python interpreter to run the flowgraph",
    )
    parser.add_argument(
        "--pythonpath",
        default=None,
        help="Optional PYTHONPATH to set when running the FG (e.g. /path/to/repo/python)",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Attempt to run the flowgraph headless (sets QT_QPA_PLATFORM=offscreen)",
    )
    parser.add_argument(
        "--keep-running",
        action="store_true",
        help="Do not stop FG on stabilization; continue until timeout or exit",
    )
    args = parser.parse_args(argv)

    # Resolve fg script path
    fg_script = Path(args.fg_script).resolve()
    if not fg_script.exists():
        print(f"[runner] Flowgraph script not found: {fg_script}", file=sys.stderr)
        return 2

    files = find_input_files(args.glob)
    if not files:
        print(
            f"[runner] No input files found for pattern: {args.glob}", file=sys.stderr
        )
        return 1

    # Install SIGINT handler to allow graceful exit
    signal.signal(signal.SIGINT, handle_sigint)

    print(f"[runner] Found {len(files)} input files. Starting batch run...")
    try:
        for f in files:
            try:
                run_flowgraph_for_file(
                    fg_script=fg_script,
                    in_path=f,
                    python_cmd=args.python_cmd,
                    pythonpath=args.pythonpath,
                    headless=args.headless,
                    timeout=args.timeout,
                    stabilize=args.stabilize,
                    keep_running=args.keep_running,
                )
            except KeyboardInterrupt:
                print("[runner] Interrupted by user. Exiting batch loop.")
                break
            except Exception as e:
                print(f"[runner] Error processing {f}: {e}", file=sys.stderr)
                # continue to next file
                continue
    except KeyboardInterrupt:
        print("[runner] Received KeyboardInterrupt, stopping.")
    print("[runner] Batch run complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
