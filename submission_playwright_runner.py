from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Playwright portal autofill runner for Grant")
    parser.add_argument("--grant-id", required=True, help="Grant ID, for example grantsgov_361009")
    parser.add_argument("--portal-url", required=True, help="Portal form URL")
    parser.add_argument(
        "--field-map",
        default="",
        help="Path to orchestrator field map JSON (defaults to output/submission_orchestrator/<grant_id>_field_map.json)",
    )
    parser.add_argument(
        "--selectors",
        default="templates/portal_selectors.example.json",
        help="JSON selector map for target portal",
    )
    parser.add_argument(
        "--screenshot",
        default="output/submission_orchestrator/playwright_filled.png",
        help="Screenshot path after autofill",
    )
    parser.add_argument("--headless", action="store_true", help="Run browser in headless mode")
    parser.add_argument(
        "--confirm-submit",
        action="store_true",
        help="Actually click submit button after autofill (unsafe in production without review)",
    )
    return parser.parse_args()


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _default_field_map_path(root: Path, grant_id: str) -> Path:
    return root / "output" / "submission_orchestrator" / f"{grant_id}_field_map.json"


def _safe_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        return ", ".join(str(item) for item in value)
    return str(value)


def _fill_fields(page: Any, portal_data: dict[str, Any], selectors: dict[str, str]) -> list[str]:
    missing_selectors: list[str] = []
    for key, value in portal_data.items():
        selector = selectors.get(key)
        if not selector:
            missing_selectors.append(key)
            continue
        page.locator(selector).first.fill(_safe_text(value))
    return missing_selectors


def main() -> None:
    args = parse_args()
    root = Path(__file__).resolve().parent

    field_map_path = Path(args.field_map) if args.field_map else _default_field_map_path(root, args.grant_id)
    selectors_path = root / args.selectors
    screenshot_path = root / args.screenshot
    screenshot_path.parent.mkdir(parents=True, exist_ok=True)

    if not field_map_path.exists():
        raise FileNotFoundError(f"Field map not found: {field_map_path}")
    if not selectors_path.exists():
        raise FileNotFoundError(f"Selectors file not found: {selectors_path}")

    field_map = _load_json(field_map_path)
    portal_data = field_map.get("portal_form_map", {})
    selector_config = _load_json(selectors_path)
    selectors = selector_config.get("field_selectors", {})
    submit_selector = selector_config.get("submit_selector", "")

    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:  # pragma: no cover
        raise RuntimeError(
            "Playwright is not installed. Run: pip install playwright && playwright install chromium"
        ) from exc

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=args.headless)
        page = browser.new_page()
        page.goto(args.portal_url, wait_until="domcontentloaded")

        missing = _fill_fields(page, portal_data, selectors)
        page.screenshot(path=str(screenshot_path), full_page=True)

        print(f"Autofill screenshot: {screenshot_path}")
        if missing:
            print(f"Missing selector mapping for fields: {', '.join(missing)}")
        else:
            print("All mapped fields filled.")

        if args.confirm_submit:
            if not submit_selector:
                raise RuntimeError("Submit requested but 'submit_selector' is missing in selectors config")
            page.locator(submit_selector).first.click()
            page.wait_for_timeout(2000)
            post_submit = screenshot_path.with_name(screenshot_path.stem + "_post_submit.png")
            page.screenshot(path=str(post_submit), full_page=True)
            print(f"Submit clicked. Post-submit screenshot: {post_submit}")
        else:
            print("No submit performed. Use --confirm-submit to click submit.")

        browser.close()


if __name__ == "__main__":
    main()
