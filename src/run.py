"""Windows-friendly equivalent of the Makefile: `python -m src.run <target>`.

Targets: data, features, eda, select, final, app, test (same as `make <target>`).
"""
import subprocess
import sys

PY = sys.executable
TARGETS = {
    "data": [["-m", "src.source_checks"], ["-m", "src.fetch_geo"], ["-m", "src.fetch_power"], ["-m", "src.fetch_nass"],
             ["-m", "src.fetch_context"], ["-m", "src.fetch_nasa_validation"], ["-m", "src.crop_tables"]],
    "features": [["-m", "src.features"], ["-m", "src.calendar"]],
    "eda": [["-m", "src.eda"]],
    "select": [["-m", "src.train"]],
    "final": [["-m", "src.final_eval"], ["-m", "src.diversity_check"]],
    "web-data": [["-m", "src.export_web"]],
    "app": [["-m", "streamlit", "run", "app.py"]],
    "test": [["-m", "pytest", "-q", "tests"]],
}


def main():
    target = sys.argv[1] if len(sys.argv) > 1 else ""
    if target not in TARGETS:
        raise SystemExit(f"usage: python -m src.run [{'|'.join(TARGETS)}]")
    for args in TARGETS[target]:
        print(">>", " ".join(args))
        subprocess.run([PY, *args], check=True)


if __name__ == "__main__":
    main()
