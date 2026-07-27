#!/usr/bin/env python3
"""Incrementally download and combine the current BAAQMD rule PDFs."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import shutil
import sys
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit

import requests
from playwright.sync_api import sync_playwright
from pypdf import PdfReader, PdfWriter


DEFAULT_CONFIG = Path(__file__).with_name("config.json")
USER_AGENT = "BAAQMD-Current-Rules-Updater/1.0"


@dataclass
class Rule:
    order: int
    code: str
    title: str
    url: str

    @property
    def filename(self) -> str:
        return f"{self.code}.pdf"


def log(message: str) -> None:
    print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {message}", flush=True)


def load_config(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as stream:
        config = json.load(stream)
    raw_output = os.path.expandvars(os.path.expanduser(config["output_folder"]))
    config["output_folder"] = str(Path(raw_output).resolve())
    return config


def load_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"rules": {}, "table_signature": None}
    try:
        with path.open(encoding="utf-8") as stream:
            return json.load(stream)
    except (json.JSONDecodeError, OSError):
        log("Existing state file is unreadable; performing a safe full check.")
        return {"rules": {}, "table_signature": None}


def save_json_atomic(path: Path, value: Any) -> None:
    temp = path.with_suffix(path.suffix + ".tmp")
    with temp.open("w", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, ensure_ascii=True)
    temp.replace(path)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def extract_rule_code(url: str) -> str | None:
    name = Path(urlsplit(url).path).name
    match = re.search(r"(?:rg|fr)[_-]?(\d{4})", name, flags=re.IGNORECASE)
    return f"RG{match.group(1)}" if match else None


def discover_rules(page_url: str, timeout_seconds: int) -> list[Rule]:
    """Render the JavaScript table and return one current PDF per rule."""
    log("Loading the BAAQMD Current Rules table...")
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(user_agent=USER_AGENT)
        page.goto(page_url, wait_until="domcontentloaded", timeout=timeout_seconds * 1000)
        page.wait_for_function(
            """() => {
                const links = [...document.querySelectorAll('table a[href]')];
                return links.filter(a => /\\.pdf(?:$|\\?)/i.test(a.href)).length >= 100;
            }""",
            timeout=timeout_seconds * 1000,
        )
        links = page.eval_on_selector_all(
            "table a[href]",
            """els => els.map(a => ({
                title: (a.innerText || a.textContent || '').trim(),
                url: a.href
            })).filter(x => /\\.pdf(?:$|\\?)/i.test(x.url))""",
        )
        browser.close()

    unique_by_url: dict[str, dict[str, str]] = {}
    for link in links:
        unique_by_url.setdefault(link["url"], link)

    rules: list[Rule] = []
    seen_codes: set[str] = set()
    for link in unique_by_url.values():
        code = extract_rule_code(link["url"])
        if not code:
            log(f"WARNING: Skipping PDF with no recognizable RG number: {link['url']}")
            continue
        if code in seen_codes:
            raise RuntimeError(f"Duplicate current-table entry for {code}")
        seen_codes.add(code)
        rules.append(
            Rule(
                order=len(rules) + 1,
                code=code,
                title=link["title"] or code,
                url=link["url"],
            )
        )

    if len(rules) < 100:
        raise RuntimeError(f"Only {len(rules)} unique rules were found; refusing to update.")
    log(f"Found {len(rules)} current rules.")
    return rules


def url_without_query(url: str) -> str:
    parts = urlsplit(url)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))


def local_file_is_valid(path: Path, expected_hash: str | None) -> bool:
    if not path.is_file() or path.stat().st_size < 5:
        return False
    with path.open("rb") as stream:
        if stream.read(5) != b"%PDF-":
            return False
    return not expected_hash or sha256_file(path) == expected_hash


def remote_appears_unchanged(
    session: requests.Session,
    rule: Rule,
    prior: dict[str, Any],
    local_path: Path,
    timeout_seconds: int,
) -> bool:
    if prior.get("url") != rule.url:
        return False
    if not local_file_is_valid(local_path, prior.get("sha256")):
        return False

    try:
        response = session.head(
            rule.url, allow_redirects=True, timeout=timeout_seconds
        )
        response.raise_for_status()
    except requests.RequestException:
        # The CMS revision token is content-addressed in normal BAAQMD links.
        return "rev=" in rule.url

    current_etag = response.headers.get("ETag")
    current_modified = response.headers.get("Last-Modified")
    if prior.get("etag") and current_etag:
        return prior["etag"] == current_etag
    if prior.get("last_modified") and current_modified:
        return prior["last_modified"] == current_modified
    return "rev=" in rule.url


def download_pdf(
    session: requests.Session,
    rule: Rule,
    destination: Path,
    timeout_seconds: int,
) -> dict[str, Any]:
    """Download to a temporary file, validate it, then replace atomically."""
    attempts = [rule.url]
    clean_url = url_without_query(rule.url)
    if clean_url != rule.url:
        attempts.append(clean_url)

    last_error: Exception | None = None
    for attempt_url in attempts:
        temp = destination.with_suffix(".pdf.download")
        try:
            with session.get(
                attempt_url, stream=True, timeout=timeout_seconds, allow_redirects=True
            ) as response:
                response.raise_for_status()
                digest = hashlib.sha256()
                with temp.open("wb") as stream:
                    for chunk in response.iter_content(chunk_size=1024 * 1024):
                        if chunk:
                            stream.write(chunk)
                            digest.update(chunk)
                with temp.open("rb") as stream:
                    if stream.read(5) != b"%PDF-":
                        raise ValueError("The downloaded file is not a valid PDF.")
                PdfReader(temp)  # Structural validation before replacement.
                temp.replace(destination)
                return {
                    "sha256": digest.hexdigest(),
                    "bytes": destination.stat().st_size,
                    "etag": response.headers.get("ETag"),
                    "last_modified": response.headers.get("Last-Modified"),
                    "download_url": attempt_url,
                }
        except (requests.RequestException, OSError, ValueError) as exc:
            last_error = exc
            temp.unlink(missing_ok=True)
    raise RuntimeError(f"Could not download {rule.code}: {last_error}")


def write_index(path: Path, rules: list[Rule], state_rules: dict[str, Any]) -> None:
    temp = path.with_suffix(".csv.tmp")
    fields = [
        "Table Order",
        "Rule Code",
        "Rule Title",
        "Filename",
        "Official Source URL",
        "Pages",
        "Last Downloaded",
        "SHA256",
    ]
    with temp.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for rule in rules:
            item = state_rules[rule.code]
            writer.writerow(
                {
                    "Table Order": rule.order,
                    "Rule Code": rule.code,
                    "Rule Title": rule.title,
                    "Filename": rule.filename,
                    "Official Source URL": rule.url,
                    "Pages": item["pages"],
                    "Last Downloaded": item["downloaded_at"],
                    "SHA256": item["sha256"],
                }
            )
    temp.replace(path)


def rebuild_combined(
    combined_path: Path, rules: list[Rule], pdf_folder: Path
) -> tuple[int, int]:
    log("Rebuilding the combined bookmarked PDF...")
    writer = PdfWriter()
    total_pages = 0
    for rule in rules:
        source = pdf_folder / rule.filename
        reader = PdfReader(source)
        start_page = total_pages
        for page in reader.pages:
            writer.add_page(page)
            total_pages += 1
        writer.add_outline_item(f"{rule.code} - {rule.title}", start_page)

    writer.add_metadata(
        {
            "/Title": "BAAQMD Current Rules - Combined",
            "/Subject": "Current BAAQMD rules in Current Rules table order",
            "/Author": "Bay Area Air Quality Management District",
        }
    )
    temp = combined_path.with_suffix(".pdf.tmp")
    with temp.open("wb") as stream:
        writer.write(stream)
    check = PdfReader(temp)
    if len(check.pages) != total_pages or len(check.outline) != len(rules):
        temp.unlink(missing_ok=True)
        raise RuntimeError("Combined PDF verification failed.")
    temp.replace(combined_path)
    log(f"Combined PDF rebuilt: {total_pages} pages, {len(rules)} bookmarks.")
    return total_pages, len(rules)


def append_change_log(path: Path, changes: list[str]) -> None:
    with path.open("a", encoding="utf-8") as stream:
        stream.write(f"\n[{datetime.now():%Y-%m-%d %H:%M:%S}]\n")
        if changes:
            for change in changes:
                stream.write(f"- {change}\n")
        else:
            stream.write("- No rule changes detected.\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument(
        "--force",
        action="store_true",
        help="Redownload every PDF and rebuild all outputs.",
    )
    args = parser.parse_args()

    config = load_config(args.config)
    output = Path(config["output_folder"])
    pdf_folder = output / "Rules"
    archive_folder = output / "Archive"
    output.mkdir(parents=True, exist_ok=True)
    pdf_folder.mkdir(exist_ok=True)
    archive_folder.mkdir(exist_ok=True)

    state_path = output / "baaqmd_rules_state.json"
    index_path = output / "BAAQMD_Current_Rules_Index.csv"
    combined_path = output / "BAAQMD_All_Current_Rules_Combined.pdf"
    changes_path = output / "BAAQMD_Change_Log.txt"

    state = load_state(state_path)
    prior_rules: dict[str, Any] = state.get("rules", {})
    rules = discover_rules(config["current_rules_url"], config["timeout_seconds"])

    table_signature = hashlib.sha256(
        json.dumps([asdict(rule) for rule in rules], sort_keys=True).encode()
    ).hexdigest()
    table_changed = table_signature != state.get("table_signature")

    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})
    new_state_rules: dict[str, Any] = {}
    changes: list[str] = []
    content_changed = False

    current_codes = {rule.code for rule in rules}
    removed_codes = sorted(set(prior_rules) - current_codes)
    if removed_codes:
        dated_archive = archive_folder / datetime.now().strftime("%Y-%m-%d")
        dated_archive.mkdir(parents=True, exist_ok=True)
        for code in removed_codes:
            old_pdf = pdf_folder / f"{code}.pdf"
            if old_pdf.exists():
                shutil.move(str(old_pdf), dated_archive / old_pdf.name)
            changes.append(f"REMOVED from current table: {code}")
            content_changed = True

    for rule in rules:
        destination = pdf_folder / rule.filename
        prior = prior_rules.get(rule.code, {})
        unchanged = (
            not args.force
            and remote_appears_unchanged(
                session, rule, prior, destination, config["timeout_seconds"]
            )
        )
        if unchanged:
            new_state_rules[rule.code] = {
                **prior,
                "order": rule.order,
                "title": rule.title,
                "url": rule.url,
                "filename": rule.filename,
            }
            log(f"Unchanged: {rule.code}")
            continue

        existed = destination.exists()
        old_hash = prior.get("sha256")
        log(f"Downloading: {rule.code}")
        download_info = download_pdf(
            session, rule, destination, config["timeout_seconds"]
        )
        reader = PdfReader(destination)
        now = datetime.now().isoformat(timespec="seconds")
        new_state_rules[rule.code] = {
            "order": rule.order,
            "title": rule.title,
            "url": rule.url,
            "filename": rule.filename,
            "pages": len(reader.pages),
            "downloaded_at": now,
            **download_info,
        }
        if not existed:
            changes.append(f"ADDED: {rule.code} - {rule.title}")
            content_changed = True
        elif old_hash != download_info["sha256"]:
            changes.append(f"UPDATED: {rule.code} - {rule.title}")
            content_changed = True
        else:
            log(f"Content hash unchanged after check: {rule.code}")

    # A title or ordering change affects the CSV and PDF bookmarks even if bytes do not.
    metadata_changed = table_changed
    write_index(index_path, rules, new_state_rules)
    if (
        args.force
        or content_changed
        or metadata_changed
        or not combined_path.exists()
    ):
        rebuild_combined(combined_path, rules, pdf_folder)
    else:
        log("No collection changes; combined PDF does not need rebuilding.")

    append_change_log(changes_path, changes)
    save_json_atomic(
        state_path,
        {
            "last_successful_run": datetime.now().isoformat(timespec="seconds"),
            "table_signature": table_signature,
            "rules": new_state_rules,
        },
    )
    log(f"Finished successfully. Output: {output}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        log(f"ERROR: {exc}")
        raise
