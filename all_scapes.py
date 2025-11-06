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

#apollo
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
            
#nedmed
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
        
#1mg
def main_1mg(medicine_name):
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    # Open 1mg Pharmacy website
    driver.get("https://www.1mg.com/")
    driver.maximize_window()

    # Wait for the page to load
    time.sleep(1)

    # Close the popup if it appears
    try:
        close_popup_button = driver.find_element(By.XPATH, '//*[@id="top-div"]/button')
        close_popup_button.click()
    except:
        pass

    # Click on the specified element after closing the popup
    try:
        update_city_button = driver.find_element(By.XPATH, '//*[@id="update-city-modal"]/div/div[2]/div[1]')
        update_city_button.click()
    except:
        pass

    # Click search bar
    search_container = driver.find_element(By.XPATH, '//*[@id="srchBarShwInfo"]')
    search_container.click()
    time.sleep(0.5)

    # Enter medicine name using alternative XPath
    search_box = driver.find_element(By.XPATH, '//*[@id="srchBarShwInfo-form"]/input')
    search_box.clear()
    search_box.send_keys(medicine_name)

    # Click the search button
    search_button = driver.find_element(By.XPATH, '//*[@id="srchBarShwInfo-form"]/span/button')
    search_button.click()

    # ✅ Wait until the main product grid appears
    try:
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.XPATH, '//*[@id="category-container"]/div/div[3]'))
        )
    except:
        driver.quit()
        exit()

    time.sleep(0.5)

    results = search_medicine(driver, medicine_name)

    # Close the driver
    driver.quit()

    return results

def search_medicine(driver, medicine_name):
    results = []  # List to hold product results

    for i in range(1, 6):  # Get 5 products (div[1] to div[5])
        try:
            name = "N/A"
            price = "N/A"
            link = "N/A"
            
            # Try different div variations for name (div[2], div[3], div[4])
            for div_num in range(2, 5):
                try:
                    name_xpath = f'//*[@id="category-container"]/div/div[3]/div[2]/div[1]/div/div[2]/div[2]/div/div[{i}]/div/a/div[{div_num}]/span'
                    name = driver.find_element(By.XPATH, name_xpath).text
                    if name:  # If found, break the loop
                        break
                except:
                    continue
            
            # Try different price XPath patterns
            price_patterns = [
                f'//*[@id="category-container"]/div/div[3]/div[2]/div[1]/div/div[2]/div[2]/div/div[{i}]/div/a/div[3]/div/div[1]',
                f'//*[@id="category-container"]/div/div[3]/div[2]/div[1]/div/div[2]/div[2]/div/div[{i}]/div/a/div[4]/div/div[1]',
                f'//*[@id="category-container"]/div/div[3]/div[2]/div[1]/div/div[2]/div[2]/div/div[{i}]/div/a/div[3]/div',
                f'//*[@id="category-container"]/div/div[3]/div[2]/div[1]/div/div[2]/div[2]/div/div[{i}]/div/a/div[4]/div',
                f'//*[@id="category-container"]/div/div[3]/div[2]/div[1]/div/div[2]/div[2]/div/div[{i}]/div/a/div[5]/div/div[1]',
                f'//*[@id="category-container"]/div/div[3]/div[2]/div[1]/div/div[2]/div[2]/div/div[{i}]/div/a/div[5]/div',
            ]
            
            for price_xpath in price_patterns:
                try:
                    price = driver.find_element(By.XPATH, price_xpath).text
                    if price:  # If found, replace Unicode with ₹
                        price = price.replace('\u20b9', '₹')  # Replace Unicode with the actual symbol
                        break
                except:
                    continue
            
            # Get the link
            try:
                link_xpath = f'//*[@id="category-container"]/div/div[3]/div[2]/div[1]/div/div[2]/div[2]/div/div[{i}]/div/a'
                link = driver.find_element(By.XPATH, link_xpath).get_attribute("href")
            except:
                link = "N/A"
            
            # Append the product details to results
            results.append({
                "name": name,
                "price": price,
                "link": link
            })
        
        except Exception as e:
            if i == 1:
                results.append({"error": f"BEST MATCH: Product not found - {str(e)}"})
            else:
                results.append({"error": f"{i-1}. Product not found - {str(e)}"})

    # Save results to JSON file
    json_filename = f"1mg_{medicine_name}.json"
    with open(json_filename, 'w') as json_file:
        json.dump(results, json_file, indent=4)

    return results

# scrape_apollo("Dolo")
# scrape_nedmed("Dolo")
# main_1mg("Dolo")