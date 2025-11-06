from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time
# Chrome setup
headless = True
options = Options()
if headless:
    options.add_argument("--headless=new")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")

def scrape_nedmed(medicine_name: str, headless: bool = False) -> dict:
    import re
    import json

    def _slugify(name: str) -> str:
        return re.sub(r'[^a-zA-Z0-9_-]+', '_', name).strip('_').lower()

    def extract_price(text: str) -> float:
        try:
            # Pick the last number with optional decimals as price
            nums = re.findall(r'[\d,]+\.?\d*', text.replace(',', ''))
            return float(nums[-1]) if nums else float('inf')
        except Exception:
            return float('inf')

    search_url = f"https://www.netmeds.com/products?q={medicine_name}"
    products = []
    best_choice = None
    alternatives = []
    error_msg = None

    driver = None
    try:
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        driver.get(search_url)

        # Small buffer for content render
        time.sleep(1)

        for i in range(5):  # 0..4 (5 products)
            div_id = f"intersection-observer-div{i}"
            try:
                element = WebDriverWait(driver, 8).until(
                    EC.presence_of_element_located((By.ID, div_id))
                )

                all_text = element.text or ""
                lines = all_text.split('\n')

                filtered_lines = []
                for line in lines:
                    if not line.strip():
                        continue
                    # Drop discount strikethrough combos like "₹X ₹Y Z% OFF"
                    if 'OFF' in line and '₹' in line:
                        continue
                    # Drop 'Add' button text
                    if line.strip() == 'Add':
                        continue
                    # Drop delivery info
                    if line.startswith('Delivery:') or 'Delivery' in line:
                        continue
                    # Drop single-word tags while keeping currency lines
                    if len(line.split()) == 1 and not line.strip().startswith('₹'):
                        if line.strip() not in ['By', 'Best']:
                            continue
                    filtered_lines.append(line)

                filtered_text = '\n'.join(filtered_lines)

                # Try to extract name (first non-price line) and price
                name_guess = None
                price_guess = None
                for ln in filtered_lines:
                    if '₹' in ln and price_guess is None:
                        price_guess = ln
                    if name_guess is None and '₹' not in ln:
                        name_guess = ln
                    if name_guess and price_guess:
                        break

                # Try to get product link from first anchor in the block
                try:
                    link = element.find_element(By.TAG_NAME, "a").get_attribute("href")
                except Exception:
                    link = "N/A"

                products.append({
                    "index": i,
                    "label": "Best Choice" if i == 0 else f"Alternate Medicine {i}",
                    "name": name_guess or "N/A",
                    "price": price_guess or "N/A",
                    "price_value": extract_price(price_guess or filtered_text),
                    "raw_text": filtered_text,
                    "link": link
                })

            except Exception:
                # Skip if not found; keep place as missing entry for traceability
                products.append({
                    "index": i,
                    "label": "Best Choice" if i == 0 else f"Alternate Medicine {i}",
                    "name": "N/A",
                    "price": "N/A",
                    "price_value": float('inf'),
                    "raw_text": "",
                    "link": "N/A",
                    "error": f"Product block {div_id} not found"
                })

        # Determine best choice by minimum numeric price
        priced = [p for p in products if p["price_value"] != float('inf')]
        if priced:
            best_choice = min(priced, key=lambda x: x["price_value"])
            alternatives = [p for p in products if p["index"] != best_choice["index"]]
        else:
            error_msg = "No priced products found."
            best_choice = None
            alternatives = [p for p in products if p["index"] != 0]

        result = {
            "medicine_query": medicine_name,
            "search_url": search_url,
            "timestamp": time.time(),
            "products": products,
            "best_choice": best_choice,
            "alternatives": alternatives,
            "error": error_msg,
        }

        # Persist to nedmed_<medicine_name>.json
        filename = f"nedmed_{_slugify(medicine_name)}.json"
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        return result

    finally:
        if driver is not None:
            driver.quit()

scrape_nedmed("Dolo")