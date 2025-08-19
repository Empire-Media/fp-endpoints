from flask import Flask, request, send_file, jsonify
from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException,ElementClickInterceptedException
import time
import os
import traceback
import requests
from io import BytesIO
import logging
from logging.handlers import TimedRotatingFileHandler

app = Flask(__name__)

# --- Logger setup ---
os.makedirs("Logs", exist_ok=True)
logger = logging.getLogger("app-qb_logger")
logger.setLevel(logging.INFO)

log_file = "Logs/app-qb_logs.log"
handler = TimedRotatingFileHandler("Logs/app-qb_logs.log", when="W0", interval=1, backupCount=1, encoding='utf-8')
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)

if not logger.handlers:
    logger.addHandler(handler)

logger.info("🔧 Logger initialized.")

def update_invoice(customer, shipping_date, carrier, po_numer):
    chrome_options = ChromeOptions()
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    driver = None

    try:
        driver = webdriver.Chrome(options=chrome_options)
        wait = WebDriverWait(driver, 30)

        logger.info("Navigating to login page")
        driver.get('https://accounts.intuit.com/index.html')
        email = wait.until(EC.presence_of_element_located((By.ID, "iux-identifier-first-unknown-identifier")))
        email.click()
        email.send_keys("rami.sbaity@empiremedia.io")
        wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button[data-testid='IdentifierFirstSubmitButton']"))).click()

        time.sleep(5)
        wait.until(EC.presence_of_element_located((By.ID, 'iux-password-confirmation-password'))).send_keys('Ha:inC6wJTYf.WW')
        driver.find_element(By.CSS_SELECTOR, 'button[data-testid="passwordVerificationContinueButton"]').click()

        try:
            skip_btn = WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.ID, "skipPasskeyRegistration")))
            skip_btn.click()
        except:
            pass

        try:
            logger.info("Requesting email code")
            email_code_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[data-testid="challengePickerOption_EMAIL_OTP"]')))
            email_code_button.click()

            time.sleep(20)
            url = 'https://hook.us2.make.com/jajpooo7sbdvgasjgk2t5ql39ubjy4r0'

            while True:
                try:
                    response = requests.post(url)
                    if response.status_code == 200 and response.text.strip():
                        try:
                            result = response.json()
                            code = result.get('code')
                            if code:
                                logger.info(f"Code received: {code}")
                                break
                            else:
                                logger.warning("Code not found in response, retrying...")
                        except requests.exceptions.JSONDecodeError:
                            logger.error("Error decoding JSON response.")
                    else:
                        logger.warning("Empty or invalid response from Make.com.")
                except Exception as e:
                    logger.error(f"Exception while retrieving 2FA code: {e}")

            input_field = wait.until(EC.visibility_of_element_located((By.ID, 'ius-mfa-confirm-code')))
            input_field.send_keys(code)
            continue_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[data-testid="VerifyOtpSubmitButton"]')))
            continue_button.click()
            time.sleep(5)

        except Exception as e:
            logger.warning("'Email a code' not found or 2FA failed: %s", e)

        try:
            skip_btn = WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.ID, "skipPasskeyRegistration")))
            skip_btn.click()
        except:
            pass
        time.sleep(10)
        logger.info("Navigating to invoices page")
        driver.get('https://qbo.intuit.com/app/invoices')
        time.sleep(10)

        try:
            account_choice_button = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[data-testid="AccountChoiceButton_0"]'))
            )
            account_choice_button.click()
            logger.info("✅ Clicked account choice button.")
        except TimeoutException:
            logger.warning("⚠️ Account choice button not found, continuing.")

        create_invoice_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//span[text()='Create invoice']/ancestor::button")))
        create_invoice_btn.click()

        time.sleep(15)
        ref_input = wait.until(EC.presence_of_element_located((By.XPATH, "//input[@data-automation-id='input-ref-number-sales']")))
        invoice_number = ref_input.get_attribute("value")
        logger.info(f"Invoice number generated: {invoice_number}")

        time.sleep(10)
        customer_input = driver.find_element(By.XPATH, '//input[@placeholder="Select a customer" and @aria-label="Select a customer"]')
        customer_input.send_keys(Keys.CONTROL, 'a')
        customer_input.send_keys(Keys.BACKSPACE)
        customer_input.send_keys(customer)
        time.sleep(2)
        customer_input.send_keys(Keys.RETURN)

        invoice_date = wait.until(EC.element_to_be_clickable((By.ID, "uniqName_8_5")))
        invoice_date.send_keys(Keys.CONTROL, 'a')
        invoice_date.send_keys(Keys.BACKSPACE)
        invoice_date.send_keys(shipping_date)
        time.sleep(2)
        invoice_date.send_keys(Keys.RETURN)

        shipping_date_input = wait.until(EC.element_to_be_clickable((By.ID, "uniqName_8_8")))
        shipping_date_input.send_keys(Keys.CONTROL, 'a')
        shipping_date_input.send_keys(Keys.BACKSPACE)
        shipping_date_input.send_keys(shipping_date)
        time.sleep(2)
        shipping_date_input.send_keys(Keys.RETURN)

        carrier_input = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "input[data-qbo-bind='value: shippingInfo_shipVia']")))
        carrier_input.send_keys(Keys.CONTROL, 'a')
        carrier_input.send_keys(Keys.BACKSPACE)
        carrier_input.send_keys(carrier)
        time.sleep(2)
        carrier_input.send_keys(Keys.RETURN)

        po_input = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'ha-text-field[label="PO Number"] input.ha-input')))
        po_input.send_keys(Keys.CONTROL, 'a')
        po_input.send_keys(Keys.BACKSPACE)
        po_input.send_keys(po_numer)
        time.sleep(2)
        po_input.send_keys(Keys.RETURN)

        td_element = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "td.dgrid-column-3.clickable.field-itemId")))
        td_element.click()
        typeahead_input = wait.until(EC.element_to_be_clickable((By.XPATH, "//input[@placeholder='Select a product/service']")))
        typeahead_input.clear()
        typeahead_input.send_keys("Abilify 10mg 30 Tabs")
        time.sleep(2)
        typeahead_input.send_keys(Keys.RETURN)
        time.sleep(10)
        ref_input.click()
        time.sleep(10)

        save_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[data-automation-id="btn-footer-save"]')))
        driver.execute_script("arguments[0].scrollIntoView(true);", save_button)
        time.sleep(0.5)
        save_button.click()
        # time.sleep(2)
        # try:
        #     dialog = wait.until(
        #         EC.visibility_of_element_located((By.ID, "yesNoDialog"))
        #     )
        #     yes_btn = dialog.find_element(By.CSS_SELECTOR, "button.button.primary")
        #     yes_btn.click()
        #     logger.info(f"Invoice number is duplicated, but was handled: {invoice_number}")
        # except Exception as e:
        #     logger.warning(f"Could not handle duplicate-invoice dialog or it wasn't found: {e}")

        time.sleep(5)

        try:
            toast = wait.until(EC.presence_of_element_located((
                By.XPATH, f"//div[contains(@class,'toast-message-view')]//a[contains(@class, 'txnStatus') and contains(text(), 'Invoice {invoice_number} saved')]"
            )))
            invoice_text = toast.text
            invoice_link = toast.get_attribute('href')
            logger.info(f"✅ {invoice_text}")

            txn_id = invoice_link.split("txnId=")[-1] if "txnId=" in invoice_link else None

            return {"status": "success", "invoice_number": invoice_number, "txn_id": txn_id}

        except TimeoutException:
            logger.warning("⚠️ Toast message not detected. Save likely failed.")
            return {"status": "error", "message": "Invoice save confirmation not detected."}

    except Exception as e:
        logger.error("❌ Exception in update_invoice: %s", traceback.format_exc())
        return {"status": "error", "message": str(e)}

    finally:
        if driver:
            driver.quit()

def create_invoice_pdf(invoice_number):
    chrome_options = ChromeOptions()
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")

    driver = None
    try:
        logger.info(f"🧾 Starting PDF generation for invoice {invoice_number}")
        driver = webdriver.Chrome(options=chrome_options)
        wait = WebDriverWait(driver, 30)

        driver.get('https://accounts.intuit.com/index.html')
        email = wait.until(EC.presence_of_element_located((By.ID, "iux-identifier-first-unknown-identifier")))
        email.click()
        email.send_keys("rami.sbaity@empiremedia.io")
        wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button[data-testid='IdentifierFirstSubmitButton']"))).click()

        wait.until(EC.presence_of_element_located((By.ID, 'iux-password-confirmation-password'))).send_keys('Ha:inC6wJTYf.WW')
        driver.find_element(By.CSS_SELECTOR, 'button[data-testid="passwordVerificationContinueButton"]').click()

        try:
            skip_btn = WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.ID, "skipPasskeyRegistration")))
            skip_btn.click()
        except:
            pass

        try:
            email_code_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[data-testid="challengePickerOption_EMAIL_OTP"]')))
            email_code_button.click()

            time.sleep(20)
            url = 'https://hook.us2.make.com/jajpooo7sbdvgasjgk2t5ql39ubjy4r0'
            while True:
                try:
                    response = requests.post(url)
                    if response.status_code == 200 and response.text.strip():
                        result = response.json()
                        code = result.get('code')
                        if code:
                            break
                except Exception as e:
                    logger.error(f"An error occurred while retrieving 2FA code: {e}")

            input_field = wait.until(EC.visibility_of_element_located((By.ID, 'ius-mfa-confirm-code')))
            input_field.send_keys(code)
            continue_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[data-testid="VerifyOtpSubmitButton"]')))
            continue_button.click()
            time.sleep(5)

        except Exception as e:
            logger.warning(f"⚠️ 'Email a code' not found or failed: {e}")

        try:
            skip_btn = WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.ID, "skipPasskeyRegistration")))
            skip_btn.click()
        except:
            pass

        time.sleep(5)
        pdf_url = (
            f"https://qbo.intuit.com/api/neo/v1/company/9130348649068986/purchsales/packingslip/print"
            f"?txnId={invoice_number}&intuit_apikey=prdakyresscUcjdZm7GGD9IYrZAx68DcdNG2Mlb7"
            f"&intuit-company-id=9130348649068986"
        )

        driver.get(pdf_url)
        time.sleep(5)

        selenium_cookies = driver.get_cookies()
        session = requests.Session()
        for cookie in selenium_cookies:
            session.cookies.set(cookie['name'], cookie['value'])

        pdf_response = session.get(pdf_url)
        if pdf_response.status_code == 200:
            logger.info(f"✅ Successfully downloaded invoice PDF for {invoice_number}")
            return send_file(
                BytesIO(pdf_response.content),
                mimetype='application/pdf',
                download_name=f'PS-{invoice_number}.pdf'
            )
        else:
            logger.error(f"❌ Failed to download invoice PDF. Status: {pdf_response.status_code}")
            return jsonify({"error": "Failed to download PS PDF."}), 500

    except Exception as e:
        logger.exception(f"💥 Exception occurred while generating invoice PDF for {invoice_number}")
        return jsonify({"error": str(e)}), 500

    finally:
        if driver:
            driver.quit()

def create_po_pdf(po_number):
    chrome_options = ChromeOptions()
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    driver = None
    try:
        driver = webdriver.Chrome(options=chrome_options)
        wait = WebDriverWait(driver, 30)

        driver.get('https://accounts.intuit.com/index.html')
        email = wait.until(EC.presence_of_element_located((By.ID, "iux-identifier-first-unknown-identifier")))
        email.click()
        email.send_keys("rami.sbaity@empiremedia.io")
        wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button[data-testid='IdentifierFirstSubmitButton']"))).click()

        wait.until(EC.presence_of_element_located((By.ID, 'iux-password-confirmation-password'))).send_keys('Ha:inC6wJTYf.WW')
        driver.find_element(By.CSS_SELECTOR, 'button[data-testid="passwordVerificationContinueButton"]').click()

        try:
            skip_btn = WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.ID, "skipPasskeyRegistration")))
            skip_btn.click()
        except:
            pass

        try:
            email_code_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[data-testid="challengePickerOption_EMAIL_OTP"]')))
            email_code_button.click()

            time.sleep(20)
            url = 'https://hook.us2.make.com/jajpooo7sbdvgasjgk2t5ql39ubjy4r0'
            while True:
                try:
                    response = requests.post(url)
                    if response.status_code == 200 and response.text.strip():
                        result = response.json()
                        code = result.get('code')
                        if code:
                            break
                except Exception as e:
                    logger.error(f"An error occurred: {e}")

            input_field = wait.until(EC.visibility_of_element_located((By.ID, 'ius-mfa-confirm-code')))
            input_field.send_keys(code)

            continue_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[data-testid="VerifyOtpSubmitButton"]')))
            continue_button.click()
            time.sleep(5)

        except Exception as e:
            logger.warning("⚠️ 'Email a code' not found: %s", e)

        try:
            skip_btn = WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.ID, "skipPasskeyRegistration")))
            skip_btn.click()
        except:
            pass

        time.sleep(2)
        pdf_url = (
            f"https://qbo.intuit.com/api/neo/v1/company/9130348649068986/purchsales/print"
            f"?&txnId={po_number}&txnTypeId=46"
            f"&intuit_apikey=prdakyres3okyVenYTeeGSQw6MhqBfy9tU0N7jvO"
            f"&intuit-company-id=9130348649068986"
        )

        driver.get(pdf_url)
        time.sleep(5)

        selenium_cookies = driver.get_cookies()
        session = requests.Session()
        for cookie in selenium_cookies:
            session.cookies.set(cookie['name'], cookie['value'])

        pdf_response = session.get(pdf_url)
        if pdf_response.status_code == 200:
            return send_file(
                BytesIO(pdf_response.content),
                mimetype='application/pdf',
                download_name=f'PO-{po_number}.pdf'
            )
        else:
            return jsonify({"error": "Failed to download PO PDF."}), 500

    except Exception as e:
        logger.exception("Exception occurred while generating PO PDF.")
        return jsonify({"error": str(e)}), 500

    finally:
        if driver:
            driver.quit()

def fix_invoice_price(invoice_number):
    chrome_options = ChromeOptions()
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")

    driver = None
    response = None

    try:
        driver = webdriver.Chrome(options=chrome_options)
        wait = WebDriverWait(driver, 30)

        logger.info("Navigating to login page...")
        driver.get('https://accounts.intuit.com/index.html')
        email = wait.until(EC.presence_of_element_located((By.ID, "iux-identifier-first-unknown-identifier")))
        email.click()
        email.send_keys("rami.sbaity@empiremedia.io")
        wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button[data-testid='IdentifierFirstSubmitButton']"))).click()

        wait.until(EC.presence_of_element_located((By.ID, 'iux-password-confirmation-password'))).send_keys('Ha:inC6wJTYf.WW')
        driver.find_element(By.CSS_SELECTOR, 'button[data-testid="passwordVerificationContinueButton"]').click()

        try:
            skip_btn = WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.ID, "skipPasskeyRegistration")))
            skip_btn.click()
        except:
            pass

        try:
            email_code_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[data-testid="challengePickerOption_EMAIL_OTP"]')))
            email_code_button.click()

            logger.info("Waiting for 2FA email code...")
            time.sleep(20)
            url = 'https://hook.us2.make.com/jajpooo7sbdvgasjgk2t5ql39ubjy4r0'
            while True:
                try:
                    response_post = requests.post(url)
                    if response_post.status_code == 200 and response_post.text.strip():
                        result = response_post.json()
                        code = result.get('code')
                        if code:
                            logger.info("Received code: %s", code)
                            break
                except Exception as e:
                    logger.error(f"An error occurred fetching 2FA code: {e}")

            input_field = wait.until(EC.visibility_of_element_located((By.ID, 'ius-mfa-confirm-code')))
            input_field.send_keys(code)
            continue_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[data-testid="VerifyOtpSubmitButton"]')))
            continue_button.click()
            time.sleep(5)

        except Exception as e:
            logger.warning("⚠️ 'Email a code' step failed: %s", e)

        try:
            skip_btn = WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.ID, "skipPasskeyRegistration")))
            skip_btn.click()
        except:
            pass

        time.sleep(10)
        logger.info(f"Navigating to invoice page...")
        driver.get("https://qbo.intuit.com/")
        time.sleep(10)
        driver.execute_script(f"window.location.href = 'https://qbo.intuit.com/app/invoice?txnId={invoice_number}'")
        time.sleep(10)

        wait.until(EC.presence_of_element_located((By.XPATH, '//table[contains(@class, "dgrid-row-table")]')))
        rows = driver.find_elements(By.XPATH, '//div[@role="row" and contains(@class, "dgrid-row")]')
        logger.info("Found %d rows", len(rows))

        for row in rows:
            rate_cell = row.find_element(By.XPATH, './/td[contains(@class, "field-rate")]')
            driver.execute_script("arguments[0].scrollIntoView(true);", rate_cell)
            time.sleep(0.3)
            try:
                rate_cell.click()
                logger.info("✅ Clicked rate cell in row")
            except ElementClickInterceptedException as e:
                logger.warning("⚠️ Click intercepted: %s", str(e))
            except Exception as e:
                logger.error("❌ Unexpected error during click: %s", str(e))
            time.sleep(5)
            break

        customer_input = driver.find_element(By.XPATH, '//input[@placeholder="Select a customer" and @aria-label="Select a customer"]')
        driver.execute_script("arguments[0].scrollIntoView(true);", customer_input)
        customer_name = customer_input.get_attribute("value")
        logger.info("Customer name: %s", customer_name)
        customer_input.send_keys(Keys.CONTROL, 'a')
        customer_input.send_keys(Keys.BACKSPACE)
        customer_input.send_keys("SERCOTECH SWISS SAGL")
        time.sleep(2)
        customer_input.send_keys(Keys.RETURN)
        time.sleep(5)

        rows = driver.find_elements(By.XPATH, '//div[@role="row" and contains(@class, "dgrid-row")]')
        logger.info("Found %d rows", len(rows))

        for row in rows:
            rate_cell = row.find_element(By.XPATH, './/td[contains(@class, "field-rate")]')
            driver.execute_script("arguments[0].scrollIntoView(true);", rate_cell)
            time.sleep(0.3)
            try:
                rate_cell.click()
                logger.info("✅ Clicked rate cell in row")
            except ElementClickInterceptedException as e:
                logger.warning("⚠️ Click intercepted: %s", str(e))
            except Exception as e:
                logger.error("❌ Unexpected error during click: %s", str(e))
            time.sleep(5)
            break
        time.sleep(5)
        driver.execute_script("arguments[0].scrollIntoView(true);", customer_input)
        customer_input.send_keys(Keys.CONTROL, 'a')
        customer_input.send_keys(Keys.BACKSPACE)
        customer_input.send_keys(customer_name)
        time.sleep(2)
        customer_input.send_keys(Keys.RETURN)
        time.sleep(5)

        save_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[data-automation-id="btn-footer-save"]')))
        driver.execute_script("arguments[0].scrollIntoView(true);", save_button)
        time.sleep(0.5)
        save_button.click()
        time.sleep(5)

        response = jsonify({"message": f"Invoice processed successfully."}), 200

    except Exception as e:
        logger.exception(f"❌ Main process error {e.__class__.__name__}: {e}")
        response = jsonify({"error": str(e)}), 500

    finally:
        if driver:
            driver.quit()
            logger.info("Browser closed.")

    return response

# update invoice number
@app.route('/invoice', methods=['POST'])
def invoice_route():
    data = request.get_json()
    customer = data.get('customer')
    shipping_date = data.get('shipping_date')
    carrier = data.get('carrier')
    po_number = data.get('po_number')

    if not customer:
        return jsonify({"status": "error", "message": "Missing required fields"}), 400

    result = update_invoice(customer, shipping_date, carrier, po_number)

    if result.get("status") == "error":
        return jsonify(result), 500

    return jsonify(result)

# print invoice
@app.route('/print/invoice', methods=['POST'])
def print_invoice_route():
    data = request.get_json()
    invoice_number = data.get("invoice_number")

    if not invoice_number:
        return jsonify({"error": "Missing 'invoice_number' in request body."}), 400

    return create_invoice_pdf(invoice_number)

# print po
@app.route('/print/po', methods=['POST'])
def print_po_route():
    data = request.get_json()
    po_number = data.get("po_number")

    if not po_number:
        return jsonify({"error": "Missing 'po_number' in request body."}), 400

    return create_po_pdf(po_number)

@app.route('/prices/invoice', methods=['POST'])
def fix_invoice_route():
    data = request.get_json()
    invoice_number = data.get("invoice_number")

    if not invoice_number:
        return jsonify({"error": "Missing 'invoice_number' in request body."}), 400

    return fix_invoice_price(invoice_number)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5009)