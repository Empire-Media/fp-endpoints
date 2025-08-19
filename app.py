from flask import Flask, request, jsonify
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from openai import OpenAI
import threading
import logging
import time
import uuid
import json
import os
from logging.handlers import TimedRotatingFileHandler
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

USERNAME = "u002358"
PASSWORD = "PB2358"

# --- Logger setup ---
os.makedirs("Logs", exist_ok=True)
logger = logging.getLogger("app-fp_logger")
logger.setLevel(logging.INFO)

handler = TimedRotatingFileHandler("Logs/app-fp_logs.log", when="W0", interval=1, backupCount=1, encoding='utf-8')
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)

if not logger.handlers:
    logger.addHandler(handler)

logger.info("🔧 Logger initialized.")

app = Flask(__name__)

RESULTS_FILE = "results.json"
results_lock = threading.Lock()

if not os.path.exists(RESULTS_FILE):
    with open(RESULTS_FILE, "w") as f:
        json.dump({}, f)

class OrderScraper:
    def __init__(self, headless=True):
        options = webdriver.ChromeOptions()
        if headless:
            options.add_argument('--headless')
            options.add_argument('--window-size=1920,1080')

        self.driver = webdriver.Chrome(options=options)
        self.wait = WebDriverWait(self.driver, 10)
        logger.info("Browser launched")

    def open_site(self, url):
        self.driver.get(url)
        logger.info(f"Opened: {url}")

    def login(self):
        self.wait.until(EC.presence_of_element_located((By.NAME, "userid"))).send_keys(USERNAME)
        self.wait.until(EC.presence_of_element_located((By.NAME, "password"))).send_keys(PASSWORD)
        self.driver.find_element(By.NAME, "password").submit()

    def navigate_to_commande(self):
        self.wait.until(EC.element_to_be_clickable((By.XPATH, "//a[@class='menu' and contains(@href, 'ORDHDR.pgm') and contains(text(), 'Commande')]"))).click()
        time.sleep(1)

    def create_cart(self, cart_name):
        cart_input = self.wait.until(EC.presence_of_element_located((By.XPATH, "//input[@type='text' and @name='name']")))
        cart_input.clear()
        cart_input.send_keys(cart_name)
        self.wait.until(EC.element_to_be_clickable((By.XPATH, "//input[@type='submit' and @value='Poursuivre']"))).click()
        time.sleep(1)
        self.wait.until(EC.element_to_be_clickable((By.XPATH, "//a[@class='menu' and contains(@href, 'ACCUEIL.pgm') and contains(text(), 'Accueil')]"))).click()
        time.sleep(1)

    def access_cart(self, cart_name):
        self.wait.until(EC.element_to_be_clickable((By.XPATH, "//a[@class='sousMenu' and contains(@href, 'ordlst.pgm') and contains(text(), 'Commandes en cours')]"))).click()
        time.sleep(1)
        self.wait.until(EC.element_to_be_clickable((By.XPATH, f"//a[contains(@href, 'orddtl.pgm') and contains(@href, 'name={cart_name.upper()}') and text()='{cart_name.upper()}']"))).click()
        time.sleep(1)

    def add_to_cart(self, keyword,required_name,qty,dosage,pack_size):
        logger.info(f"Searching for: {keyword}")
        actifs_radio = self.wait.until(EC.presence_of_element_located((By.ID, "status1")))

        if not actifs_radio.is_selected():
            logger.info("Actifs radio is clicked")
            actifs_radio.click()
        else:
            logger.info("Actifs radio was already clicked")
        search_box = self.wait.until(EC.presence_of_element_located((By.NAME, "search")))
        search_box.clear()
        search_box.send_keys(keyword)
        
        ok_button = self.driver.find_element(By.XPATH, "//input[@type='submit' and @value=' Ok ']")
        ok_button.click()
        logger.info("Search submitted")
        
        time.sleep(1)

        rows = self.driver.find_elements(By.XPATH, "//tr[td[@class='item']]")
        results = []

        while True:
            time.sleep(1)
            rows = self.driver.find_elements(By.XPATH, "//tr[td[@class='item']]")
            
            for row in rows:
                try:
                    desc = row.find_element(By.XPATH, ".//td[@class='item']/b").text
                    price = row.find_elements(By.XPATH, ".//td[@class='R']")[2].text
                    product_id = row.find_element(By.XPATH, "./td[1]/a").text
                    results.append({
                        "element": row,
                        "description": desc,
                        "price": price,
                        "id": product_id
                    })
                except:
                    continue

            try:
                next_button = self.driver.find_element(By.XPATH, "//a[@class='sousMenu' and contains(text(), 'Page suivante')]")
                if next_button.is_displayed():
                    next_button.click()
                    self.wait.until(EC.staleness_of(rows[0]))  
                    time.sleep(1)
                else:
                    break
            except:
                break 

        name_str=""
        if required_name is not None:
            name_str=f"\nRequired Name: {required_name}"

        selected_id="" 
        if len(results) > 1:
            options = "\n".join([f"{r['description']} (ID: {r['id']})" for r in results])
            prompt = (
                f"Extract from the text below the id of the product with the required dosage and pack size.\n"
                f"Available options:\n{options}\n\n"
                f"Match the correct form (in name, dosage, or pack size) IF MENTIONED: Pen, Syringe (SER), Auto-Injector (INJ), Prefilled Syringe (PFS/PF SER), Cream (CR).\n\n"
                f"Required dosage: {dosage}\nRequired pack size: {pack_size}{name_str}\n\n"
                f"For some products like Protopic, if the required dosage is 0.0x% and the available is 0.x% and NOT 0.0y%, then take it since it is the closest match.\n\n"
                f"Return the id alone with no additional text. Return only one result.\n\n"
                f"YOU MUST FIND A MATCH (not necessarily an exact match but the closest possible match). If nothing matches, return null only."
            )
            try:
                # Combine system message with user prompt for input
                full_input = f"You are an assistant that identifies the correct medication product from a list.\n\n{prompt}"
                
                response = client.responses.create(
                    model="gpt-4.1",
                    input=full_input,
                    temperature=0.2,
                )

                # Handle different possible response structures
                try:
                    if hasattr(response, 'output_text') and response.output_text:
                        selected_id = str(response.output_text).strip()
                    elif hasattr(response, 'text') and response.text:
                        if hasattr(response.text, 'strip'):
                            selected_id = response.text.strip()
                        else:
                            selected_id = str(response.text).strip()
                    elif hasattr(response, 'output') and response.output:
                        if hasattr(response.output, 'strip'):
                            selected_id = response.output.strip()
                        else:
                            selected_id = str(response.output).strip()
                    elif hasattr(response, 'choices') and response.choices:
                        selected_id = response.choices[0].message.content.strip()
                    elif hasattr(response, 'content'):
                        if hasattr(response.content, 'strip'):
                            selected_id = response.content.strip()
                        else:
                            selected_id = str(response.content).strip()
                    elif hasattr(response, 'message'):
                        if hasattr(response.message, 'content'):
                            selected_id = str(response.message.content).strip()
                        else:
                            selected_id = str(response.message).strip()
                    else:
                        # Fallback: convert entire response to string
                        selected_id = str(response).strip()
                        
                    logger.info(f"Extracted text: {selected_id[:100]}...")  # Log first 100 chars
                except Exception as parse_error:
                    logger.error(f"Error parsing response: {parse_error}")
                    selected_id = "null"
                    
                logger.info(f"GPT selected product ID: {selected_id}")

                if selected_id.lower() == "null":
                    logger.info("GPT returned null, Retrying...")
                    prompt = (
                    f"Extract from the text below the id of the product with the required dosage and pack size.\n"
                    f"Available options:\n{options}\n\n"
                    f"Match the correct form (in name, dosage, or pack size) IF MENTIONED: Pen, Syringe (SER), Auto-Injector (INJ), Prefilled Syringe (PFS/PF SER), Cream (CR).\n\n"
                    f"Required dosage: {dosage}\nRequired pack size: {pack_size}{name_str}\n\n"
                    f"For some products like Protopic, if the required dosage is 0.0x% and the available is 0.x% and NOT 0.0y%, then take it since it is the closest match.\n\n"
                    f"Return the id alone with no additional text. Return only one result.\n\n"
                    f"YOU MUST FIND A MATCH (not necessarily an exact match but the closest possible match). If nothing matches, return null only."
                    )
                    full_input = f"You are an assistant that identifies the correct medication product from a list.\n\n{prompt}"
                    
                    response = client.responses.create(
                        model="gpt-4.1",
                        input=full_input,
                        temperature=0.2,
                    )

                    
                    if hasattr(response, 'output_text') and response.output_text:
                        selected_id = str(response.output_text).strip()
                    elif hasattr(response, 'text') and response.text:
                        if hasattr(response.text, 'strip'):
                            selected_id = response.text.strip()
                        else:
                            selected_id = str(response.text).strip()
                    elif hasattr(response, 'output') and response.output:
                        if hasattr(response.output, 'strip'):
                            selected_id = response.output.strip()
                        else:
                            selected_id = str(response.output).strip()
                    elif hasattr(response, 'choices') and response.choices:
                        selected_id = response.choices[0].message.content.strip()
                    elif hasattr(response, 'content'):
                        if hasattr(response.content, 'strip'):
                            selected_id = response.content.strip()
                        else:
                            selected_id = str(response.content).strip()
                    elif hasattr(response, 'message'):
                        if hasattr(response.message, 'content'):
                            selected_id = str(response.message.content).strip()
                        else:
                            selected_id = str(response.message).strip()
                    else:
                        selected_id = str(response).strip()  
                    logger.info(f"New selected ID: {selected_id}...")
                    if selected_id.lower() == "null": 
                        logger.info(f"Product {required_name} not found...") 
                        return {
                            "found": "0",
                            "description": required_name,                    
                            "upc": "",
                            "quantity": qty,
                            "price": None
                        }                             

                # Perform refined search with selected_id
                search_box = self.wait.until(EC.presence_of_element_located((By.NAME, "search")))
                search_box.clear()
                search_box.send_keys(selected_id)
                ok_button = self.driver.find_element(By.XPATH, "//input[@type='submit' and @value=' Ok ']")
                ok_button.click()
                logger.info(f"Search resubmitted for GPT-selected product ID: {selected_id}")
            except Exception as e:
                logger.error(f"GPT selection failed: {e}")
                return {
                    "found": "0",
                    "description": required_name,                    
                    "upc": "",
                    "quantity": qty,
                    "price": None
                }
        try:
            time.sleep(5)
            product_desc = self.wait.until(
            EC.presence_of_element_located((By.XPATH, "//tr[1]/td[@class='item']/b"))
            ).text

            product_price = self.wait.until(
                EC.presence_of_element_located((By.XPATH, "(//tr[1]/td[@class='R'])[3]"))
            ).text

            stock_status = self.wait.until(
                EC.presence_of_element_located((By.XPATH, "//tr[1]/td[@class='C'][1]"))
            ).text.strip()

            logger.info(f"Product {product_desc} not in Inventory: {stock_status}")

            if stock_status.startswith("Non"):
                return {
                    "found": "2",
                    "description": product_desc,
                    "upc": "",
                    "quantity": qty,
                    "price": product_price
                }

            logger.info(f"Product found: {product_desc} - {product_price}")
            product_id = self.driver.find_element(By.XPATH, "//tr[1]/td[1]/a").text
            try:
                item_link = self.wait.until(EC.element_to_be_clickable((By.XPATH, f"//a[text()='{product_id}']")))
                item_link.click()
                time.sleep(2)
            except Exception as e:
                logger.warning(f"Item link with ID {product_id} not clickable — assuming already on detail page.")

            upc_cell = self.wait.until(
                EC.presence_of_element_located((By.XPATH, "//table//td[text()='U.P.C.']/following-sibling::td[1]"))
            )
            upc_value = upc_cell.text.strip().lstrip('0')
            logger.info(f"UPC: {upc_value}")

            logger.info(f"Entering quantity {qty}")
            quantity_input = self.wait.until(EC.presence_of_element_located((By.NAME, "qte21")))
            quantity_input.clear()
            quantity_input.send_keys(qty)

            add_to_cart_button = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, "//input[@type='submit' and @value='Ajouter au panier']"))
            )
            add_to_cart_button.click()
            time.sleep(20)
            logger.info("Item added to cart")
            time.sleep(1)
            return {
                "found": "1",
                "description": product_desc,
                "upc": upc_value,
                "quantity": qty,
                "price": product_price
            }
        except Exception as e:
            logger.info(f"Product {keyword} not found: {e}")
            return {
                "found": "0",
                "description": keyword,
                "upc": "",                
                "quantity": qty,
                "price": None
            }
       
    def close(self):
        self.driver.quit()

def process_cart(task_id, name, keywords,scraper):
    logger.info(f"Started processing task {task_id} with {len(keywords)} items")
    start_time = time.time()
    try:
        results = []
        for item in keywords:
            logger.info(f"Processing item: {item}")
            result = scraper.add_to_cart(item["name"], item["required_name"], item["quantity"], item["dosage"], item["pack_size"])
            results.append(result)
        logger.info(f"Finished processing all items for task {task_id}")
    except Exception as e:
        logger.exception(f"Error in processing task {task_id}")
        results = [{"error": str(e)}]
    finally:
        scraper.close()
        with results_lock:
            try:
                with open(RESULTS_FILE, "r") as f:
                    existing = json.load(f)
            except Exception as e:
                logger.exception("Error reading existing results before write")
                existing = {}

            existing[task_id] = {"status": "done", "result": results}
            try:
                with open(RESULTS_FILE, "w") as f:
                    json.dump(existing, f, indent=2)
                logger.info(f"Task {task_id} results written to file")
            except Exception as e:
                logger.exception("Error writing results to file")

@app.route('/cart', methods=['POST'])
def start_cart():
    scraper = OrderScraper(headless=True)
    logger.info("Received request to /cart")
    data = request.json
    name = data.get("name")
    keywords = data.get("keywords", [])
    
    logger.info(f"Cart name: {name}, Keywords count: {len(keywords)}")
    
    if not name or not keywords:
        logger.warning("Missing cart name or keywords")
        return jsonify({"error": "Missing cart name or keywords"}), 400

    try:
        logger.info("Opening Familiprix site and logging in")
        scraper.open_site("https://nel.familiprix.com/")
        scraper.login()
        scraper.navigate_to_commande()
        scraper.create_cart(name)
        scraper.access_cart(name)
    except Exception as e:
        logger.exception("Failed during cart initialization")
        return jsonify({"error": str(e)}), 500

    task_id = uuid.uuid4().hex
    logger.info(f"Task ID generated: {task_id}")

    thread = threading.Thread(target=process_cart, args=(task_id, name, keywords,scraper))
    thread.start()
    logger.info(f"Thread started for task {task_id}")

    start = time.time()
    while time.time() - start < 250:
        with results_lock:
            try:
                with open(RESULTS_FILE, "r") as f:
                    results = json.load(f)
            except Exception as e:
                logger.exception("Failed to read results file")
                break

            if task_id in results:
                logger.info(f"Result ready for task {task_id}")
                return jsonify({"status": "done", "id": task_id, "result": results[task_id]["result"]})

        time.sleep(5)

    logger.info(f"Result not ready within timeout for task {task_id}")
    return jsonify({"status": "in_progress", "id": task_id})

@app.route('/result/<task_id>', methods=['GET'])
def get_result(task_id):
    logger.info(f"Received request to /result/{task_id}")
    with results_lock:
        try:
            with open(RESULTS_FILE, "r") as f:
                results = json.load(f)
        except Exception as e:
            logger.exception("Error reading results file")
            return jsonify({"error": "Internal error"}), 500

        if task_id in results:
            result = results.pop(task_id)
            try:
                with open(RESULTS_FILE, "w") as f:
                    json.dump(results, f, indent=2)
                logger.info(f"Returning and removing result for task {task_id}")
            except Exception as e:
                logger.exception("Error writing to results file after popping")
            return jsonify(result)
        else:
            logger.warning(f"Result not found for task {task_id}")
            return jsonify({"status": "not_found"}), 404


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5001, debug=True)
