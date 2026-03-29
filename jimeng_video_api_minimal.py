import argparse
import datetime as dt
import hashlib
import hmac
import json
import os
import re
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

import requests

HOST = "visual.volcengineapi.com"
REGION = "cn-north-1"
SERVICE = "cv"
VERSION = "2022-08-31"
SUBMIT_ACTION = "CVSync2AsyncSubmitTask"
QUERY_ACTION = "CVSync2AsyncGetResult"
REQ_KEY = "jimeng_ti2v_v30_pro"
ENDPOINT = f"https://{HOST}"
DEFAULT_OUTPUT_DIR = Path(r"A:\OpenClaw_Data\jimeng")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def hmac_sha256(key: bytes, msg: str) -> bytes:
    return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()


def slugify(text: str) -> str:
    text = text.strip().lower()
    text = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "-", text)
    text = re.sub(r"-+", "-", text).strip("-")
    return text[:48] or "jimeng-video"


def build_signed_request(access_key: str, secret_key: str, action: str, body: dict[str, Any]) -> tuple[dict[str, str], bytes, str, str, str]:
    payload = json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    payload_hash = sha256_hex(payload)

    now = dt.datetime.utcnow()
    amz_date = now.strftime("%Y%m%dT%H%M%SZ")
    short_date = now.strftime("%Y%m%d")

    canonical_query = urlencode({"Action": action, "Version": VERSION})
    canonical_headers = (
        f"content-type:application/json\n"
        f"host:{HOST}\n"
        f"x-content-sha256:{payload_hash}\n"
        f"x-date:{amz_date}\n"
    )
    signed_headers = "content-type;host;x-content-sha256;x-date"
    canonical_request = "\n".join([
        "POST",
        "/",
        canonical_query,
        canonical_headers,
        signed_headers,
        payload_hash,
    ])

    algorithm = "HMAC-SHA256"
    credential_scope = f"{short_date}/{REGION}/{SERVICE}/request"
    string_to_sign = "\n".join([
        algorithm,
        amz_date,
        credential_scope,
        sha256_hex(canonical_request.encode("utf-8")),
    ])

    k_date = hmac_sha256(secret_key.encode("utf-8"), short_date)
    k_region = hmac.new(k_date, REGION.encode("utf-8"), hashlib.sha256).digest()
    k_service = hmac.new(k_region, SERVICE.encode("utf-8"), hashlib.sha256).digest()
    k_signing = hmac.new(k_service, b"request", hashlib.sha256).digest()
    signature = hmac.new(k_signing, string_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()

    authorization = (
        f"{algorithm} Credential={access_key}/{credential_scope}, "
        f"SignedHeaders={signed_headers}, Signature={signature}"
    )

    headers = {
        "Content-Type": "application/json",
        "Host": HOST,
        "X-Date": amz_date,
        "X-Content-Sha256": payload_hash,
        "Authorization": authorization,
    }
    return headers, payload, canonical_query, canonical_request, string_to_sign


def post_signed(action: str, body: dict[str, Any], access_key: str, secret_key: str) -> dict[str, Any]:
    headers, payload, canonical_query, canonical_request, string_to_sign = build_signed_request(access_key, secret_key, action, body)
    response = requests.post(
        ENDPOINT,
        params={"Action": action, "Version": VERSION},
        headers=headers,
        data=payload,
        timeout=60,
    )
    if not response.ok:
        print("HTTP_STATUS=", response.status_code)
        print("REQUEST_URL=", response.request.url)
        print("REQUEST_HEADERS=")
        print(json.dumps(dict(response.request.headers), ensure_ascii=False, indent=2))
        print("REQUEST_BODY=")
        print(payload.decode("utf-8"))
        print("CANONICAL_QUERY=", canonical_query)
        print("CANONICAL_REQUEST=")
        print(canonical_request)
        print("STRING_TO_SIGN=")
        print(string_to_sign)
        print("RESPONSE_HEADERS=")
        print(json.dumps(dict(response.headers), ensure_ascii=False, indent=2))
        print("RESPONSE_TEXT=")
        print(response.text)
        response.raise_for_status()
    return response.json()


def submit_text_to_video(access_key: str, secret_key: str, prompt: str, image_urls: list[str] | None = None,
                         aspect_ratio: str = "9:16", frames: int = 121, seed: int = -1) -> dict[str, Any]:
    body: dict[str, Any] = {
        "req_key": REQ_KEY,
        "prompt": prompt,
        "seed": seed,
        "frames": frames,
        "aspect_ratio": aspect_ratio,
    }
    if image_urls:
        body["image_urls"] = image_urls
    return post_signed(SUBMIT_ACTION, body, access_key, secret_key)


def query_task(access_key: str, secret_key: str, task_id: str, req_json: dict[str, Any] | None = None) -> dict[str, Any]:
    body: dict[str, Any] = {
        "req_key": REQ_KEY,
        "task_id": task_id,
    }
    if req_json:
        body["req_json"] = json.dumps(req_json, ensure_ascii=False, separators=(",", ":"))
    return post_signed(QUERY_ACTION, body, access_key, secret_key)


def wait_for_video(access_key: str, secret_key: str, task_id: str, timeout_seconds: int = 600,
                   poll_seconds: int = 8) -> dict[str, Any]:
    deadline = time.time() + timeout_seconds
    last_result: dict[str, Any] | None = None
    poll_count = 0
    while time.time() < deadline:
        poll_count += 1
        result = query_task(access_key, secret_key, task_id=task_id)
        last_result = result
        data = result.get("data") or {}
        video_url = data.get("video_url")
        generation_status = data.get("status")
        status = result.get("status") or result.get("code")
        message = result.get("message")
        remaining = max(0, int(deadline - time.time()))
        print(f"[poll {poll_count}] api_status={status} generation_status={generation_status} message={message} remaining={remaining}s")
        if video_url:
            return result
        time.sleep(poll_seconds)
    raise TimeoutError(f"Timed out waiting for video. Last result: {json.dumps(last_result, ensure_ascii=False)}")


def download_file(url: str, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with requests.get(url, stream=True, timeout=120) as r:
        r.raise_for_status()
        with open(output_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)
    return output_path


def build_default_filename(title: str | None, prompt: str) -> str:
    timestamp = dt.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    stem = slugify(title or prompt[:60])
    return f"{timestamp}-{stem}.mp4"


def main() -> None:
    parser = argparse.ArgumentParser(description="Jimeng / Volcengine video API runner")
    parser.add_argument("--prompt", required=True, help="Text prompt for video generation")
    parser.add_argument("--title", help="Optional short title used in output filename")
    parser.add_argument("--aspect-ratio", default="9:16", help="Aspect ratio, e.g. 9:16, 16:9")
    parser.add_argument("--frames", type=int, default=121, help="Frame count")
    parser.add_argument("--seed", type=int, default=-1, help="Seed, default -1")
    parser.add_argument("--image-url", action="append", default=[], help="Optional reference image URL, repeatable")
    parser.add_argument("--timeout-seconds", type=int, default=600, help="Polling timeout")
    parser.add_argument("--poll-seconds", type=int, default=8, help="Polling interval")
    parser.add_argument("--retries", type=int, default=2, help="Retry count for submit step on transient errors")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR), help="Where to save downloaded video")
    parser.add_argument("--no-download", action="store_true", help="Do not download, only print final result")
    args = parser.parse_args()

    access_key = os.environ.get("VOLCENGINE_ACCESS_KEY")
    secret_key = os.environ.get("VOLCENGINE_SECRET_KEY")
    if not access_key or not secret_key:
        raise SystemExit("Please set VOLCENGINE_ACCESS_KEY and VOLCENGINE_SECRET_KEY first.")

    print("=== JIMENG VIDEO RUNNER ===")
    print(f"title={args.title or '(none)'}")
    print(f"aspect_ratio={args.aspect_ratio} frames={args.frames} seed={args.seed}")
    print(f"output_dir={args.output_dir}")
    if args.image_url:
        print(f"image_urls={len(args.image_url)}")

    last_error: Exception | None = None
    submit_result: dict[str, Any] | None = None
    for attempt in range(1, args.retries + 2):
        try:
            print(f"[submit attempt {attempt}] sending request...")
            submit_result = submit_text_to_video(
                access_key,
                secret_key,
                prompt=args.prompt,
                image_urls=args.image_url or None,
                aspect_ratio=args.aspect_ratio,
                frames=args.frames,
                seed=args.seed,
            )
            break
        except requests.RequestException as exc:
            last_error = exc
            print(f"[submit attempt {attempt}] failed: {exc}")
            if attempt >= args.retries + 1:
                raise
            time.sleep(min(3 * attempt, 10))

    if submit_result is None:
        raise SystemExit(f"Submit failed: {last_error}")

    print("SUBMIT_RESULT=")
    print(json.dumps(submit_result, ensure_ascii=False, indent=2))

    task_id = (submit_result.get("data") or {}).get("task_id")
    if not task_id:
        raise SystemExit("No task_id found in submit result.")

    print(f"task_id={task_id}")
    print("[poll] waiting for generated video...")
    final_result = wait_for_video(
        access_key,
        secret_key,
        task_id=task_id,
        timeout_seconds=args.timeout_seconds,
        poll_seconds=args.poll_seconds,
    )
    print("FINAL_RESULT=")
    print(json.dumps(final_result, ensure_ascii=False, indent=2))

    if args.no_download:
        return

    video_url = (final_result.get("data") or {}).get("video_url")
    if not video_url:
        raise SystemExit("No video_url found in final result.")

    output_dir = Path(args.output_dir)
    output_path = output_dir / build_default_filename(args.title, args.prompt)
    print(f"[download] saving to {output_path}")
    download_file(video_url, output_path)
    print(f"DOWNLOADED_TO={output_path}")


if __name__ == "__main__":
    main()
