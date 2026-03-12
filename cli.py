#!/usr/bin/env python3
"""FamilyView CLI — setup and launch helper."""

import argparse
import os
import subprocess
import sys
import time
import webbrowser

# ---------------------------------------------------------------------------
# ANSI colours (degrade gracefully on Windows)
# ---------------------------------------------------------------------------

def _supports_colour():
    return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()

RESET  = "\033[0m"  if _supports_colour() else ""
BOLD   = "\033[1m"  if _supports_colour() else ""
DIM    = "\033[2m"  if _supports_colour() else ""
GREEN  = "\033[32m" if _supports_colour() else ""
YELLOW = "\033[33m" if _supports_colour() else ""
CYAN   = "\033[36m" if _supports_colour() else ""
RED    = "\033[31m" if _supports_colour() else ""

def ok(msg):    print(f"  {GREEN}✓{RESET}  {msg}")
def info(msg):  print(f"  {CYAN}→{RESET}  {msg}")
def warn(msg):  print(f"  {YELLOW}!{RESET}  {msg}")
def err(msg):   print(f"  {RED}✗{RESET}  {msg}")
def step(msg):  print(f"\n{BOLD}{msg}{RESET}")

BANNER = f"""
{CYAN}{BOLD}  ███████╗ █████╗ ███╗   ███╗██╗██╗  ██╗   ██╗{RESET}
{CYAN}{BOLD}  ██╔════╝██╔══██╗████╗ ████║██║██║  ╚██╗ ██╔╝{RESET}
{CYAN}{BOLD}  █████╗  ███████║██╔████╔██║██║██║   ╚████╔╝ {RESET}
{CYAN}{BOLD}  ██╔══╝  ██╔══██║██║╚██╔╝██║██║██║    ╚██╔╝  {RESET}
{CYAN}{BOLD}  ██║     ██║  ██║██║ ╚═╝ ██║██║███████╗██║   {RESET}
{CYAN}{BOLD}  ╚═╝     ╚═╝  ╚═╝╚═╝     ╚═╝╚═╝╚══════╝╚═╝  {RESET}
{CYAN}{BOLD}       ██╗   ██╗██╗███████╗██╗    ██╗          {RESET}
{CYAN}{BOLD}       ██║   ██║██║██╔════╝██║    ██║          {RESET}
{CYAN}{BOLD}       ██║   ██║██║█████╗  ██║ █╗ ██║          {RESET}
{CYAN}{BOLD}       ╚██╗ ██╔╝██║██╔══╝  ██║███╗██║          {RESET}
{CYAN}{BOLD}        ╚████╔╝ ██║███████╗╚███╔███╔╝          {RESET}
{CYAN}{BOLD}         ╚═══╝  ╚═╝╚══════╝ ╚══╝╚══╝           {RESET}
{DIM}  Local family tree viewer & editor{RESET}
"""

APP_URL = "http://localhost:5001"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _python():
    """Return the current Python executable path."""
    return sys.executable


def _check_deps():
    """Return True if all requirements are already importable."""
    try:
        import fasthtml   # noqa: F401
        import multipart  # noqa: F401
        return True
    except ImportError:
        return False


def _install_deps():
    step("Installing dependencies…")
    req = os.path.join(os.path.dirname(__file__), "requirements.txt")
    result = subprocess.run(
        [_python(), "-m", "pip", "install", "-r", req, "--quiet"],
        capture_output=False,
    )
    if result.returncode != 0:
        err("pip install failed — check the output above.")
        sys.exit(1)
    ok("Dependencies installed.")


def _ensure_photos_dir():
    path = os.path.join(os.path.dirname(__file__), "static", "photos")
    os.makedirs(path, exist_ok=True)


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_setup(args):
    print(BANNER)
    step("Setting up FamilyView…")

    # Python version check
    if sys.version_info < (3, 9):
        err(f"Python 3.9+ required (you have {sys.version.split()[0]})")
        sys.exit(1)
    ok(f"Python {sys.version.split()[0]}")

    if _check_deps():
        ok("Dependencies already installed.")
    else:
        _install_deps()

    _ensure_photos_dir()
    ok("Static directories ready.")

    print()
    print(f"  {GREEN}{BOLD}All done!{RESET} Run {CYAN}python3 cli.py start{RESET} to launch the app.")
    print()


def cmd_start(args):
    print(BANNER)

    if not _check_deps():
        warn("Dependencies not installed. Running setup first…")
        cmd_setup(args)

    _ensure_photos_dir()

    step("Starting FamilyView…")
    info(f"Server → {CYAN}{APP_URL}{RESET}")
    info("Press  Ctrl+C  to stop.\n")

    if args.open:
        # Give the server a moment to bind before opening the browser
        import threading
        def _open():
            time.sleep(1.5)
            webbrowser.open(APP_URL)
        threading.Thread(target=_open, daemon=True).start()

    main_py = os.path.join(os.path.dirname(__file__), "main.py")
    try:
        subprocess.run([_python(), main_py], check=True)
    except KeyboardInterrupt:
        print(f"\n\n  {DIM}Server stopped. Goodbye!{RESET}\n")
    except subprocess.CalledProcessError as e:
        err(f"App exited with code {e.returncode}")
        sys.exit(e.returncode)


def cmd_open(_args):
    info(f"Opening {APP_URL} in your browser…")
    webbrowser.open(APP_URL)


def cmd_close(_args):
    import signal
    result = subprocess.run(
        ["lsof", "-ti", "tcp:5001"], capture_output=True, text=True
    )
    pids = result.stdout.strip().splitlines()
    if not pids:
        warn("No FamilyView server found on port 5001.")
        return
    for pid in pids:
        try:
            os.kill(int(pid), signal.SIGTERM)
        except ProcessLookupError:
            pass
    ok(f"Server stopped (PID {', '.join(pids)}).")


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        prog="cli.py",
        description="FamilyView — local family tree app",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""\
commands:
  setup   Install dependencies and prepare the environment
  start   Start the web server  (default if no command given)
  open    Open the app in your browser (server must already be running)
  close   Stop the running server

examples:
  python3 cli.py setup
  python3 cli.py start
  python3 cli.py start --open
  python3 cli.py close
""",
    )
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("setup", help="Install deps and prepare environment")

    p_start = sub.add_parser("start", help="Start the web server")
    p_start.add_argument(
        "--open", action="store_true", help="Open the browser automatically"
    )

    sub.add_parser("open", help="Open the app URL in your default browser")
    sub.add_parser("close", help="Stop the running server")

    args = parser.parse_args()

    # Default to `start` when no sub-command given
    if args.command is None:
        args.command = "start"
        args.open = False

    dispatch = {"setup": cmd_setup, "start": cmd_start, "open": cmd_open, "close": cmd_close}
    dispatch[args.command](args)


if __name__ == "__main__":
    main()
