import argparse
import json
import subprocess
import sys
import datetime as dt
from pathlib import Path

PYTHON = r"C:\Users\Administrator\.conda\envs\yolov8\python.exe"
SCRIPT = r"C:\Users\Administrator\Desktop\Openclaw_codex\ark_seedance_video.py"
CONCAT_SCRIPT = r"C:\Users\Administrator\Desktop\Openclaw_codex\ffmpeg_concat_jimeng.py"
NOTIFY_SCRIPT = r"C:\Users\Administrator\Desktop\Openclaw_codex\notify_popup.py"
DEFAULT_OUTPUT_DIR = r"A:\OpenClaw_Data\jimeng\ark-batch"
DEFAULT_MODEL = "doubao-seedance-1-5-pro-251215"


def popup_notify(title: str, message: str) -> None:
    try:
        subprocess.Popen([PYTHON, NOTIFY_SCRIPT, title, message], creationflags=0x08000000)
    except Exception:
        pass


def write_progress(progress_file: Path, data: dict) -> None:
    data["updated_at"] = dt.datetime.now().isoformat()
    progress_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def run_segment(segment: dict, model: str, output_dir: str) -> int:
    cmd = [
        PYTHON,
        SCRIPT,
        "--model", model,
        "--title", segment["title"],
        "--prompt", segment["prompt"],
        "--ratio", segment.get("ratio", "9:16"),
        "--duration", str(segment.get("duration", 10)),
        "--resolution", segment.get("resolution", "720p"),
        "--seed", str(segment.get("seed", 11)),
        "--output-dir", output_dir,
    ]
    if segment.get("camera_fixed"):
        cmd.append("--camera-fixed")
    if segment.get("watermark"):
        cmd.append("--watermark")
    if segment.get("generate_audio"):
        cmd.append("--generate-audio")
    for url in segment.get("image_urls", []):
        cmd.extend(["--image-url", url])

    print(f"\n=== RUN SEGMENT: {segment['title']} ===")
    return subprocess.call(cmd)


def run_concat(input_dir: str, output_path: str) -> int:
    cmd = [PYTHON, CONCAT_SCRIPT, "--input-dir", input_dir, "--output", output_path]
    print(f"\n=== CONCAT: {output_path} ===")
    return subprocess.call(cmd)


def main() -> None:
    parser = argparse.ArgumentParser(description="Batch runner for Ark Seedance story generation")
    parser.add_argument("--config", required=True)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--output-dir", help="Directory to save segment videos")
    parser.add_argument("--concat", action="store_true")
    parser.add_argument("--concat-output", help="Final merged output path")
    args = parser.parse_args()

    config_path = Path(args.config)
    data = json.loads(config_path.read_text(encoding="utf-8"))
    project = data.get("project", "ark-story")
    segments = data.get("segments", [])
    if not segments:
        raise SystemExit("No segments found in config.")

    output_dir = args.output_dir or str(Path(DEFAULT_OUTPUT_DIR) / project.replace(" ", "-").lower())
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    progress_file = Path(output_dir) / "progress.json"
    total = len(segments)

    print(f"=== ARK SEEDANCE BATCH RUNNER ===")
    print(f"project={project}")
    print(f"model={args.model}")
    print(f"segments={total}")
    print(f"output_dir={output_dir}")
    print(f"progress_file={progress_file}")

    results = []
    write_progress(progress_file, {
        "project": project,
        "model": args.model,
        "total_segments": total,
        "completed": 0,
        "current_segment": segments[0]["title"],
        "status": "starting",
        "results": results,
    })

    for idx, segment in enumerate(segments, start=1):
        write_progress(progress_file, {
            "project": project,
            "model": args.model,
            "total_segments": total,
            "completed": idx - 1,
            "current_segment": segment["title"],
            "status": f"generating {idx}/{total}",
            "results": results,
        })

        code = run_segment(segment, args.model, output_dir)
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
                "model": args.model,
                "total_segments": total,
                "completed": idx - 1,
                "current_segment": segment["title"],
                "status": f"FAILED at segment {idx}/{total}",
                "results": results,
            })
            popup_notify("Ark Seedance Failed", f"❌ Segment {idx}/{total} failed\n{segment['title']}")
            raise SystemExit(f"Segment {idx} failed: {segment['title']}")

        print(f"\n>>> SEGMENT {idx}/{total} DONE: {segment['title']}")
        popup_notify(f"Ark Seedance {idx}/{total}", f"✅ {segment['title']} done")

    write_progress(progress_file, {
        "project": project,
        "model": args.model,
        "total_segments": total,
        "completed": total,
        "current_segment": "",
        "status": "all_segments_done",
        "results": results,
    })
    print(f"\nALL {total} SEGMENTS DONE")
    popup_notify("Ark Seedance Batch", f"🎬 All {total} segments generated!")

    if args.concat:
        concat_output = args.concat_output or str(Path(output_dir).parent / f"{Path(output_dir).name}-final.mp4")
        code = run_concat(output_dir, concat_output)
        if code == 0:
            write_progress(progress_file, {
                "project": project,
                "model": args.model,
                "total_segments": total,
                "completed": total,
                "current_segment": "",
                "status": "concat_done",
                "concat_output": concat_output,
                "results": results,
            })
            print(f"\nFINAL_VIDEO={concat_output}")
            popup_notify("Ark Seedance Final", f"🎉 Final video ready!\n{concat_output}")
        else:
            write_progress(progress_file, {
                "project": project,
                "model": args.model,
                "total_segments": total,
                "completed": total,
                "current_segment": "",
                "status": "concat_failed",
                "results": results,
            })
            popup_notify("Ark Seedance Final", "❌ Concat failed")
            raise SystemExit("Concat failed.")

    print(f"\nPROGRESS_FILE={progress_file}")


if __name__ == "__main__":
    main()
