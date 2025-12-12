# ===========================
# Python Script for Scraping Bilibili AI & Human Cover Song Data
# ===========================
# Description：
# This script automates the acquisition of video-related data on Bilibili 
# (including metadata, danmaku, and user comments) for the comparative study of AI-generated cover songs and human-performed cover songs. 
# The script performs browser automation login, dynamic webpage parsing, 
# candidate video identification, metadata retrieval, danmaku extraction, 
# comment scraping (including nested replies), and final data storage in CSV format.
#===========================

# Import required libraries

import os 
# File path and directory operations
import re
# Regular expressions for text extractio
import time
# Time-related operations (sleep, timestamp)
import random 
# Generate random numbers, used for anti-scraping delays
import json
# Handling JSON data returned by APIs
import pandas as pd 
# Data processing and storage (DataFrame)
import requests 
# HTTP requests to Bilibili API
from datetime import datetime
# Convert timestamps and format date/time
from selenium import webdriver
# Selenium WebDriver for browser automation
from selenium.webdriver.common.by import By
# Locate HTML elements (CSS selector, XPath, etc.)
from selenium.webdriver.chrome.service import Service
# Manage ChromeDriver service
from selenium.webdriver.chrome.options import Options
# Configure Chrome startup options (e.g., headless mode)

# ===========================
# Search & scraping configuration parameters
# ===========================

SONG_TITLE = "悬溺 Ai翻唱"
# Keyword used for Bilibili search
START_DATE = datetime(2023, 1, 1)
# Start date of the time window for valid videos
END_DATE = datetime(2025, 10, 1)
# End date of the time window for valid videos.
MAX_CANDIDATES = 60
# Maximum number of raw candidate videos to collect from the Bilibili 
TARGET_COUNT = 10
# Final number of videos selected for full scraping


RESULT_DIR = "/Users/xujingyu/Desktop/课程资料/5507/11.6.17"
# Directory path where all scraped data
os.makedirs(RESULT_DIR, exist_ok=True)
# Create the directory if it does not already exist. 
# exist_ok=True prevents errors if the folder already exists

# ===========================
# Chrome configuration + launching the Selenium browser
# ===========================
chrome_options = Options()
# Create a Chrome options object for customizing browser behavior.
chrome_options.add_argument("--start-maximized")
# Start Chrome with a maximized window (better for element detection and stability).
service = Service()
# Instantiate the ChromeDriver service manager. This automatically locates the driver.
driver = webdriver.Chrome(service=service, options=chrome_options)
# Launch the Chrome browser using Selenium with the specified options and service.

# ===========================
# Login and Retrieve Cookie
# ===========================

def ensure_login_and_get_cookie_string(driver, timeout_sec=120):
    """
    打开B站主页，等待用户手动登录（建议扫码）；
    检测到 SESSDATA 后，导出整套 Cookie 并拼接为 Cookie 字符串。
    """
# Waits for user login in Selenium and returns the merged cookie string.

    print("🔐 正在打开B站主页，请在弹出的窗口中完成登录（建议扫码）...")
# Notify the user to log in manually; login is required to access restricted comments.
    driver.get("https://www.bilibili.com/")
# Selenium loads Bilibili’s homepage.
    start = time.time()
    sess_ok = False
    # Poll the browser repeatedly to check whether SESSDATA appears within timeout.
    while time.time() - start < timeout_sec:
        try:
            cookies = {c["name"]: c["value"] for c in driver.get_cookies()}
            # Retrieve all cookies from Selenium and convert into a dictionary.
            if "SESSDATA" in cookies:
                sess_ok = True
                break
                 # SESSDATA found → login success → exit polling loop.
        except Exception:
            pass
        time.sleep(2)
         # Wait 2 seconds before checking again to avoid excessive polling.

    if not sess_ok:
        print("⚠️ 未在限定时间内检测到登录（SESSDATA）。仍将继续，但可能抓不到受限评论。")
         # Warning: No login detected → restricted comments may not be collected.
        cookies = {c["name"]: c["value"] for c in driver.get_cookies()}
         # Use whatever cookies exist (likely guest cookies).

    # 将 Selenium cookies 注入到 requests 使用
    cookie_pairs = [f"{k}={v}" for k, v in cookies.items()]
    # Convert each cookie to "key=value" format.
    cookie_string = "; ".join(cookie_pairs)
    # Join all pairs into a single cookie string for HTTP request headers.
    return cookie_string
    # Return the cookie string for future API calls.

# 执行登录并拿到 Cookie
COOKIE_STRING = ensure_login_and_get_cookie_string(driver)
# Execute login function and retrieve the cookie string after login.

# 基础请求头（会在需要时带上 Cookie）
BASE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36",
   # User-Agent mimics a real browser, reducing risk of anti-scraping blocks.

    "Referer": "https://www.bilibili.com/",
   # Some Bilibili APIs require a valid Referer header for access.
  
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}
   # Language preference header.
if COOKIE_STRING:
    BASE_HEADERS["Cookie"] = COOKIE_STRING
    # Attach cookie string so that requests library can perform authenticated API calls.

    
# ===========================
# Open search page and collect candidate videos
# ===========================
search_url = f"https://search.bilibili.com/video?keyword={SONG_TITLE}&order=dm"
driver.get(search_url)
time.sleep(3)
# Build Bilibili search URL using the song keyword.

videos = []
 # List for storing candidate video URLs and BV IDs

def fast_scroll_to_load(driver, max_scrolls=6):
  #Scrolls down multiple times to trigger lazy loading of video items.
    for i in range(max_scrolls):
        driver.execute_script(f"window.scrollTo(0, document.body.scrollHeight*{(i+1)/max_scrolls});")
        time.sleep(random.uniform(1.5, 2.5))
        # Trigger additional scroll events to force rendering of new elements.
        driver.execute_script("window.dispatchEvent(new Event('scroll'));")
        time.sleep(random.uniform(1.5, 2.5))

fast_scroll_to_load(driver)
# Execute scroll to load enough video cards.


elements = driver.find_elements(By.CSS_SELECTOR, ".bili-video-card__info--right")
if not elements:
    elements = driver.find_elements(By.CSS_SELECTOR, ".bili-video-card")
# Locate video card elements (layout may vary across versions).
    
for e in elements:
    try:
        link_elem = e.find_element(By.CSS_SELECTOR, "a")
        url = link_elem.get_attribute("href")
        if url and "BV" in url:
            m = re.search(r"BV[\w]+", url)
            if not m:
                continue
            bvid = m.group(0)
            # Extract video links and parse BV IDs.
            if not any(v["bvid"] == bvid for v in videos):
                videos.append({"url": url, "bvid": bvid})
                 # Avoid duplicates before adding to candidate list.
                if len(videos) >= MAX_CANDIDATES:
                    break
    except Exception:
        continue
         # Stop if we reached the maximum allowed candidates.

print(f"共获取候选视频 {len(videos)} 条。")
# Print number of collected candidate videos.

# ===========================
# Get video metadata
# ===========================

def get_video_info(bvid):
    api_url = f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}"
    # Build API URL for retrieving video metadata
    res = requests.get(api_url, headers=BASE_HEADERS, timeout=10)
    # Send GET request with browser-like headers
    j = res.json()
    # Parse JSON into Python dict
    data = j.get("data", {}) or {}
    # Extract 'data' block safely
    if not data:
        return None
      # Return None if video data is missing or invalid
   

    pages = data.get("pages") or []
    cids = [p.get("cid") for p in pages if p.get("cid")]
    # Extract all content IDs (cids) for multi-part videos.
    if not cids and data.get("cid"):
        cids = [data.get("cid")]
        # If no pages exist, use the single cid provided.

    info = {
        "aid": data.get("aid"),
        "bvid": bvid,
        "cids": cids,
        "title": data.get("title"),
        "pubdate": datetime.fromtimestamp(data.get("pubdate")),
        "view": data.get("stat", {}).get("view"),
        "like": data.get("stat", {}).get("like"),
        "coin": data.get("stat", {}).get("coin"),
        "favorite": data.get("stat", {}).get("favorite"),
        "share": data.get("stat", {}).get("share"),
        "danmaku": data.get("stat", {}).get("danmaku"),
        "reply_count": data.get("stat", {}).get("reply")
    }
    return info
   # Construct structured metadata dictionary.

# ===========================
# Filter videos by publication date and build final video list
# ===========================

video_infos = []
# Store filtered video metadata
for v in videos:
    try:
        info = get_video_info(v["bvid"]) # Retrieve metadata via API
        if info and START_DATE <= info["pubdate"] <= END_DATE:
            v.update(info) # Merge metadata into the candidate record
            video_infos.append(v) # Append to final list
        time.sleep(random.uniform(1, 2)) # Random delay to avoid rate limiting
    except Exception as e:
        print(f"获取视频信息失败：{v['bvid']}，原因：{e}")

if len(video_infos) > TARGET_COUNT:
    video_infos = random.sample(video_infos, TARGET_COUNT)
# If more videos than needed were collected, randomly sample to meet target count.
    
print(f"筛选后共 {len(video_infos)} 个视频用于爬取。")

# ===========================
# Fetch danmaku (prefer public XML; fallback to legacy API if needed)
# ===========================
def get_danmu(cid, bvid, max_retries=3):
    # A. 公开 XML（更稳）
    xml_url = f"https://comment.bilibili.com/{cid}.xml"
    a_headers = {
        "User-Agent": BASE_HEADERS.get("User-Agent"),
        "Referer": f"https://www.bilibili.com/video/{bvid}",
        "Accept": "application/xml,text/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": BASE_HEADERS.get("Accept-Language", "zh-CN,zh;q=0.9,en;q=0.8"),
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
    }
    # Build request headers simulating a browser
    
    if "Cookie" in BASE_HEADERS:
        a_headers["Cookie"] = BASE_HEADERS["Cookie"]
         # Optional cookie injection

    for attempt in range(1, max_retries + 1):
        try:
            r = requests.get(xml_url, headers=a_headers, timeout=10)
             # Retry XML endpoint several times for robustness
            ct = (r.headers.get("Content-Type") or "").lower()
             # Check Content-Type to verify XML correctness
            if r.status_code == 200 and ("xml" in ct or "<d p=" in r.text):
                r.encoding = "utf-8"
                 # Check if valid XML is returned
                return re.findall(r"<d p=.*?>(.*?)</d>", r.text)
              # Extract danmaku text inside <d> tags
            time.sleep(random.uniform(1.0, 2.0))
             # Wait before retrying
        except Exception:
            time.sleep(random.uniform(1.0, 2.0))
            # Handle network exceptions gracefully and retry

    # B. 回退旧接口（list.so）
    listso_url = "https://api.bilibili.com/x/v1/dm/list.so"
    params = {"oid": str(cid)}
    # Fallback to legacy API when XML endpoint fails
    
    b_headers = {
        "User-Agent": BASE_HEADERS.get("User-Agent"),
        "Referer": f"https://www.bilibili.com/video/{bvid}",
        "Accept": "application/xml,text/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": BASE_HEADERS.get("Accept-Language", "zh-CN,zh;q=0.9,en;q=0.8"),
        "Origin": "https://www.bilibili.com",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
    }
   # Legacy API is sensitive to cookies, so cookie is omitted intentionally
  
   # Retry legacy API multiple times
    for attempt in range(1, max_retries + 1):
        try:
            r = requests.get(listso_url, params=params, headers=b_headers, timeout=10)
            ct = (r.headers.get("Content-Type") or "").lower()
            if r.status_code == 200 and ("xml" in ct or "<d p=" in r.text):
                r.encoding = "utf-8"
                return re.findall(r"<d p=.*?>(.*?)</d>", r.text)
            else:
                print(f"弹幕接口返回异常（尝试{attempt}/{max_retries}）：status={r.status_code}, ct={ct}")
                time.sleep(random.uniform(1.5, 3.0))
        except Exception as e:
            print(f"拉取弹幕异常（尝试{attempt}/{max_retries}）：{e}")
            time.sleep(random.uniform(1.5, 3.0))
    return []
   # Return empty list if both endpoints fail
  
# ===========================
# Comment scraping (cursor-based top-level retrieval + paginated sub-replies),
# with anti-scraping handling and optional login session.
# ===========================

def get_comments(aid, bvid, max_retries=4, limit=5000, with_sub=True, mode=3, need_login=True):
    """
    - 主楼游标：/x/v2/reply/main?type=1&oid={aid}&mode={mode}&next={cursor}
    - 楼中楼分页：/x/v2/reply/reply?type=1&oid={aid}&root={rpid}&pn={pn}&ps=49&mode={mode}
    关键点：
      * 按视频设置 Referer: https://www.bilibili.com/video/{bvid}/
      * 检查 json['code']，-412/-403 退避重试
      * 登录态 need_login=True（使用上面登录得到的 COOKIE_STRING）
    """
    collected = [] # Store all retrieved comments
    next_cursor = 0 # Cursor for paginating top-level comments

     # Build request headers
    base_headers = {
        "User-Agent": BASE_HEADERS.get("User-Agent"),
        "Referer": f"https://www.bilibili.com/video/{bvid}/",
        "Origin": "https://www.bilibili.com",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": BASE_HEADERS.get("Accept-Language", "zh-CN,zh;q=0.9,en;q=0.8"),
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
    }
    
    if need_login and "Cookie" in BASE_HEADERS:
        base_headers["Cookie"] = BASE_HEADERS["Cookie"]
        # Inject login cookies if enabled

     # Internal unified JSON request with retry + backoff
    def _req_json(url, params, backoff=1.2):
        for attempt in range(1, max_retries + 1):
            try:
                r = requests.get(url, params=params, headers=base_headers, timeout=10)
                j = r.json()
                code = j.get("code", 0)
                if code == 0:
                    return j.get("data") or {} # Return valid data
                else:
                    print(f"[评论接口] code={code}, msg={j.get('message')}, attempt={attempt}/{max_retries}")
                    time.sleep(backoff * attempt + random.uniform(0.3, 0.8))
                    # Anti-scraping triggered; retry with backoff
                    
            except Exception as e:
                print(f"[评论接口异常] {e} (attempt {attempt}/{max_retries})")
                time.sleep(backoff * attempt + random.uniform(0.3, 0.8))
                # Network or parsing error; retry after delay
        return {}

    # —— 主楼游标循环 ——
    # Main loop for paginating top-level comments using cursor-based API
    while len(collected) < limit:
        main_url = "https://api.bilibili.com/x/v2/reply/main"
        params = {"type": 1, "oid": aid, "mode": mode, "next": next_cursor} 
        # Parameters: video aid, sorting mode, pagination cursor
        data = _req_json(main_url, params)
        # Fetch JSON using unified request handler with retry & backoff
        if not data: # Exit if no data returned
            break
            
        # Parse pagination cursor
        cursor = data.get("cursor") or {}
        is_end = cursor.get("is_end", True) # Whether all pages have been reached
        next_cursor = cursor.get("next", 0) # Cursor for the next page

        # 置顶区
        # Pinned comments
        
        # Retrieve pinned top-level comments stored in `top_replies` by the Bilibili API.
        top_replies = data.get("top_replies") or []
       

        for tr in top_replies:
            try:             
                collected.append({
                    "rpid": tr["rpid"],
                    "message": tr.get("content", {}).get("message", ""),
                    "like": tr.get("like", 0),
                    "ctime": datetime.fromtimestamp(tr.get("ctime", 0)),
                    "member_mid": tr.get("member", {}).get("mid"),
                    "member_uname": tr.get("member", {}).get("uname"),
                    "is_top": 1, "root": None,
                })
            except Exception:
                pass
             # Append pinned comment into `collected`, marked as is_top=1
            
            # 置顶楼中楼补齐
            if with_sub and tr.get("rcount", 0) > len(tr.get("replies") or []):
            # If rcount > inline replies, additional nested replies must be fetched via pagination.
            
                root_id = tr.get("rpid")
              # Root ID of this thread
                pn = 1
                # Start pagination from page 1
                while len(collected) < limit:
                    sub_url = "https://api.bilibili.com/x/v2/reply/reply"
                     # Endpoint for nested replies
                    sub_params = {"type": 1, "oid": aid, "root": root_id, "pn": pn, "ps": 49, "mode": mode}
                    # Pagination parameters (up to 49 replies/page)
                    
                    sub_data = _req_json(sub_url, sub_params, backoff=0.9)
                     # Request with backoff for anti-scraping                    
                    if not sub_data: break
                    # Stop pagination if no reply data
                    subs = sub_data.get("replies") or []
                    # Get sub-replies list
                    if not subs: break
                    for s in subs:
                        collected.append({
                            "rpid": s.get("rpid"),
                            "message": "↳ " + s.get("content", {}).get("message", ""),
                            "like": s.get("like", 0),
                            "ctime": datetime.fromtimestamp(s.get("ctime", 0)),
                            "member_mid": s.get("member", {}).get("mid"),
                            "member_uname": s.get("member", {}).get("uname"),
                            "is_top": 0, "root": root_id,
                        })
                        if len(collected) >= limit: break
                    pn += 1
                    time.sleep(random.uniform(0.8, 1.6))
                     # Random delay to avoid anti-scraping

        replies = data.get("replies") or []
         # Retrieve regular top-level replies
        if not replies and is_end:
            break
             # If no replies and no more pages, stop

        for r in replies:
            try:
                collected.append({
                    "rpid": r["rpid"],
                    "message": r.get("content", {}).get("message", ""),
                    "like": r.get("like", 0),
                    "ctime": datetime.fromtimestamp(r.get("ctime", 0)),
                    "member_mid": r.get("member", {}).get("mid"),
                    "member_uname": r.get("member", {}).get("uname"),
                    "is_top": 0, "root": None,
                })
            except Exception:
                pass

            # 内联子楼
            # Inline sub-replies
            if r.get("replies"):
               # Insert inline sub-replies directly
                for sub in r["replies"]:
                    collected.append({
                        "rpid": sub.get("rpid"),
                        "message": "↳ " + sub.get("content", {}).get("message", ""),
                        "like": sub.get("like", 0),
                        "ctime": datetime.fromtimestamp(sub.get("ctime", 0)),
                        "member_mid": sub.get("member", {}).get("mid"),
                        "member_uname": sub.get("member", {}).get("uname"),
                        "is_top": 0, "root": r.get("rpid"),
                    })

            # 子楼分页补齐
            # Paginated sub-replies
            if with_sub and r.get("rcount", 0) > len(r.get("replies") or []):
              # Need additional pagination for missing nested replies
                root_id = r.get("rpid")
                pn = 1
                while len(collected) < limit:
                    sub_url = "https://api.bilibili.com/x/v2/reply/reply"
                    sub_params = {"type": 1, "oid": aid, "root": root_id, "pn": pn, "ps": 49, "mode": mode}
                    sub_data = _req_json(sub_url, sub_params, backoff=0.9)
                    if not sub_data: break
                    subs = sub_data.get("replies") or []
                    if not subs: break
                    for s in subs:
                        collected.append({
                            "rpid": s.get("rpid"),
                            "message": "↳ " + s.get("content", {}).get("message", ""),
                            "like": s.get("like", 0),
                            "ctime": datetime.fromtimestamp(s.get("ctime", 0)),
                            "member_mid": s.get("member", {}).get("mid"),
                            "member_uname": s.get("member", {}).get("uname"),
                            "is_top": 0, "root": root_id,
                        })
                        if len(collected) >= limit: break
                    pn += 1
                    time.sleep(random.uniform(0.8, 1.6))
                    # Anti-scraping pause

            if len(collected) >= limit:
                break

        if is_end or len(collected) >= limit:
            break
            #Stop if end of pages or limit reached

        time.sleep(random.uniform(1.2, 2.0))
        # Random sleep between pages for safety

    # 回退旧接口，避免极端情况下拿到0
    # Fallback to legacy comment API
    
    if not collected:
        print("⚠️ 主接口未取到评论，回退到 /x/v2/reply?pn=… 旧接口尝试补救")
        page = 1 # Start legacy pagination from page 1
        while len(collected) < min(limit, 1000):
          # Limit recovery to 1000 comments to prevent infinite loops
            old_url = "https://api.bilibili.com/x/v2/reply"
            # 旧接口 URL（Legacy Bilibili comment API URL）
            old_params = {"type": 1, "oid": aid, "pn": page, "ps": 20, "sort": 2}
            try:
                r = requests.get(old_url, params=old_params, headers=base_headers, timeout=10)
                 # Send HTTP request to legacy endpoint

                j = r.json()
                # Parse response JSON
                if j.get("code") != 0:
                    break
                    # Stop fallback if API returns an error code
                replies = (j.get("data") or {}).get("replies") or []
                 # Extract reply list from legacy API result
                if not replies:
                    break
                    # No more comments → end fallback
                for rr in replies:
                  # Iterate through recovered replies
                    collected.append({
                        "rpid": rr.get("rpid"),
                        "message": rr.get("content", {}).get("message", ""),
                        "like": rr.get("like", 0),
                        "ctime": datetime.fromtimestamp(rr.get("ctime", 0)),
                        "member_mid": rr.get("member", {}).get("mid"),
                        "member_uname": rr.get("member", {}).get("uname"),
                        "is_top": 0, "root": None,
                    }) # Legacy API does not distinguish pinned comments
                       # Legacy endpoint lacks nested structure info
                    if len(collected) >= limit:
                        break
                page += 1
                time.sleep(random.uniform(0.8, 1.4))
                # Random delay to reduce anti-scraping triggers
            except Exception:
                break
                  # Stop fallback on any error such as network failure or JSON parse error

    return collected[:limit]
  # Return the final collected comment list, cropped to the specified limit
  
# ===========================
# Data scraping main loop
# ===========================
summary_list, all_comments, all_danmu = [], [], []
# summary_list → store video metadata
# all_comments → store all comments (incl. nested)
# all_danmu → store all danmaku messages

try:
    for v in video_infos:
        print(f"▶ 正在抓取：{v['title']}")
          # Print the title of the video being processed
        summary_list.append({
            "bvid": v["bvid"],
            "aid": v["aid"],
            "title": v["title"],
            "pubdate": v["pubdate"],
            "view": v["view"],
            "like": v["like"],
            "coin": v["coin"],
            "favorite": v["favorite"],
            "share": v["share"],
            "danmaku": v["danmaku"],
            "reply_count": v["reply_count"],
            "cids": "|".join(map(str, v.get("cids", []))),
            "url": v.get("url")
        })
        # Append video metadata into summary_list

        # 弹幕 Danmaku Scraping
        for cid in v.get("cids", []):
            danmu_list = get_danmu(cid, v["bvid"]) # Fetch danmaku for each CID via get_danmu()
            for d in danmu_list[:1000]:
                all_danmu.append({"bvid": v["bvid"], "cid": cid, "danmu": d})
            print(f"  - cid={cid} 弹幕数：{len(danmu_list)}")# Print danmaku count for this CID
            time.sleep(random.uniform(1.2, 2.0))# Random sleep to avoid anti-scraping triggers

        # 评论（登录态；游标 + 楼中楼）Comments Scraping
        comments_list = get_comments(
            v["aid"], v["bvid"],
            limit=5000, with_sub=True, mode=3, need_login=True  # 登陆后抓取的关键
        )
        # Max 5000 comments， Include nested replies，Sort mode，Use login cookies
        for c in comments_list:
            c["bvid"] = v["bvid"] # Attach BV ID to each comment
            all_comments.append(c)# Append to global comment list
        print(f"  - 评论数（含楼中楼）：{len(comments_list)}")
         # Print total comments count (including nested)

        time.sleep(random.uniform(1.8, 3.5))
        # Random delay between videos for safety
finally:
    driver.quit()
     # Ensure Selenium browser closes even if an error occurs

# ===========================
# Save output files to target directory
# ===========================
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
# Generate a timestamp to distinguish output batches
safe_song_name = SONG_TITLE.replace(" ", "_")
# Replace spaces with underscores to make the name file-safe
summary_path  = os.path.join(RESULT_DIR, f"bili_covers_summary_{safe_song_name}_{timestamp}.csv")
comments_path = os.path.join(RESULT_DIR, f"bili_covers_comments_{safe_song_name}_{timestamp}.csv")
danmu_path    = os.path.join(RESULT_DIR, f"bili_covers_danmu_{safe_song_name}_{timestamp}.csv")
# Construct file paths for the three CSV outputs: summary / comments / danmaku

pd.DataFrame(summary_list).to_csv(summary_path, index=False)
pd.DataFrame(all_comments).to_csv(comments_path, index=False)
pd.DataFrame(all_danmu).to_csv(danmu_path, index=False)
# Convert lists into DataFrames and write them into CSV files

print("✅ 所有数据已保存完成！")
print("📂 保存目录：", RESULT_DIR)
print("📄 文件：")
print(" -", summary_path)
print(" -", comments_path)
print(" -", danmu_path)
