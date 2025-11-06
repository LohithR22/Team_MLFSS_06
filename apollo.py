from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time
import re

# --------------------------------
# CONFIGURATION
# --------------------------------
medicine_name = "dolo"  # Change this to any medicine
headless = False        # True = background run
# --------------------------------

# Chrome setup
options = Options()
if headless:
    options.add_argument("--headless=new")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")

# Initialize driver
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

# Open Apollo Pharmacy search URL directly
search_url = f"https://www.apollopharmacy.in/search-medicines/{medicine_name}"
driver.get(search_url)
driver.maximize_window()

# ✅ Wait until the main product grid appears
try:
    WebDriverWait(driver, 15).until(
        EC.presence_of_element_located((By.XPATH, "/html/body/div[2]/div[2]/div[1]/div[2]/div[3]/div/div/div/div/div[1]"))
    )
    print("✅ Product grid loaded successfully.")
except:
    print("❌ Product grid did not load. Try increasing wait time.")
    driver.quit()
    exit()

time.sleep(3)

# Helper function to extract price as float
def extract_price(price_text):
    try:
        # Extract numeric value from price (e.g., "₹15.50" -> 15.50)
        match = re.search(r'[\d,]+\.?\d*', price_text.replace(',', ''))
        return float(match.group()) if match else float('inf')
    except:
        return float('inf')

# ✅ Extract 5 products using incremental XPath
print(f"\nExtracting top 5 products for '{medicine_name}':\n")

products = []

for i in range(1, 6):  # Get 5 products (div[1] to div[5])
    try:
        # Build XPaths with incrementing div index
        name_xpath = f"/html/body/div[2]/div[2]/div[1]/div[2]/div[3]/div/div/div/div/div[1]/div[{i}]/div/div/a/div/div[2]/div[1]/h2[1]"
        price_xpath = f"/html/body/div[2]/div[2]/div[1]/div[2]/div[3]/div/div/div/div/div[1]/div[{i}]/div/div/a/div/div[2]/div[2]/div[2]/p[1]"
        link_xpath = f"/html/body/div[2]/div[2]/div[1]/div[2]/div[3]/div/div/div/div/div[1]/div[{i}]/div/div/a"
        
        try:
            name = driver.find_element(By.XPATH, name_xpath).text
        except:
            name = "N/A"
        
        try:
            price = driver.find_element(By.XPATH, price_xpath).text
        except:
            price = "N/A"
        
        try:
            link = driver.find_element(By.XPATH, link_xpath).get_attribute("href")
        except:
            link = "N/A"
        
        products.append({
            'index': i,
            'name': name,
            'price': price,
            'price_value': extract_price(price),
            'link': link
        })
        
    except Exception as e:
        print(f"Product {i} not found - {str(e)}\n")

# Find the best choice (lowest price)
if products:
    best_choice = min(products, key=lambda x: x['price_value'])
    
    print("=" * 80)
    print("🏆 BEST CHOICE (Lowest Price)")
    print("=" * 80)
    print(f"✅ {best_choice['name']}")
    print(f"   💰 Price: {best_choice['price']}")
    print(f"   🔗 Link: {best_choice['link']}\n")
    
    print("=" * 80)
    print("🔄 ALTERNATIVE MEDICINES")
    print("=" * 80)
    
    # Show alternatives (remaining 4 medicines)
    alternatives = [p for p in products if p['index'] != best_choice['index']]
    
    for idx, product in enumerate(alternatives, 1):
        print(f"{idx}. {product['name']}")
        print(f"   💰 Price: {product['price']}")
        print(f"   🔗 Link: {product['link']}\n")
else:
    print("❌ No products found.")

driver.quit()


