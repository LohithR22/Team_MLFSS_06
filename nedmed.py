from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time

# --------------------------------
# CONFIGURATION
# --------------------------------
medicine_name = "Paracetamol"  # Change this to any medicine
headless = False               # True = background run
# --------------------------------

# Chrome setup
options = Options()
if headless:
    options.add_argument("--headless=new")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")

# Initialize driver
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

# Open Netmeds search results page directly
search_url = f"https://www.netmeds.com/products?q={medicine_name}"
driver.get(search_url)
driver.maximize_window()

# Wait for the page to load
time.sleep(1)

# print(f"✅ Opened search results for: {medicine_name}")

# ✅ Extract 5 products using incremental ID
# print(f"\nExtracting medicines for '{medicine_name}':\n")
print("=" * 80)

for i in range(5):  # 0 to 4 (5 products)
    div_id = f"intersection-observer-div{i}"
    
    try:
        element = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.ID, div_id))
        )
        
        # Get all text content from the div
        all_text = element.text
        
        # Filter out unwanted lines
        lines = all_text.split('\n')
        filtered_lines = []
        
        for line in lines:
            # Skip lines containing strikethrough prices (₹X.XX ₹X.XX X% OFF pattern)
            if 'OFF' in line and '₹' in line:
                continue
            # Skip "Add" button text
            if line.strip() == 'Add':
                continue
            # Skip delivery information
            if line.startswith('Delivery:') or 'Delivery' in line:
                continue
            # Skip single-word lines that appear to be tags (like "Fever")
            if len(line.split()) == 1 and line.strip() not in ['By', 'Best']:
                # Check if it's not part of important info
                if not line.startswith('₹'):
                    continue
            
            filtered_lines.append(line)
        
        filtered_text = '\n'.join(filtered_lines)
        
        # Label first product as "Best Choice" and rest as "Alternate Medicine"
        if i == 0:
            print(f"🏆 BEST CHOICE:")
        else:
            print(f"💊 ALTERNATE MEDICINE {i}:")
        
        print(f"{filtered_text}")
        print("-" * 80)
        
    except Exception as e:
        if i == 0:
            print(f"🏆 BEST CHOICE: Not found - {str(e)}\n")
        else:
            print(f"💊 ALTERNATE MEDICINE {i}: Not found - {str(e)}\n")


# print("Extraction complete!")