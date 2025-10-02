"""
X Scraper that uses Logger from logger.py and Selenium + BeautifulSoup.

Flow per hashtag:
  1. Login
  2. Click Explore icon
  3. Enter hashtag (clearing input first)
  4. Click Latest tab
  5. Scroll/wait until at least 500 tweets are loaded
  6. Capture container HTML (or concatenate tweet outerHTMLs)
  7. Parse HTML into DataFrame and save Parquet
"""

import hashlib
import os
import re
import time
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import pandas as pd
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from logger import Logger, _ln  # local import of your logger

# Default wait constants
WAIT = 18
SCROLL_PAUSE = 0.8
TARGET_PER_TAG = 500
MAX_SCROLLS = 300


class Scraper:
    """
    Scraper class responsible for automating X and extracting tweets.

    Uses Logger for all logging. Scrolling logic ensures at least TARGET_PER_TAG
    tweets are present before capturing HTML.
    """

    def __init__(self, driver_path: str, headless: bool = False):
        """
        Initialize Scraper instance.

        Args:
            driver_path (str): Path to chromedriver.exe
            headless (bool): Run Chrome headless if True
        """
        self.driver_path = Path(driver_path)
        self.headless = headless
        self.logger = Logger()  # No base_path provided
        self.driver = None
        self.logger.log("INFO", "Scraper", "__init__", _ln(), f"Scraper init driver={self.driver_path} headless={self.headless}")

    def start_driver(self):
        """
        Start local ChromeDriver using provided path.

        Returns:
            webdriver.Chrome: Running driver instance

        Raises:
            FileNotFoundError: If chromedriver path does not exist.
        """
        if not self.driver_path.exists():
            self.logger.log("ERROR", "Scraper", "start_driver", _ln(), f"Chromedriver not found at {self.driver_path}")
            raise FileNotFoundError(f"Chromedriver not found at: {self.driver_path}")

        options = webdriver.ChromeOptions()

        if self.headless:
            options.add_argument("--headless=new")

        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--start-maximized")

        service = Service(str(self.driver_path))
        self.driver = webdriver.Chrome(service=service, options=options)
        self.driver.set_window_size(1200, 900)

        self.logger.log("INFO", "Scraper", "start_driver", _ln(), "Chrome driver started")
        return self.driver

    def login(self, username: str, password: str):
        """
        Login to X. Best-effort - does not stop for verification.

        Args:
            username (str): account username/email/phone
            password (str): account password
        """
        self.logger.log("INFO", "Scraper", "login", _ln(), f"Attempting login for {username}")
        driver = self.driver
        driver.get("https://x.com/i/flow/login")

        wait = WebDriverWait(driver, WAIT)

        username_input = None
        candidates = [
            'input[name="text"]',
            'input[autocomplete="username"]',
            'input[placeholder="Phone, email, or username"]',
            'input[aria-label="Phone, email, or username"]',
        ]
        for sel in candidates:
            try:
                username_input = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, sel)))
                if username_input:
                    break
            except Exception:
                username_input = None

        if username_input:
            self.logger.log("INFO", "Scraper", "login", _ln(), "Found username input - typing")
            username_input.click()
            username_input.clear()
            username_input.send_keys(username)
            time.sleep(0.35)
        else:
            self.logger.log("WARNING", "Scraper", "login", _ln(), "Username input not found")

        try:
            next_btn = None
            try:
                next_btn = driver.find_element(By.XPATH, "//span[normalize-space()='Next']/ancestor::button")
            except Exception:
                next_btn = None

            if next_btn:
                self.logger.log("INFO", "Scraper", "login", _ln(), "Clicking Next")
                driver.execute_script("arguments[0].scrollIntoView({block:'center'});", next_btn)
                time.sleep(0.2)
                next_btn.click()
            else:
                if username_input:
                    username_input.send_keys(Keys.ENTER)
                    self.logger.log("INFO", "Scraper", "login", _ln(), "Pressed Enter on username input")
        except Exception as e:
            self.logger.log("ERROR", "Scraper", "login", _ln(), f"Exception during Next click: {e}")

        pw_input = None
        pw_candidates = ['input[name="password"]', 'input[autocomplete="current-password"]', 'input[type="password"]']
        for sel in pw_candidates:
            try:
                pw_input = WebDriverWait(driver, 6).until(EC.presence_of_element_located((By.CSS_SELECTOR, sel)))
                if pw_input:
                    break
            except Exception:
                pw_input = None

        if pw_input:
            self.logger.log("INFO", "Scraper", "login", _ln(), "Found password input - typing")
            pw_input.click()
            pw_input.clear()
            pw_input.send_keys(password)
            time.sleep(0.3)
        else:
            self.logger.log("WARNING", "Scraper", "login", _ln(), "Password input not found")

        try:
            login_btn = None
            try:
                login_btn = driver.find_element(By.CSS_SELECTOR, '[data-testid="LoginForm_Login_Button"]')
            except Exception:
                login_btn = None

            if not login_btn:
                try:
                    login_btn = driver.find_element(By.XPATH, "//span[normalize-space()='Log in']/ancestor::button")
                except Exception:
                    login_btn = None

            if login_btn:
                self.logger.log("INFO", "Scraper", "login", _ln(), "Clicking Log in")
                driver.execute_script("arguments[0].scrollIntoView({block:'center'});", login_btn)
                time.sleep(0.2)
                if login_btn.get_attribute("disabled"):
                    time.sleep(1.2)
                login_btn.click()
            else:
                if pw_input:
                    pw_input.send_keys(Keys.ENTER)
                    self.logger.log("INFO", "Scraper", "login", _ln(), "Pressed Enter on password input")
        except Exception as e:
            self.logger.log("ERROR", "Scraper", "login", _ln(), f"Exception during Log in click: {e}")

        time.sleep(1.0)
        self.logger.log("INFO", "Scraper", "login", _ln(), "Login attempted")

    def click_explore(self) -> bool:
        """
        Click the Explore/Search icon; fall back to navigate /explore.

        Returns:
            bool: True if explore appears available, False otherwise.
        """
        self.logger.log("INFO", "Scraper", "click_explore", _ln(), "Clicking Explore icon")
        driver = self.driver

        def verify_explore():
            try:
                if "/explore" in driver.current_url:
                    return True
                WebDriverWait(driver, 4).until(EC.presence_of_element_located(
                    (By.CSS_SELECTOR, '[data-testid="SearchBox_Search_Input"], input[placeholder="Search"], input[aria-label="Search query"]')
                ))
                return True
            except Exception:
                return False

        try:
            svg_btn = driver.find_element(By.XPATH, "//*[self::button or self::div or self::a][.//svg//path[contains(@d,'M10.25 3.75')]]")
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", svg_btn)
            time.sleep(0.25)
            svg_btn.click()
            time.sleep(1.0)
            if verify_explore():
                self.logger.log("INFO", "Scraper", "click_explore", _ln(), "Clicked search SVG icon")
                return True
        except Exception as e:
            self.logger.log("DEBUG", "Scraper", "click_explore", _ln(), f"SVG click failed: {e}")

        try:
            el = driver.find_element(By.XPATH, "//button[.//span[normalize-space()='Explore']] | //a[.//span[normalize-space()='Explore']]")
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
            time.sleep(0.25)
            el.click()
            time.sleep(1.0)
            if verify_explore():
                self.logger.log("INFO", "Scraper", "click_explore", _ln(), "Clicked Explore text button")
                return True
        except Exception as e:
            self.logger.log("DEBUG", "Scraper", "click_explore", _ln(), f"Explore text click failed: {e}")

        try:
            driver.get("https://x.com/explore")
            time.sleep(1.0)
            if verify_explore():
                self.logger.log("INFO", "Scraper", "click_explore", _ln(), "Navigated to /explore fallback")
                return True
        except Exception as e:
            self.logger.log("ERROR", "Scraper", "click_explore", _ln(), f"Navigate fallback failed: {e}")

        self.logger.log("WARNING", "Scraper", "click_explore", _ln(), "Explore not reachable")
        return False

    def search_hashtag(self, hashtag: str):
        """
        Clear search input then enter hashtag and submit.

        This prevents concatenation of multiple hashtags.
        """
        self.logger.log("INFO", "Scraper", "search_hashtag", _ln(), f"Searching: {hashtag}")
        driver = self.driver
        wait = WebDriverWait(driver, WAIT)

        search_sel = '[data-testid="SearchBox_Search_Input"], [data-testid="searchBox"] input, input[aria-label="Search query"], input[placeholder="Search"]'
        el = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, search_sel)))

        try:
            el.click()
        except Exception:
            pass

        if el.tag_name.lower() != "input":
            try:
                child = el.find_element(By.TAG_NAME, "input")
                el = child
            except Exception:
                pass

        # Clear input robustly to avoid stacking hashtags
        try:
            el.send_keys(Keys.CONTROL, "a")
            time.sleep(0.05)
            el.send_keys(Keys.BACKSPACE)
        except Exception:
            try:
                el.clear()
            except Exception:
                pass

        el.send_keys(hashtag)
        time.sleep(0.35)
        el.send_keys(Keys.ENTER)
        time.sleep(1.0)
        self.logger.log("INFO", "Scraper", "search_hashtag", _ln(), "Search submitted")

    def click_latest_tab(self) -> bool:
        """
        Click the 'Latest' tab (f=live) to show live/latest results.

        Returns:
            bool: True if clicked, False otherwise.
        """
        self.logger.log("INFO", "Scraper", "click_latest_tab", _ln(), "Clicking Latest tab")
        driver = self.driver

        try:
            latest = None
            try:
                latest = WebDriverWait(driver, 6).until(
                    EC.element_to_be_clickable((By.XPATH, "//a[contains(@href,'f=live') and (contains(., 'Latest') or .//span[text()='Latest'])]"))
                )
            except Exception:
                latest = None

            if not latest:
                try:
                    latest = driver.find_element(By.XPATH, "//a[.//span[normalize-space()='Latest'] or normalize-space()='Latest']")
                except Exception:
                    latest = None

            if latest:
                driver.execute_script("arguments[0].scrollIntoView({block:'center'});", latest)
                time.sleep(0.2)
                latest.click()
                time.sleep(1.0)
                self.logger.log("INFO", "Scraper", "click_latest_tab", _ln(), "Latest clicked")
                return True
        except Exception as e:
            self.logger.log("DEBUG", "Scraper", "click_latest_tab", _ln(), f"Latest click exception: {e}")

        self.logger.log("WARNING", "Scraper", "click_latest_tab", _ln(), "Latest not clicked")
        return False

    def ensure_min_tweets_loaded(self, min_count: int = TARGET_PER_TAG, max_scrolls: int = MAX_SCROLLS, pause: float = SCROLL_PAUSE) -> int:
        """
        Scroll the feed repeatedly and accumulate unique tweets until at least
        `min_count` unique tweets are present or `max_scrolls` is reached.

        This method creates stable fingerprints for tweets using (in order):
        1. the tweet id extracted from an ancestor link ("/status/<id>")
        2. SHA1 hash of the tweet element's outerHTML as a fallback

        It returns the number of unique tweets seen.

        Args:
            min_count (int): Desired minimum number of unique tweets to load.
            max_scrolls (int): Maximum scroll iterations to attempt.
            pause (float): Seconds to wait after each scroll for content to load.

        Returns:
            int: Number of unique tweets present after scrolling.
        """
        self.logger.log("INFO", "Scraper", "ensure_min_tweets_loaded", _ln(), f"Ensuring at least {min_count} unique tweets loaded")
        driver = self.driver

        seen = set()
        scrolls = 0
        stable_rounds = 0
        last_seen_count = 0

        while scrolls < max_scrolls:
            # collect current tweet elements
            elems = driver.find_elements(By.CSS_SELECTOR, '[data-testid="tweet"]')
            # fingerprint each and add to set
            for el in elems:
                try:
                    # try to extract tweet id from ancestor link containing '/status/'
                    outer_html = el.get_attribute("outerHTML") or ""
                    tweet_id = None
                    # quick regex search for /status/<digits> in the element HTML
                    m = re.search(r"/status/(\d+)", outer_html)
                    if m:
                        tweet_id = m.group(1)
                    else:
                        # fallback: try to locate a link with /status/ using DOM query (robust)
                        try:
                            a_status = el.find_element(By.XPATH, './/a[contains(@href, "/status/")]')
                            href = a_status.get_attribute("href") or ""
                            m2 = re.search(r"/status/(\d+)", href)
                            if m2:
                                tweet_id = m2.group(1)
                        except Exception:
                            tweet_id = None

                    # final fallback: SHA1 of outerHTML
                    if not tweet_id:
                        sha = hashlib.sha1()
                        sha.update(outer_html.encode('utf-8', errors='ignore'))
                        tweet_id = "sha1-" + sha.hexdigest()

                    seen.add(tweet_id)
                except Exception:
                    # on any per-element failure, continue - don't stop the whole loop
                    continue

            # log progress
            current_count = len(seen)
            self.logger.log("DEBUG", "Scraper", "ensure_min_tweets_loaded", _ln(), f"Scroll {scrolls+1}/{max_scrolls} - unique tweets: {current_count}")

            # success condition
            if current_count >= min_count:
                self.logger.log("INFO", "Scraper", "ensure_min_tweets_loaded", _ln(), f"Target reached: {current_count} unique tweets")
                return current_count

            # if no new tweets were added since last iteration, increment stable counter
            if current_count <= last_seen_count:
                stable_rounds += 1
            else:
                stable_rounds = 0

            last_seen_count = current_count

            # if we've gone several rounds with no progress, break early
            if stable_rounds >= 6:
                self.logger.log("WARNING", "Scraper", "ensure_min_tweets_loaded", _ln(), f"No progress after {stable_rounds} rounds; stopping. unique tweets: {current_count}")
                break

            # scroll to last visible tweet to trigger lazy loading
            try:
                if elems:
                    last_el = elems[-1]
                    driver.execute_script("arguments[0].scrollIntoView(true);", last_el)
                else:
                    # fallback: scroll to bottom
                    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            except Exception as e:
                # log and attempt window scroll fallback
                self.logger.log("DEBUG", "Scraper", "ensure_min_tweets_loaded", _ln(), f"Element scroll failed: {e}; using window.scrollTo")
                try:
                    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                except Exception:
                    pass

            # wait a bit for new tweets to load
            time.sleep(pause)

            scrolls += 1

        final_count = len(seen)
        self.logger.log("WARNING", "Scraper", "ensure_min_tweets_loaded", _ln(), f"Stopped after {scrolls} scrolls; unique tweets loaded: {final_count}")
        return final_count

    def grab_entire_div_html(self) -> Optional[str]:
        """
        Grab the outerHTML of the tweets container after ensuring enough tweets are loaded.

        If container doesn't include all tweets, fall back to concatenating
        individual tweet outerHTMLs into a wrapper div and return that.
        """
        self.logger.log("INFO", "Scraper", "grab_entire_div_html", _ln(), "Capturing tweets container HTML")
        driver = self.driver

        # First try to capture container elements
        selectors = [
            "div.css-175oi2r.r-f8sm7e.r-13qz1uu.r-1ye8kvj",
            'div[data-testid="primaryColumn"] div[data-testid="timeline"]',
            'div[role="feed"]',
            'div[aria-label*="Timeline"]',
        ]

        html = None
        for sel in selectors:
            try:
                el = WebDriverWait(driver, 6).until(EC.presence_of_element_located((By.CSS_SELECTOR, sel)))
                outer = el.get_attribute("outerHTML")
                if outer and len(outer) > 50:
                    html = outer
                    self.logger.log("INFO", "Scraper", "grab_entire_div_html", _ln(), f"Captured using selector {sel}")
                    break
            except Exception:
                continue

        # If container found but small, or not found, fallback to concatenating tweets
        tweets = driver.find_elements(By.CSS_SELECTOR, '[data-testid="tweet"]')
        if (not html) or (len(tweets) > 0 and html and html.count("<article") < max(10, len(tweets) // 4)):
            # Build wrapper with all tweet outerHTMLs
            self.logger.log("INFO", "Scraper", "grab_entire_div_html", _ln(), f"Fallback: concatenating {len(tweets)} tweet elements into wrapper")
            parts = ["<div id='x-scraper-wrapper'>"]
            for t in tweets:
                try:
                    parts.append(t.get_attribute("outerHTML") or "")
                except Exception:
                    continue
            parts.append("</div>")
            html = "\n".join(parts)

        if not html:
            self.logger.log("WARNING", "Scraper", "grab_entire_div_html", _ln(), "No HTML captured")
            return None

        return html

    def parse_html_to_df(self, html: str) -> pd.DataFrame:
        """
        Parse captured HTML into a DataFrame of tweet records.

        Returns:
            pd.DataFrame: parsed records
        """
        self.logger.log("INFO", "Scraper", "parse_html_to_df", _ln(), "Parsing HTML")
        soup = BeautifulSoup(html, "lxml")

        tweet_blocks = soup.select('[data-testid="tweet"]')
        if not tweet_blocks:
            tweet_blocks = []
            for div in soup.find_all("div"):
                if div.find("time") and div.find(attrs={"data-testid": "tweetText"}):
                    tweet_blocks.append(div)

        records = []
        for tb in tweet_blocks:
            rec = {
                "tweet_id": None, "display_name": None, "handle": None, "username": None,
                "timestamp_iso": None, "timestamp_relative": None,
                "content": None, "hashtags": [], "mentions": [],
                "reply_count": None, "retweet_count": None, "like_count": None, "view_count": None
            }

            user_block = tb.select_one('[data-testid="User-Name"]')
            if user_block:
                a = user_block.find("a")
                if a:
                    href = a.get("href","")
                    if href:
                        rec["handle"] = href.rstrip("/").split("/")[-1]
                    span = a.find("span")
                    if span:
                        rec["display_name"] = span.get_text(strip=True)
                if not rec["username"] and rec["handle"]:
                    rec["username"] = rec["handle"]

            time_tag = tb.find("time")
            if time_tag:
                rec["timestamp_iso"] = time_tag.get("datetime")
                rec["timestamp_relative"] = time_tag.get_text(strip=True)
                parent_a = time_tag.find_parent("a", href=True)
                if parent_a:
                    href = parent_a.get("href","")
                    if "/status/" in href:
                        rec["tweet_id"] = href.split("/status/")[-1].split("?")[0]

            content_el = tb.find(attrs={"data-testid":"tweetText"})
            if content_el:
                rec["content"] = content_el.get_text(" ", strip=True)
                tags = content_el.find_all("a", href=True)
                for t in tags:
                    href = t.get("href","")
                    txt = t.get_text(strip=True)
                    if href.startswith("/hashtag/") or txt.startswith("#"):
                        rec["hashtags"].append(txt)
                    elif txt.startswith("@"):
                        rec["mentions"].append(txt)
                    else:
                        if re.match(r"^/[^/]+$", href) and not href.startswith("/hashtag"):
                            rec["mentions"].append("@" + href.lstrip("/"))
                rec["hashtags"] = list(dict.fromkeys(rec["hashtags"]))
                rec["mentions"] = list(dict.fromkeys(rec["mentions"]))
            else:
                rec["content"] = tb.get_text(" ", strip=True)

            try:
                reply_btn = tb.select_one('div[role="group"] [data-testid="reply"]')
                rec["reply_count"] = self._parse_count_from_text(reply_btn.get_text(" ", strip=True)) if reply_btn else None
            except Exception:
                rec["reply_count"] = None

            try:
                rt_btn = tb.select_one('div[role="group"] [data-testid="retweet"]')
                rec["retweet_count"] = self._parse_count_from_text(rt_btn.get_text(" ", strip=True)) if rt_btn else None
            except Exception:
                rec["retweet_count"] = None

            try:
                like_btn = tb.select_one('div[role="group"] [data-testid="like"]')
                rec["like_count"] = self._parse_count_from_text(like_btn.get_text(" ", strip=True)) if like_btn else None
            except Exception:
                rec["like_count"] = None

            try:
                view_elem = tb.find(attrs={"aria-label": re.compile(r"view", re.I)})
                if view_elem:
                    vtxt = view_elem.get("aria-label") or view_elem.get_text(" ", strip=True)
                    rec["view_count"] = self._parse_count_from_text(vtxt)
                else:
                    m = re.search(r"([\d,.]+[kKmM]?)\s*views?", tb.get_text(" ", strip=True), re.I)
                    if m:
                        rec["view_count"] = self._shorthand_to_int(m.group(1))
            except Exception:
                rec["view_count"] = None

            records.append(rec)

        df = pd.DataFrame(records)
        self.logger.log("INFO", "Scraper", "parse_html_to_df", _ln(), f"Parsed {len(df)} records")
        return df

    def _shorthand_to_int(self, s: str):
        """
        Convert shorthand numeric strings to integer.

        Args:
            s (str): shorthand string like '1.2K'

        Returns:
            Optional[int]: integer value or None
        """
        if not s:
            return None
        s = s.replace(",", "").strip()
        m = re.match(r"^([\d\.]+)\s*([kKmM]?)$", s)
        if not m:
            try:
                return int(re.sub(r"[^\d]", "", s))
            except Exception:
                return None
        num = float(m.group(1))
        suf = m.group(2).lower()
        if suf == "k":
            return int(num * 1000)
        if suf == "m":
            return int(num * 1000000)
        return int(num)

    def _parse_count_from_text(self, text: str):
        """
        Parse first numeric shorthand from text.

        Returns:
            Optional[int]: integer or None
        """
        if not text:
            return None
        m = re.search(r"([\d,.]+[kKmM]?)", text)
        if m:
            return self._shorthand_to_int(m.group(1))
        return None

    def save_df(self, df: pd.DataFrame, out_path: str):
        """
        Save DataFrame to Parquet.

        Args:
            df (pd.DataFrame): DataFrame to save
            out_path (str): output parquet path
        """
        self.logger.log("INFO", "Scraper", "save_df", _ln(), f"Saving {len(df)} rows to {out_path}")
        df.to_parquet(out_path, index=False)
        self.logger.log("INFO", "Scraper", "save_df", _ln(), "Parquet saved")

    def close(self):
        """
        Quit the Selenium driver if running.
        """
        if self.driver:
            try:
                self.driver.quit()
                self.logger.log("INFO", "Scraper", "close", _ln(), "Driver closed")
            except Exception as e:
                self.logger.log("ERROR", "Scraper", "close", _ln(), f"Error closing driver: {e}")

    def run(self, username: Optional[str], password: Optional[str], hashtags: List[str], per_tag_target: int = TARGET_PER_TAG):
        """
        Execute the full flow for each hashtag and save combined Parquet.

        Args:
            username (Optional[str]): login username
            password (Optional[str]): login password
            hashtags (List[str]): list of hashtags
            per_tag_target (int): how many tweets to attempt to load per tag

        Returns:
            str: Path to saved parquet file
        """
        # Create output directory with today's date
        today = datetime.now().strftime("%d-%m-%Y")
        output_dir = Path("../io") / today
        output_dir.mkdir(parents=True, exist_ok=True)
        
        out_path = output_dir / "tweets.parquet"
        
        self.start_driver()

        try:
            if username and password:
                self.login(username, password)
                self.logger.log("INFO", "Scraper", "run", _ln(), "Login attempted")
            else:
                self.logger.log("INFO", "Scraper", "run", _ln(), "Proceeding as guest")

            ok = self.click_explore()
            if not ok:
                self.logger.log("WARNING", "Scraper", "run", _ln(), "Explore may be unavailable")

            all_dfs = []

            for tag in hashtags:
                self.logger.log("INFO", "Scraper", "run", _ln(), f"Processing {tag}")

                self.search_hashtag(tag)

                latest_ok = self.click_latest_tab()
                if not latest_ok:
                    self.logger.log("WARNING", "Scraper", "run", _ln(), "Latest tab not clicked")

                # Wait + scroll to load tweets
                loaded = self.ensure_min_tweets_loaded(min_count=per_tag_target, max_scrolls=MAX_SCROLLS, pause=SCROLL_PAUSE)
                self.logger.log("INFO", "Scraper", "run", _ln(), f"{loaded} tweets loaded after scrolling for {tag}")

                # Grab HTML after enough tweets loaded
                html = self.grab_entire_div_html()
                if not html:
                    self.logger.log("WARNING", "Scraper", "run", _ln(), f"No HTML for {tag}; skipping")
                    continue

                df = self.parse_html_to_df(html)
                if not df.empty:
                    df["_queried_hashtag"] = tag
                    all_dfs.append(df)
                
                # small pause between tags
                time.sleep(1.0)

            if all_dfs:
                final = pd.concat(all_dfs, ignore_index=True)
                if "tweet_id" in final.columns:
                    final.drop_duplicates(subset=["tweet_id"], inplace=True)
                self.save_df(final, str(out_path))
                return str(out_path)
            else:
                self.logger.log("WARNING", "Scraper", "run", _ln(), "No tweets parsed; writing empty Parquet")
                pd.DataFrame([]).to_parquet(str(out_path), index=False)
                return str(out_path)

        finally:
            self.close()