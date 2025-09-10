from flask import Flask, request, jsonify
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import logging
import time
import threading

# Fixed credentials
USERNAME = "u002358"
PASSWORD = "PB2358"

# Logging setup
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

app = Flask(__name__)
lock = threading.Lock()

class OrderScraper:
    def __init__(self, headless=True):
        options = webdriver.ChromeOptions()
        if headless:
            options.add_argument('--headless=new')
            options.add_argument('--disable-gpu')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--window-size=1920,1080')
            options.add_argument('--blink-settings=imagesEnabled=false')
            options.page_load_strategy = 'eager'

        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=options)
        self.wait = WebDriverWait(self.driver, 10)
        logger.info("🚀 Browser launched")

    def login(self, url):
        logger.info("🌐 Logging in...")
        self.driver.get(url)
        self.wait.until(EC.presence_of_element_located((By.NAME, "userid"))).send_keys(USERNAME)
        self.driver.find_element(By.NAME, "password").send_keys(PASSWORD)
        self.driver.find_element(By.NAME, "password").submit()
        self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        logger.info("✅ Login successful")
        self.navigate_to_products()

    def is_logged_in(self):
        self.driver.get("https://nel.familiprix.com/")
        return "PRODUITS.A.VERIFIER" in self.driver.page_source

    def ensure_logged_in(self, url):
        try:
            if not self.is_logged_in():
                logger.info("🔁 Session expired. Re-logging in.")
                self.login(url)
        except Exception as e:
            logger.error(f"⚠️ Error checking session, reinitializing browser: {e}")
            self.driver.quit()
            self.__init__()
            self.login(url)

    def navigate_to_products(self):
        logger.info("Navigating to product section...")
        self.wait.until(
            EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), 'Commandes en cours')]"))
        ).click()
        self.wait.until(
            EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), 'ANTHONY')]"))
        ).click()
        self.wait.until(EC.presence_of_element_located((By.NAME, "search")))

    def perform_search(self, keyword):
        logger.info(f"🔍 Searching: {keyword}")
        search_box = self.wait.until(EC.presence_of_element_located((By.NAME, "search")))
        search_box.clear()
        search_box.send_keys(keyword)
        ok_button = self.driver.find_element(By.XPATH, "//input[@type='submit' and @value=' Ok ']")
        ok_button.click()
        self.wait.until(EC.presence_of_element_located((By.CLASS_NAME, "produits")))

    def scrape_table(self):
        logger.info("📊 Scraping table...")
        table = self.driver.find_element(By.CLASS_NAME, "produits")
        rows = table.find_elements(By.TAG_NAME, "tr")[1:]

        data = []
        for row in rows:
            cols = row.find_elements(By.TAG_NAME, "td")
            if len(cols) >= 10:
                data.append({
                    "Code": cols[0].text.strip(),
                    "Description": cols[1].text.strip(),
                    "Qt/CS": cols[2].text.strip(),
                    "Détail": cols[3].text.strip(),
                    "Coûtant Régulier": cols[4].text.strip(),
                    "Coûtant Facture": cols[5].text.strip(),
                    "Rabais POS": cols[6].text.strip(),
                    "Disponible": cols[7].text.strip(),
                    "Qté": cols[8].text.strip(),
                    "Dern. Cmd": cols[9].text.strip()
                })
        logger.info(f"✅ Scraped {len(data)} rows")
        return data

    def close(self):
        logger.info("🛑 Closing browser")
        self.driver.quit()


# Global shared scraper
scraper = OrderScraper(headless=True)
scraper.login("https://nel.familiprix.com/")  # login once at startup

@app.route('/scrape', methods=['GET'])
def scrape():
    keywords_param = request.args.get("keywords")
   
    if not keywords_param:
        return jsonify({"error": "Missing 'keywords' parameter"}), 400
    
    
 

    keywords = [k.strip() for k in keywords_param.split(",") if k.strip()]
    if not keywords:
        return jsonify({"error": "No valid UPCs provided"}), 400

    all_results = []
    start = time.time()

    with lock:  # thread-safe
        try:
            scraper.ensure_logged_in("https://nel.familiprix.com/")
            logger.info("🔄 Refreshing browser before starting search...")
            scraper.driver.refresh()
            scraper.wait.until(EC.presence_of_element_located((By.NAME, "search")))

            for keyword in keywords:
                print("Keyyyyyyyyyyyyyyyyyy", keyword)
                Ckeyword = keyword.lstrip('0')


                try:
                    scraper.perform_search(Ckeyword)
                    data = scraper.scrape_table()
                    all_results.append({
                        "upc": keyword,
                        "results": data
                    })
                except Exception as e:
                    logger.warning(f"❌ UPC {keyword} failed: {e}")
                    all_results.append({
                        "upc": keyword,
                        "error": str(e),
                        "results": []
                    })

            duration = round(time.time() - start, 2)
            return jsonify({
                "status": "success",
                "duration": duration,
                "total_upcs": len(keywords),
                "data": all_results
            })

        except Exception as e:
            logger.error(f"❌ Scraping failed: {e}")
            return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    print("🚀 Server running at http://localhost:5000")
    app.run(host="0.0.0.0", port=5000, threaded=True)
