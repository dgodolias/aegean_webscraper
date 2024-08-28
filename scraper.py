import time
from bs4 import BeautifulSoup
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

def get_dropdown_div_html(driver):
    try:
        # Click the "To" field to trigger the dropdown
        to_field = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.ID, 'AirportToSelect')))
        to_field.click()
        time.sleep(2)  # Wait for dropdown to load

        # Locate the container holding the list of destinations
        dropdown_div = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'div.ddList.autocomplete.mCustomScrollbar'))
        )

        # Scroll to the bottom of the dropdown to ensure all items are loaded
        driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", dropdown_div)
        time.sleep(2)  # Wait for all items to load

        # Return the outer HTML of the dropdown div
        return dropdown_div.get_attribute('outerHTML')

    except Exception as e:
        print(f"Error getting dropdown div: {e}")
        traceback.print_exc()
        return ""

def extract_prices(driver):
    try:
        # Capture the order of months as displayed on the site
        month_order = []
        outbound_elements = driver.find_elements(By.CSS_SELECTOR, 'ul[ng-model="Outbound"] li')
        for element in outbound_elements:
            month = element.find_element(By.CSS_SELECTOR, 'p.month').text.strip()
            month_order.append(month)
        
        # Extract outbound prices
        outbound_prices = {}
        for element in outbound_elements:
            month = element.find_element(By.CSS_SELECTOR, 'p.month').text.strip()
            price_text = element.find_element(By.CSS_SELECTOR, 'p.price').text.strip().replace('€', '').replace(',', '')
            if price_text:  # Only process non-empty price texts
                try:
                    price = float(price_text)
                    outbound_prices[month] = price
                except ValueError:
                    print(f"Warning: Skipping invalid price for {month}: '{price_text}'")

        # Extract inbound prices
        inbound_prices = {}
        inbound_elements = driver.find_elements(By.CSS_SELECTOR, 'ul[ng-model="Inbound"] li')
        for element in inbound_elements:
            month = element.find_element(By.CSS_SELECTOR, 'p.month').text.strip()
            price_text = element.find_element(By.CSS_SELECTOR, 'p.price').text.strip().replace('€', '').replace(',', '')
            if price_text:  # Only process non-empty price texts
                try:
                    price = float(price_text)
                    inbound_prices[month] = price
                except ValueError:
                    print(f"Warning: Skipping invalid price for {month}: '{price_text}'")

        # Combine outbound and inbound prices
        combined_prices = {}
        for month in month_order:
            outbound_price = outbound_prices.get(month, 0)
            inbound_price = inbound_prices.get(month, 0)
            combined_prices[month] = outbound_price + inbound_price

        return combined_prices, month_order
    except Exception as e:
        print(f"Error extracting prices: {e}")
        traceback.print_exc()
        return {}, []

def get_destinations(dropdown_div_html):
    try:
        # Parse the HTML using BeautifulSoup
        soup = BeautifulSoup(dropdown_div_html, 'html.parser')
        
        # Find all the list items (li elements) in the dropdown
        li_elements = soup.find_all('li', class_='ui-menu-item')
        
        # Extract the text from each li element
        destinations = [li.text.strip() for li in li_elements if li.text.strip()]
        
        return destinations
    
    except Exception as e:
        print(f"Error extracting destinations from HTML: {e}")
        return []

def scrape_aegean_places():
    driver = init_driver()
    url = 'https://en.aegeanair.com/flight-deals/low-fare-calendar/'
    driver.get(url)
    time.sleep(2)  # Ensure the page is fully loaded

    set_departure_from_athens(driver)
    dropdown_div_html = get_dropdown_div_html(driver)

    # Extracting the destinations list after scrolling the dropdown
    destinations = get_destinations(dropdown_div_html)

    # Print all the destinations
    print("Available destinations:")
    for place in destinations:
        print(place)
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
            combined_prices, month_order = extract_prices(driver)
            if combined_prices:
                print(f"Athens-{place}:")
                for month in month_order:
                    if month in combined_prices:
                        print(f"{month} {combined_prices[month]:.2f}€")
                print("-------------------")
            print(f"Finished processing {place}")
            
        except Exception as e:
            print(f"Failed to process {place}: {e}")
            traceback.print_exc()
            continue
        
        print(f"Completed all steps for {place}")

    print("All destinations processed, quitting driver...")
    driver.quit()

if __name__ == "__main__":
    scrape_aegean_places()
