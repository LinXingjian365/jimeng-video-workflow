import argparse
import json
import time
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

EDGE_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
USER_DATA_DIR = r"C:\Users\Administrator\.openclaw\browser\openclaw\user-data"
DEFAULT_OUTPUT_DIR = Path(r"A:\OpenClaw_Data\jimeng\web")


def wait_for_text(page, text: str, timeout_ms: int = 30000):
    page.get_by_text(text, exact=False).wait_for(timeout=timeout_ms)


def open_generate_panel(page):
    page.goto("https://jimeng.jianying.com/ai-tool/video/generate", wait_until="domcontentloaded")
    wait_for_text(page, "即梦AI", 60000)
    # Home shell often redirects here. Click the video generation entry if needed.
    if "ai-tool/home" in page.url:
        try:
            page.get_by_text("视频生成", exact=False).click(timeout=10000)
        except Exception:
            pass
    page.wait_for_timeout(2000)


def fill_prompt(page, prompt: str):
    prose = page.locator(".ProseMirror").first
    prose.click()
    page.keyboard.press("Control+A")
    page.keyboard.press("Backspace")
    prose.fill(prompt)


def set_ratio(page, ratio: str):
    page.get_by_text("16:9", exact=True).or_(page.get_by_text("9:16", exact=True)).first.click()
    page.wait_for_timeout(500)
    page.get_by_role("radio", name=ratio).click(timeout=10000)
    page.wait_for_timeout(500)


def set_duration(page, duration: str):
    current = page.locator('[role="combobox"]').filter(has_text='s').nth(3)
    # fallback: any combobox with duration text
    try:
        current.click(timeout=5000)
    except Exception:
        page.get_by_text("4s", exact=True).click(timeout=5000)
    page.wait_for_timeout(500)
    page.get_by_role("option", name=duration).click(timeout=10000)
    page.wait_for_timeout(500)


def submit(page):
    submit_btn = page.locator("button.submit-button-s4a7XV, button.submit-button-xdhu0e").filter(has_not=page.locator(":disabled")).last
    submit_btn.click(timeout=10000)


def snapshot_status(page):
    body_text = page.locator("body").inner_text(timeout=10000)
    return {
        "url": page.url,
        "text": body_text[:4000]
    }


def main():
    parser = argparse.ArgumentParser(description="Jimeng web automation (member workflow)")
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--ratio", default="9:16")
    parser.add_argument("--duration", default="12s")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--status-only", action="store_true")
    parser.add_argument("--headless", action="store_true")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    progress_path = output_dir / "web_progress.json"

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            USER_DATA_DIR,
            executable_path=EDGE_PATH,
            headless=args.headless,
            viewport={"width": 1440, "height": 1000},
        )
        page = context.pages[0] if context.pages else context.new_page()

        if args.status_only:
            data = snapshot_status(page)
            progress_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            print(json.dumps(data, ensure_ascii=False, indent=2))
            context.close()
            return

        open_generate_panel(page)
        fill_prompt(page, args.prompt)
        set_ratio(page, args.ratio)
        set_duration(page, args.duration)
        submit(page)
        page.wait_for_timeout(3000)
        data = snapshot_status(page)
        progress_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(data, ensure_ascii=False, indent=2))
        context.close()


if __name__ == "__main__":
    main()
