import argparse
import json
import os
import time
from pathlib import Path
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

BASE_URL = "https://ark.cn-beijing.volces.com/api/v3"
DEFAULT_OUTPUT_DIR = Path(r"A:\OpenClaw_Data\jimeng\ark")


def build_session() -> requests.Session:
    session = requests.Session()
    retries = Retry(
        total=5,
        connect=5,
        read=5,
        backoff_factor=1.5,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=frozenset(["GET", "POST"]),
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retries, pool_connections=1, pool_maxsize=1)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def api_headers() -> dict[str, str]:
    api_key = os.environ.get("ARK_API_KEY")
    if not api_key:
        raise SystemExit("Please set ARK_API_KEY first.")
    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
        "Connection": "close",
    }


def create_task(session: requests.Session, model: str, prompt: str, ratio: str, duration: int, resolution: str, seed: int,
                watermark: bool, generate_audio: bool, camera_fixed: bool, image_urls: list[str] | None = None) -> dict[str, Any]:
    content: list[dict[str, Any]] = [{"type": "text", "text": prompt}]
    for url in image_urls or []:
        content.append({"type": "image_url", "image_url": {"url": url}})

    payload = {
        "model": model,
        "content": content,
        "resolution": resolution,
        "ratio": ratio,
        "duration": duration,
        "seed": seed,
        "camera_fixed": camera_fixed,
        "watermark": watermark,
        "generate_audio": generate_audio,
    }
    resp = session.post(f"{BASE_URL}/contents/generations/tasks", headers=api_headers(), json=payload, timeout=120)
    if not resp.ok:
        print("CREATE_STATUS=", resp.status_code)
        print("CREATE_TEXT=", resp.text)
        resp.raise_for_status()
    return resp.json()


def get_task(session: requests.Session, task_id: str) -> dict[str, Any]:
    resp = session.get(f"{BASE_URL}/contents/generations/tasks/{task_id}", headers=api_headers(), timeout=60)
    if not resp.ok:
        print("GET_STATUS=", resp.status_code)
        print("GET_TEXT=", resp.text)
        resp.raise_for_status()
    return resp.json()


def wait_task(session: requests.Session, task_id: str, timeout_seconds: int = 900, poll_seconds: int = 10) -> dict[str, Any]:
    deadline = time.time() + timeout_seconds
    last: dict[str, Any] | None = None
    idx = 0
    consecutive_errors = 0
    while time.time() < deadline:
        idx += 1
        try:
            result = get_task(session, task_id)
            consecutive_errors = 0
        except requests.RequestException as exc:
            consecutive_errors += 1
            print(f"[poll {idx}] query error: {exc} (consecutive_errors={consecutive_errors})")
            if consecutive_errors >= 5:
                raise
            time.sleep(min(poll_seconds + consecutive_errors * 3, 20))
            continue

        last = result
        status = result.get("status") or result.get("data", {}).get("status")
        print(f"[poll {idx}] status={status}")
        if status in {"succeeded", "failed", "expired", "canceled"}:
            return result
        time.sleep(poll_seconds)
    raise TimeoutError(json.dumps(last, ensure_ascii=False))


def extract_video_url(result: dict[str, Any]) -> str | None:
    content = result.get("content") or result.get("data", {}).get("content") or {}
    if isinstance(content, dict):
        return content.get("video_url")
    if isinstance(content, list):
        for item in content:
            if isinstance(item, dict) and item.get("video_url"):
                return item.get("video_url")
    return result.get("video_url")


def download(url: str, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with requests.get(url, stream=True, timeout=120) as r:
        r.raise_for_status()
        with open(out_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)


def main() -> None:
    parser = argparse.ArgumentParser(description="Ark Seedance video generator")
    parser.add_argument("--model", required=True)
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--ratio", default="9:16")
    parser.add_argument("--duration", type=int, default=5)
    parser.add_argument("--resolution", default="720p")
    parser.add_argument("--seed", type=int, default=11)
    parser.add_argument("--watermark", action="store_true")
    parser.add_argument("--generate-audio", action="store_true")
    parser.add_argument("--camera-fixed", action="store_true")
    parser.add_argument("--image-url", action="append", default=[])
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--title", default="ark-seedance-test")
    args = parser.parse_args()

    session = build_session()

    create_result = create_task(
        session=session,
        model=args.model,
        prompt=args.prompt,
        ratio=args.ratio,
        duration=args.duration,
        resolution=args.resolution,
        seed=args.seed,
        watermark=args.watermark,
        generate_audio=args.generate_audio,
        camera_fixed=args.camera_fixed,
        image_urls=args.image_url or None,
    )
    print("CREATE_RESULT=")
    print(json.dumps(create_result, ensure_ascii=False, indent=2))
    task_id = create_result.get("id") or create_result.get("task_id") or create_result.get("data", {}).get("id")
    if not task_id:
        raise SystemExit("No task id found in create result")

    final_result = wait_task(session, task_id)
    print("FINAL_RESULT=")
    print(json.dumps(final_result, ensure_ascii=False, indent=2))
    video_url = extract_video_url(final_result)
    if not video_url:
        raise SystemExit("No video_url found in final result")

    out_path = Path(args.output_dir) / f"{args.title}.mp4"
    download(video_url, out_path)
    print(f"DOWNLOADED_TO={out_path}")


if __name__ == "__main__":
    main()
