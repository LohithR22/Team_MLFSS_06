from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time
import re
import json
headless = True 
options = Options()
if headless:
    options.add_argument("--headless=new")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")


def scrape_apollo(medicine_name: str, headless: bool = False) -> dict:
    # Helper: safe filename suffix
    def _slugify(name: str) -> str:
        return re.sub(r'[^a-zA-Z0-9_-]+', '_', name).strip('_').lower()

    # Helper: extract numeric price from string
    def extract_price(price_text: str) -> float:
        try:
            match = re.search(r'[\d,]+\.?\d*', price_text.replace(',', ''))
            return float(match.group()) if match else float('inf')
        except Exception:
            return float('inf')

    search_url = f"https://www.apollopharmacy.in/search-medicines/{medicine_name}"
    products = []
    best_choice = None
    alternatives = []
    error_msg = None
    driver = None
    try:
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        driver.get(search_url)

        # Wait for main product grid to appear
        try:
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((
                    By.XPATH,
                    "/html/body/div[2]/div[2]/div[1]/div[2]/div[3]/div/div/div/div/div[1]"
                ))
            )
        except Exception:
            error_msg = "Product grid did not load in time."
            # Build and persist minimal result before returning
            result = {
                "medicine_query": medicine_name,
                "search_url": search_url,
                "timestamp": time.time(),
                "products": [],
                "best_choice": None,
                "alternatives": [],
                "error": error_msg,
            }
            filename = f"apollo_{_slugify(medicine_name)}.json"
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            return result

        time.sleep(3)  # small buffer for content render

        # Extract up to 5 products via incremental XPaths
        for i in range(1, 6):
            try:
                name_xpath = f"/html/body/div[2]/div[2]/div[1]/div[2]/div[3]/div/div/div/div/div[1]/div[{i}]/div/div/a/div/div[2]/div[1]/h2[1]"
                price_xpath = f"/html/body/div[2]/div[2]/div[1]/div[2]/div[3]/div/div/div/div/div[1]/div[{i}]/div/div/a/div/div[2]/div[2]/div[2]/p[1]"
                link_xpath = f"/html/body/div[2]/div[2]/div[1]/div[2]/div[3]/div/div/div/div/div[1]/div[{i}]/div/div/a"

                try:
                    name = driver.find_element(By.XPATH, name_xpath).text
                except Exception:
                    name = "N/A"

                try:
                    price = driver.find_element(By.XPATH, price_xpath).text
                except Exception:
                    price = "N/A"

                try:
                    link = driver.find_element(By.XPATH, link_xpath).get_attribute("href")
                except Exception:
                    link = "N/A"

                products.append({
                    "index": i,
                    "name": name,
                    "price": price,
                    "price_value": extract_price(price),
                    "link": link
                })
            except Exception:
                # Skip if product block not found
                continue

        # Determine best choice and alternatives
        if products:
            best_choice = min(products, key=lambda x: x["price_value"])
            alternatives = [p for p in products if p["index"] != best_choice["index"]]
        else:
            error_msg = "No products found."

        # Build result payload
        result = {
            "medicine_query": medicine_name,
            "search_url": search_url,
            "timestamp": time.time(),
            "products": products,
            "best_choice": best_choice,
            "alternatives": alternatives,
            "error": error_msg,
        }

        # Write JSON file
        filename = f"apollo_{_slugify(medicine_name)}.json"
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        return result

    finally:
        if driver is not None:
            driver.quit()
            
scrape_apollo("dolo")