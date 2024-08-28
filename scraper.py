import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import traceback

def init_driver():
    chrome_options = Options()
    profile_path = r'C:\Users\User\AppData\Local\Google\Chrome\User Data\Default'
    chrome_options.add_argument(f"user-data-dir={profile_path}")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("start-maximized")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    return webdriver.Chrome(options=chrome_options)

def set_departure_from_athens(driver):
    try:
        from_field = WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.ID, 'AirportFromSelect')))
        from_field.click()  # Click the field to ensure it's active
        from_field.clear()
        from_field.send_keys("Athens")  # Start typing 'Athens' to trigger the dropdown
        time.sleep(2)  # Allow time for autocomplete suggestions to appear
        
        # Wait for the autocomplete suggestions to be visible
        suggestions = WebDriverWait(driver, 10).until(
            EC.visibility_of_all_elements_located((By.CSS_SELECTOR, 'ul.ui-menu.ui-widget.ui-widget-content.ui-autocomplete.ui-front li.ui-menu-item'))
        )
        
        # Loop through the visible suggestions and click the correct one
        for suggestion in suggestions:
            if "Athens (ATH)" in suggestion.text:
                suggestion.click()  # Click the exact suggestion
                break
        time.sleep(0.5)  # A brief pause after selecting from the suggestions
    except Exception as e:
        print(f"Error setting departure from Athens: {e}")
        traceback.print_exc()

def get_destinations(driver):
    try:
        WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.ID, 'AirportToSelect'))).click()
        time.sleep(2)  # Wait for dropdown to fully load
        destinations = driver.find_elements(By.CSS_SELECTOR, 'ul.ui-menu.ui-widget.ui-widget-content.ui-autocomplete.ui-front li.ui-menu-item')
        destination_list = [destination.text for destination in destinations if destination.text != '']
        return destination_list
    except Exception as e:
        print(f"Error getting destinations: {e}")
        traceback.print_exc()
        return []

def extract_prices(driver):
    try:
        # Extracting outbound prices
        outbound_prices = {}
        outbound_elements = driver.find_elements(By.CSS_SELECTOR, 'ul[ng-model="Outbound"] li')
        for element in outbound_elements:
            month = element.find_element(By.CSS_SELECTOR, 'p.month').text.strip()
            price_text = element.find_element(By.CSS_SELECTOR, 'p.price').text.strip().replace('€', '').replace(',', '')
            if price_text:  # Only process non-empty price texts
                try:
                    price = float(price_text)
                    outbound_prices[month] = price
                except ValueError:
                    print(f"Warning: Skipping invalid price for {month}: '{price_text}'")

        # Extracting inbound prices
        inbound_prices = {}
        inbound_elements = driver.find_elements(By.CSS_SELECTOR, 'ul[ng-model="Inbound"] li')
        for element in inbound_elements:
            month = element.find_element(By.CSS_SELECTOR, 'p.month').text.strip()
            price_text = element.find_element(By.CSS_SELECTOR, 'p.price').text.strip().replace('€', '').replace(',', '')
            if price_text:  # Only process non-empty price texts
                try:
                    price = float(price_text)
                    if month in outbound_prices:
                        inbound_prices[month] = price + outbound_prices[month]
                    else:
                        inbound_prices[month] = price
                except ValueError:
                    print(f"Warning: Skipping invalid price for {month}: '{price_text}'")

        # Combine outbound and inbound prices
        combined_prices = {month: outbound_prices.get(month, 0) + inbound_prices.get(month, 0)
                           for month in set(outbound_prices) | set(inbound_prices)}

        return combined_prices
    except Exception as e:
        print(f"Error extracting prices: {e}")
        traceback.print_exc()
        return {}

def scrape_aegean_places():
    driver = init_driver()
    url = 'https://en.aegeanair.com/flight-deals/low-fare-calendar/'
    driver.get(url)
    time.sleep(2)  # Ensure the page is fully loaded

    set_departure_from_athens(driver)
    destinations = get_destinations(driver)

    # Print all extracted destinations
    print("Extracted destinations:")
    for dest in destinations:
        print(dest)
    print("------")

    for place in destinations:
        print(f"Starting to process {place}...")
        
        try:
            input_field = WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.ID, 'AirportToSelect')))
            input_field.clear()
            input_field.send_keys(place)
            time.sleep(2)  # Increased delay to ensure dropdown interaction is complete
            input_field.send_keys(Keys.RETURN)
            
            print(f"Entered {place} and triggered search")
            
            search_button = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.ID, 'lfc_mask_searchbutton')))
            driver.execute_script("arguments[0].click();", search_button)
            time.sleep(5)  # Wait for search results to process

            # Extract and print prices
            combined_prices = extract_prices(driver)
            if combined_prices:
                print(f"Athens-{place}:")
                for month, price in sorted(combined_prices.items()):
                    print(f"{month} {price:.2f}€")
                print("-------------------")
            print(f"Finished processing {place}")
            
        except Exception as e:
            print(f"Failed to process {place}: {e}")
            traceback.print_exc()
            # Continue with the next place even if there's a failure
            continue
        
        print(f"Completed all steps for {place}")

    print("All destinations processed, quitting driver...")
    driver.quit()

if __name__ == "__main__":
    scrape_aegean_places()
