"""Run the synthetic UI probe with bounded diagnostics under xvfb-run."""
import argparse
import os
from pathlib import Path
import signal
import subprocess
import time


def diagnose(process, output, elapsed, stack=False):
    label = f"watchdog-{int(elapsed):03d}s"
    print(f"PHONE_LAYOUT_WATCHDOG {label} pid={process.pid}", flush=True)
    # This captures the test display even when Godot's main thread is stuck.
    with (output / (label + ".log")).open("w") as log:
        commands = [
            ["import", "-window", "root", str(output / (label + ".png"))],
            ["ps", "-p", str(process.pid), "-o", "pid,stat,pcpu,pmem,etime,wchan:30,comm"],
        ]
        if stack:
            commands.append([
                "sudo", "-n", "gdb", "--batch", "-ex", "set pagination off",
                "-ex", "thread apply all bt 12", "-ex", "detach", "-p", str(process.pid),
            ])
        for command in commands:
            try:
                subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, timeout=20, check=False)
            except (OSError, subprocess.TimeoutExpired) as error:
                log.write(str(error) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("binary", type=Path)
    parser.add_argument("project", type=Path)
    args = parser.parse_args()
    output = Path(os.environ["PHONE_LAYOUT_OUTPUT"])
    output.mkdir(parents=True, exist_ok=True)
    process = subprocess.Popen([
        str(args.binary.resolve()), "--editor", "--single-window", "--verbose",
        "--audio-driver", "Dummy", "--rendering-method", "gl_compatibility",
        "--rendering-driver", "opengl3", "--display-driver", "x11",
        "--path", str(args.project.resolve()),
    ], start_new_session=True)
    start = time.monotonic()
    checkpoints = [30, 90]
    try:
        while process.poll() is None:
            elapsed = time.monotonic() - start
            if checkpoints and elapsed >= checkpoints[0]:
                mark = checkpoints.pop(0)
                diagnose(process, output, elapsed, stack=mark == 90)
            if elapsed >= 300:
                print("PHONE_LAYOUT_TIMEOUT: no completed result within 300 seconds", flush=True)
                os.killpg(process.pid, signal.SIGTERM)
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait(timeout=5)
                return 124
            time.sleep(0.5)
        if process.returncode:
            return process.returncode
        if not (output / "geometry.json").is_file():
            print("PHONE_LAYOUT_MISSING_RESULT", flush=True)
            return 1
        return 0
    finally:
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait(timeout=5)


if __name__ == "__main__":
    raise SystemExit(main())
