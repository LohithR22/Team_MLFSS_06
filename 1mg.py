from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time
import json

# --------------------------------
# CONFIGURATION
# --------------------------------
medicine_name = "Paracetamol"  # Change this to any medicine
headless = False               # True = background run
# --------------------------------

def main():
    # Chrome setup
    options = Options()
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    # Initialize driver
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    # Open Apollo Pharmacy website
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

# Call the main function
if __name__ == "__main__":
    search_results = main()
    print(search_results)
