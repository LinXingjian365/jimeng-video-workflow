import argparse
import json
import subprocess
import sys
import datetime as dt
from pathlib import Path

PYTHON = r"C:\Users\Administrator\.conda\envs\yolov8\python.exe"
SCRIPT = r"C:\Users\Administrator\Desktop\Openclaw_codex\jimeng_video_api_minimal.py"
CONCAT_SCRIPT = r"C:\Users\Administrator\Desktop\Openclaw_codex\ffmpeg_concat_jimeng.py"
NOTIFY_SCRIPT = r"C:\Users\Administrator\Desktop\Openclaw_codex\notify_popup.py"
DEFAULT_OUTPUT_DIR = r"A:\OpenClaw_Data\jimeng"


def popup_notify(title: str, message: str) -> None:
    """Fire a non-blocking popup notification."""
    try:
        subprocess.Popen(
            [PYTHON, NOTIFY_SCRIPT, title, message],
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
        )
    except Exception:
        pass


def write_progress(progress_file: Path, data: dict) -> None:
    data["updated_at"] = dt.datetime.now().isoformat()
    progress_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def run_segment(segment: dict, aspect_ratio: str, frames: int, output_dir: str) -> int:
    cmd = [
        PYTHON,
        SCRIPT,
        "--title", segment["title"],
        "--prompt", segment["prompt"],
        "--aspect-ratio", aspect_ratio,
        "--frames", str(frames),
        "--output-dir", output_dir,
    ]
    print(f"\n=== RUN SEGMENT: {segment['title']} ===")
    return subprocess.call(cmd)


def run_concat(input_dir: str, output_path: str) -> int:
    cmd = [
        PYTHON,
        CONCAT_SCRIPT,
        "--input-dir", input_dir,
        "--output", output_path,
    ]
    print(f"\n=== CONCAT: {output_path} ===")
    return subprocess.call(cmd)


def main() -> None:
    parser = argparse.ArgumentParser(description="Batch runner for Jimeng multi-segment story generation with progress tracking")
    parser.add_argument("--config", required=True, help="Path to segment JSON config")
    parser.add_argument("--output-dir", help="Directory to save segment videos (default: from config or A:\\OpenClaw_Data\\jimeng\\<project>)")
    parser.add_argument("--concat", action="store_true", help="Auto-concat segments after all are generated")
    parser.add_argument("--concat-output", help="Final merged video path (default: <output-dir>-final.mp4)")
    args = parser.parse_args()

    config_path = Path(args.config)
    data = json.loads(config_path.read_text(encoding="utf-8"))
    project = data.get("project", "jimeng-story")
    aspect_ratio = data.get("aspect_ratio", "9:16")
    frames = int(data.get("frames", 121))
    segments = data.get("segments", [])

    if not segments:
        raise SystemExit("No segments found in config.")

    output_dir = args.output_dir or str(Path(DEFAULT_OUTPUT_DIR) / project.replace(" ", "-").lower())
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    progress_file = Path(output_dir) / "progress.json"
    total = len(segments)

    print(f"=== JIMENG BATCH RUNNER ===")
    print(f"project={project}")
    print(f"segments={total}")
    print(f"output_dir={output_dir}")
    print(f"progress_file={progress_file}")

    write_progress(progress_file, {
        "project": project,
        "total_segments": total,
        "completed": 0,
        "current_segment": segments[0]["title"] if segments else "",
        "status": "starting",
        "results": [],
    })

    results = []
    for idx, segment in enumerate(segments, start=1):
        write_progress(progress_file, {
            "project": project,
            "total_segments": total,
            "completed": idx - 1,
            "current_segment": segment["title"],
            "status": f"generating {idx}/{total}",
            "results": results,
        })

        code = run_segment(segment, aspect_ratio, frames, output_dir)
        result_entry = {
            "segment": idx,
            "title": segment["title"],
            "success": code == 0,
            "exit_code": code,
            "finished_at": dt.datetime.now().isoformat(),
        }
        results.append(result_entry)

        if code != 0:
            write_progress(progress_file, {
                "project": project,
                "total_segments": total,
                "completed": idx - 1,
                "current_segment": segment["title"],
                "status": f"FAILED at segment {idx}/{total}",
                "results": results,
            })
            raise SystemExit(f"Segment {idx} failed: {segment['title']}")

        print(f"\n>>> SEGMENT {idx}/{total} DONE: {segment['title']}")
        popup_notify(f"Jimeng {idx}/{total}", f"✅ {segment['title']} done")

    write_progress(progress_file, {
        "project": project,
        "total_segments": total,
        "completed": total,
        "current_segment": "",
        "status": "all_segments_done",
        "results": results,
    })
    print(f"\nALL {total} SEGMENTS DONE")
    popup_notify("Jimeng Batch", f"🎬 All {total} segments generated!")

    if args.concat:
        concat_output = args.concat_output or str(Path(output_dir).parent / f"{Path(output_dir).name}-final.mp4")
        code = run_concat(output_dir, concat_output)
        if code == 0:
            write_progress(progress_file, {
                "project": project,
                "total_segments": total,
                "completed": total,
                "current_segment": "",
                "status": "concat_done",
                "concat_output": concat_output,
                "results": results,
            })
            print(f"\nFINAL_VIDEO={concat_output}")
            popup_notify("Jimeng Final", f"🎉 Final video ready!\n{concat_output}")
        else:
            write_progress(progress_file, {
                "project": project,
                "total_segments": total,
                "completed": total,
                "current_segment": "",
                "status": "concat_failed",
                "results": results,
            })
            raise SystemExit("Concat failed.")

    print(f"\nPROGRESS_FILE={progress_file}")


if __name__ == "__main__":
    main()
