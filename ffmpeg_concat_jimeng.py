import argparse
import subprocess
from pathlib import Path


def natural_sort_key(path: Path):
    return path.name


def main() -> None:
    parser = argparse.ArgumentParser(description="Concatenate generated Jimeng video segments with ffmpeg")
    parser.add_argument("--input-dir", required=True, help="Directory containing generated mp4 segments")
    parser.add_argument("--output", required=True, help="Final merged mp4 path")
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    files = sorted(input_dir.glob("*.mp4"), key=natural_sort_key)
    if not files:
        raise SystemExit("No mp4 files found.")

    list_file = input_dir / "concat_list.txt"
    with open(list_file, "w", encoding="utf-8") as f:
        for file in files:
            f.write(f"file '{file.as_posix()}'\n")

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        "ffmpeg",
        "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(list_file),
        "-c", "copy",
        str(output_path),
    ]
    print("RUNNING:", " ".join(cmd))
    subprocess.check_call(cmd)
    print(f"MERGED_TO={output_path}")


if __name__ == "__main__":
    main()
