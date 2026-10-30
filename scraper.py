"""
scraper.py - collects book information from the public HTML pages of
Project Gutenberg (https://www.gutenberg.org/ebooks/<number>).
No API, no login. Only /ebooks/search is disallowed in their robots.txt;
we never touch it, we only open individual book pages.

Quick check from the terminal (run this FIRST on your PC):
    python scraper.py 84 1342 11
It prints every field it found and warns about empty ones.

If the website ever answers with a bot-check page, the scraper stops with a
clear message. It does NOT try to get around that check.
"""
import csv
import os
import random
import re
import sys
import threading
import time

import requests
from bs4 import BeautifulSoup

from schema import FIELDS

BASE_URL = "https://www.gutenberg.org/ebooks"
MAX_EBOOK_ID = 80000          # ids above the real maximum just return 404 and are skipped
REQUEST_HEADERS = {"User-Agent": "BookVault/1.0 (university DSA course project)"}


class BotChallenge(Exception):
    """Website blocked us or returned a bot-check page instead of the book page."""


class NetworkProblem(Exception):
    """Internet down / server error after several retries."""


def is_bot_challenge(html):
    low = html.lower()
    return ("ai scrapers break the web" in low or "i challenge thee" in low
            or ("anubis" in low and "javascript" in low)
            or "enable javascript and cookies" in low)


# ------------------------------------------------------------------ parsing
def _text(el):
    return " ".join(el.get_text(" ").split()) if el else ""


def parse_book_page(html, ebook_id=""):
    """HTML of one book page -> dict with all FIELDS (None if it is not a book page)."""
    if is_bot_challenge(html):
        raise BotChallenge("The website returned a bot-check page")
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table", class_="bibrec")
    if table is None:
        return None

    rec = {f: "" for f in FIELDS}
    subjects, languages = [], []
    for tr in table.find_all("tr"):
        th, td = tr.find("th"), tr.find("td")
        if not th or not td:
            continue
        label, value = _text(th).lower(), _text(td)
        if not value:
            continue
        if label in ("author", "creator"):
            if not rec["author"]:                 # first author only
                rec["author"] = value
        elif label == "title":
            rec["title"] = value
        elif label == "language":
            languages.append(value)
        elif label.startswith("loc class"):
            rec["loc_class"] = value
        elif label.startswith("subject"):
            subjects.append(value)
        elif label == "category":
            rec["category"] = value
        elif label.startswith("ebook"):
            m = re.search(r"\d+", value)
            if m:
                rec["ebook_no"] = m.group(0)
        elif label.startswith("release date"):
            rec["release_date"] = value
            m = re.search(r"(\d{4})", value)
            if m:
                rec["release_year"] = int(m.group(1))
        elif label.startswith("last update") or label.startswith("most recent"):
            rec["last_update"] = value
        elif label.startswith("copyright"):
            rec["copyright"] = value
        elif label.startswith("download"):
            m = re.search(r"([\d,]+)", value)
            if m:
                rec["downloads_30d"] = int(m.group(1).replace(",", ""))
        elif label.startswith("reading"):
            m = re.search(r"score:\s*([\d.]+)", value)
            if m:
                rec["reading_ease"] = float(m.group(1))

    if not rec["title"]:
        rec["title"] = _text(soup.find("h1"))
    if not rec["ebook_no"]:
        rec["ebook_no"] = str(ebook_id)
    if not rec["title"] or not rec["ebook_no"]:
        return None
    rec["language"] = "; ".join(languages)
    rec["subjects"] = "; ".join(subjects)
    rec["subject_count"] = len(subjects)
    return rec


# --------------------------------------------------------------- networking
def fetch_html(session, url, retries=3):
    """Page text, or None if the page does not exist (404)."""
    for attempt in range(retries):
        try:
            r = session.get(url, timeout=20)
        except requests.RequestException:
            time.sleep(1 + attempt)
            continue
        if r.status_code == 404 or r.status_code == 410:
            return None
        if r.status_code == 403:
            raise BotChallenge("The website refused the request (HTTP 403)")
        if r.status_code in (429, 500, 502, 503, 504):
            time.sleep(2 * (attempt + 1))
            continue
        if r.status_code == 200:
            return r.text
        return None
    raise NetworkProblem("Could not reach the website")


def fetch_book(session, ebook_id):
    html = fetch_html(session, f"{BASE_URL}/{ebook_id}")
    return parse_book_page(html, ebook_id) if html else None


def new_session():
    s = requests.Session()
    s.headers.update(REQUEST_HEADERS)
    return s


# ------------------------------------------------------------ CSV helpers
def read_csv(path):
    if not os.path.exists(path):
        return []
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv(path, rows):
    """Rewrite the whole file (used by CRUD). Temp file first, so a crash can't corrupt data."""
    tmp = path + ".tmp"
    with open(tmp, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    os.replace(tmp, path)


# -------------------------------------------------------------- controller
class ScraperController:
    """Runs scraping in background threads with start / pause / resume / stop.

    Callbacks (called from worker threads):
        on_progress(done, target)   on_log(text)   on_finished(reason)
    """

    def __init__(self, csv_path, target, on_progress, on_log, on_finished, workers=5):
        self.csv_path = csv_path
        self.target = target
        self.on_progress = on_progress
        self.on_log = on_log
        self.on_finished = on_finished
        self.workers = workers
        self._running = threading.Event()     # set = working, cleared = paused
        self._stop = threading.Event()
        self._lock = threading.Lock()
        self.count = 0
        self.blocked = False
        self.net_errors = 0
        self.ids = []
        self.pos = 0

    # --- controls used by the UI buttons
    def start(self):
        self._running.set()
        threading.Thread(target=self._manager, daemon=True).start()

    def pause(self):
        self._running.clear()

    def resume(self):
        self._running.set()

    def stop(self):
        self._stop.set()
        self._running.set()                   # wake up paused workers so they can exit

    # --- internals
    def _manager(self):
        reason = "finished"
        try:
            existing = read_csv(self.csv_path)
            self.count = len(existing)
            done_ids = {str(r["ebook_no"]) for r in existing}
            self.on_progress(self.count, self.target)

            ids = [str(i) for i in range(1, MAX_EBOOK_ID + 1) if str(i) not in done_ids]
            random.Random(42).shuffle(ids)        # mix old and new books, not 1,2,3...
            self.ids = ids
            self.on_log(f"Starting {self.workers} workers...")

            new_file = not os.path.exists(self.csv_path) or os.path.getsize(self.csv_path) == 0
            with open(self.csv_path, "a", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
                if new_file:
                    writer.writeheader()
                threads = [threading.Thread(target=self._worker, args=(writer, f), daemon=True)
                           for _ in range(self.workers)]
                for t in threads:
                    t.start()
                for t in threads:
                    t.join()
            if self.blocked:
                reason = "blocked"
            elif self.net_errors >= 20:
                reason = "error"
            elif self._stop.is_set():
                reason = "stopped"
            elif self.count < self.target:
                reason = "ran out of books"
        except Exception as e:
            self.on_log(f"Error: {e}")
            reason = "error"
        self.on_finished(reason)

    def _worker(self, writer, fileobj):
        session = new_session()
        while not self._stop.is_set():
            if not self._running.wait(timeout=0.5):
                continue                           # paused
            with self._lock:
                if self.count >= self.target or self.pos >= len(self.ids):
                    return
                ebook_id = self.ids[self.pos]
                self.pos += 1
            try:
                rec = fetch_book(session, ebook_id)
                self.net_errors = 0
            except BotChallenge as e:
                self.blocked = True
                self.on_log(f"{e}. Scraping stopped.")
                self._stop.set()
                return
            except NetworkProblem:
                self.net_errors += 1
                if self.net_errors >= 20:
                    self.on_log("Too many network errors. Check your internet connection.")
                    self._stop.set()
                    return
                continue
            except Exception as e:
                self.on_log(f"book {ebook_id}: {e}")
                continue
            time.sleep(0.1)                        # be polite to the server
            if not rec:
                continue
            with self._lock:
                if self.count >= self.target:
                    return
                writer.writerow(rec)
                fileobj.flush()
                self.count += 1
                done = self.count
            self.on_progress(done, self.target)


def scrape_single_url(url, csv_path):
    """Bonus: scrape ONE book page given as URL and add it to the CSV."""
    m = re.match(r"https?://(?:www\.)?gutenberg\.org/ebooks/(\d+)", url.strip())
    if not m:
        raise ValueError("URL must look like https://www.gutenberg.org/ebooks/84")
    try:
        rec = fetch_book(new_session(), m.group(1))
    except NetworkProblem:
        raise ValueError("Page could not be downloaded (check internet)")
    if not rec:
        raise ValueError("That page is not a normal book page")
    rows = read_csv(csv_path)
    if any(str(r["ebook_no"]) == str(rec["ebook_no"]) for r in rows):
        raise ValueError(f"eBook #{rec['ebook_no']} already exists in the data")
    rows.append(rec)
    write_csv(csv_path, rows)
    return rec


if __name__ == "__main__":
    session = new_session()
    for book_id in sys.argv[1:] or ["84"]:
        try:
            rec = fetch_book(session, book_id)
        except BotChallenge as e:
            print(f"{book_id}: {e}")
            continue
        except NetworkProblem as e:
            print(f"{book_id}: {e}")
            continue
        if not rec:
            print(f"{book_id}: no book data found")
            continue
        print("-" * 60)
        for k, v in rec.items():
            print(f"{k:15}: {str(v)[:90]}")
        empty = [k for k, v in rec.items() if v == ""]
        if empty:
            print("WARNING empty fields:", ", ".join(empty))
