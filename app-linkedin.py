from flask import Flask, request, jsonify
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import os
import time

app = Flask(__name__)

EMAIL = os.getenv("LINKEDIN_EMAIL", "za6597718@gmail.com")
PASSWORD = os.getenv("LINKEDIN_PASSWORD", "Zainab914*")


def create_driver():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(options=options)
    driver.set_window_size(1366, 768)
    return driver


def try_login(driver,url):
    try:
        signin_btn = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Sign in') or contains(@data-tracking-control-name, 'login')]") )
        )
        signin_btn.click()
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "session_key"))).send_keys(EMAIL)
        driver.find_element(By.ID, "session_password").send_keys(PASSWORD)
        driver.find_element(By.XPATH, "//button[@type='submit']").click()
        time.sleep(3)
        about_url = url.rstrip('/') + '/about/'
        driver.get(about_url)
        time.sleep(3)
    except Exception:
        pass


def scrape_company_data(driver, url):
    driver.get(url)
    time.sleep(3)

    try:
        dismiss_btn = WebDriverWait(driver, 3).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button.contextual-sign-in-modal__modal-dismiss"))
        )
        dismiss_btn.click()
        time.sleep(1)
    except Exception:
        pass

    try_login(driver,url)

    data = {}

    def get_text(selector):
        try:
            return driver.find_element(By.CSS_SELECTOR, selector).text.strip()
        except:
            return None
    try:
        data['description'] = get_text('p.break-words')
    except:
        data['description'] = None
    data["website"] = get_text('[data-test-id="about-us__website"] a')
    data["industry"] = get_text('[data-test-id="about-us__industry"] dd')
    data["company_size"] = get_text('[data-test-id="about-us__size"] dd')
    data["headquarters"] = get_text('[data-test-id="about-us__headquarters"] dd')
    data["type"] = get_text('[data-test-id="about-us__organizationType"] dd')
    data["founded"] = get_text('[data-test-id="about-us__foundedOn"] dd')

    try:
        specialties = get_text('[data-test-id="about-us__specialties"] dd')
        if specialties:
            parts = [s.strip() for s in specialties.split(",") if s.strip()]
            data["specialties"] = ". ".join(parts) + "."
        else:
            data["specialties"] = ""
    except:
        data["specialties"] = ""

    affiliated_text = ""
    try:
        cards = driver.find_elements(By.CSS_SELECTOR, '[data-test-id="affiliated-pages"] li')
        pairs = []
        for card in cards:
            try:
                name = card.find_element(By.CSS_SELECTOR, ".base-aside-card__title").text.strip()
            except:
                name = None
            try:
                industry = card.find_element(By.CSS_SELECTOR, ".base-aside-card__subtitle").text.strip()
            except:
                industry = None
            if name:
                pair = f"{name}: {industry}" if industry else name
                pairs.append(pair)
        if pairs:
            affiliated_text = "\n".join(pairs)
    except:
        affiliated_text = ""

    data["affiliated_pages"] = affiliated_text
    return data


@app.route("/company", methods=["POST"])
def scrape_company():
    content = request.json or {}
    linkedin_url = content.get("linkedin_url")
    if not linkedin_url:
        return jsonify({"error": "linkedin_url is required"}), 400
    driver = create_driver()
    try:
        result = scrape_company_data(driver, linkedin_url)
    finally:
        driver.quit()
    return jsonify(result)


if __name__ == "__main__":
    app.run(port=5050, debug=True)
