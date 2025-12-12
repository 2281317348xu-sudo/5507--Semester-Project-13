# ----------------------------
# Bilibili Hot Song Selection Chart Crawler (Top 16 songs only, up to 2 pages)
# Version Notes:
# This script only retrieves the top 16 songs from the “Hot Song Selection Chart”.
# A maximum of 2 pages will be crawled to ensure speed and stability.
# ----------------------------

from selenium import webdriver # Import Selenium WebDriver, used to control the browser
from selenium.webdriver.chrome.service import Service # Used to create the ChromeDriver service object
from selenium.webdriver.chrome.options import Options # Browser configuration options
from selenium.webdriver.common.by import By # Used for locating DOM elements with different strategies
from selenium.webdriver.support.ui import WebDriverWait # Import explicit wait module
from selenium.webdriver.support import expected_conditions as EC # Import expected conditions (used to wait for specific elements to load)
from webdriver_manager.chrome import ChromeDriverManager # Automatically install and manage ChromeDriver versions
import time # Standard time module, used for delay operations
import random # Random module, used to simulate human behavior (reducing anti-crawler detection)

# ----------------------------
# Parameter configuration (modifiable as needed)
# ----------------------------
LOGIN_WAIT_SECONDS = 45    # Time to wait on the login page for QR scan (seconds)
PAGE_LOAD_WAIT = 20        # Waiting time for the music center page to load (seconds)
SCROLL_STEPS = 3           # Number of simulated scroll actions per page (used to trigger lazy loading)
DELAY_MIN, DELAY_MAX = 0.8, 1.5   # Delay range between each song extraction (simulates human clicks)
MAX_SONGS = 16                    # Only fetch the top 16 songs
MAX_PAGES = 2                     # Maximum of 2 pages to crawl

# ----------------------------
# Create browser driver object
# ----------------------------
def make_driver():
    options = Options()

    # Set user-agent to simulate a real browser identity and reduce risk of detection
    ua = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
          "AppleWebKit/537.36 (KHTML, like Gecko) "
          "Chrome/120.0.0.0 Safari/537.36")
    options.add_argument(f"user-agent={ua}")

    # Remove Selenium-specific indicators to lower automation detection risk
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    options.add_argument("--disable-blink-features=AutomationControlled")

    # Improve compatibility and prevent crashes in certain system environments
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
   
    # options.add_argument("--headless")  # Enable this if running without a GUI

    # Automatically download and configure ChromeDriver
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    
    driver.maximize_window() # Maximize window to ensure all elements are visible
    return driver

# ----------------------------
# Simulate user scrolling (trigger lazy loading)
# ----------------------------
def simulate_scroll(driver):
    for _ in range(SCROLL_STEPS):
        # JavaScript controls the browser to scroll down a certain distance
        driver.execute_script(f"window.scrollBy(0, {random.randint(300, 700)});")
        time.sleep(random.uniform(0.3, 0.7)) # Random pause to avoid abnormal behavior patterns

# ----------------------------
# Main function: Fetch Hot Song Selection chart
# ----------------------------
def fetch_hot_rank_songs():
    driver = make_driver()  # Launch browser
    all_songs = []          # Store retrieved song names

    try:
        # ---------------------
        # Login to Bilibili
        # ---------------------
        driver.get("https://passport.bilibili.com/login")
        print(f"请扫码登录 Bilibili（等待 {LOGIN_WAIT_SECONDS} 秒）...")
        time.sleep(LOGIN_WAIT_SECONDS)
        # ---------------------
        # Enter the music center page
        # ---------------------
        driver.get("https://music.bilibili.com/pc/music-center/?spm_id_from=333.40138.0.0")
        print(f"等待音乐中心加载 {PAGE_LOAD_WAIT} 秒...")
        WebDriverWait(driver, PAGE_LOAD_WAIT).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        time.sleep(2)
        
        # --------------------- 
        # Locate the Hot Song Selection area
        # --------------------- 
        hot_rank = WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CLASS_NAME, "_hotRank_1b42a_6"))
        )
        print("✅ 已定位到 热歌精选榜 区块。")

        # ---------------------
        # Start extracting (up to 2 pages × top 16 songs)
        # ---------------------
        page = 1
        while page <= MAX_PAGES:
            print(f"\n==== 正在抓取第 {page} 页 ====")
            
            simulate_scroll(driver) # Simulate scrolling to load more content
            time.sleep(random.uniform(1, 1.5))

            # Locate song containers in the chart
            containers = hot_rank.find_elements(By.CSS_SELECTOR, "div._container_1b42a_477")
           
           # Iterate through two layout floors: first floor and second floor
            for container in containers:
                for floor_class in ["_first-floor_1b42a_482", "_second-floor_1b42a_483"]:
                    try:
                        floor = container.find_element(By.CLASS_NAME, floor_class)
                        
                        # Locate the tags where song names are stored
                        song_divs = floor.find_elements(
                            By.CSS_SELECTOR,
                            "div._info_1epcv_140 > div._name_1epcv_140"
                        )


                        for s in song_divs:
                            name = s.text.strip() # Retrieve song name text

                            # Remove duplicates and add to list
                            if name and name not in all_songs:
                                all_songs.append(name)
                                print(f"🎵 {len(all_songs)}. {name}")
                                time.sleep(random.uniform(DELAY_MIN, DELAY_MAX))

                            # If 16 songs reached, forcibly stop extraction
                            if len(all_songs) >= MAX_SONGS:
                                print("\n✅ 已抓满 16 首歌曲，停止抓取。")
                                raise StopIteration # Exit nested loops
                    except Exception:
                        continue
            # ---------------------
            # Pagination logic (max 2 pages)
            # ---------------------
            if page >= MAX_PAGES:
                print("\n✅ 已到第 2 页（上限），停止翻页。")
                break

            try:
                # Find “Next Page” button (right-side arrow)
                next_button = driver.find_element(By.CLASS_NAME, "_headerControlRight_1b42a_59")
                
                # Scroll button into visible area
                driver.execute_script("arguments[0].scrollIntoView(true);", next_button)
                time.sleep(0.5)

                # Click next page (JavaScript click more stable than Selenium click)
                driver.execute_script("arguments[0].click();", next_button)
                print("➡️ 成功点击下一页")

                time.sleep(15)   # Wait for next page to load
                page += 1

            except Exception as e:
                print("⚠️ 翻页失败或未找到下一页按钮：", e)
                break

    except StopIteration:
         # Used to stop early when 16 songs have been collected
        pass

    finally:
        # ---------------------
        # Output final results
        # ---------------------
        print("\n================== 抓取完成 ==================")
        for i, name in enumerate(all_songs, 1):
            print(f"{i}. {name}")

        print(f"\n共抓取 {len(all_songs)} 首歌曲。")

       # Close browser
        print("\n5 秒后关闭浏览器...")
        time.sleep(5)
        driver.quit()

# ----------------------------
# Program entry point
# ----------------------------
if __name__ == "__main__":
    fetch_hot_rank_songs()
