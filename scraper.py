import time
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import traceback
from datetime import datetime

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

def get_fares_html(driver):
    try:
        # Get the outbound and inbound fare HTML content after search
        outbound_html = driver.find_element(By.CSS_SELECTOR, 'ul[ng-model="Outbound"]').get_attribute('outerHTML')
        inbound_html = driver.find_element(By.CSS_SELECTOR, 'ul[ng-model="Inbound"]').get_attribute('outerHTML')
        return outbound_html, inbound_html
    except Exception as e:
        print(f"Error getting fares HTML: {e}")
        traceback.print_exc()
        return "", ""

def extract_fares_from_html(fares_html):
    try:
        # Parse the HTML using BeautifulSoup
        soup = BeautifulSoup(fares_html, 'html.parser')
        
        # Find all the list items (li elements) in the fares list
        li_elements = soup.find_all('li')
        
        # Extract the month and price from each li element
        fares = {}
        for li in li_elements:
            month = li.find('p', class_='month').text.strip()
            price_text = li.find('p', class_='price').text.strip().replace('€', '').replace(',', '')
            if price_text:
                try:
                    price = float(price_text)
                    fares[month] = price
                except ValueError:
                    print(f"Warning: Skipping invalid price for {month}: '{price_text}'")
        
        return fares
    except Exception as e:
        print(f"Error extracting fares from HTML: {e}")
        traceback.print_exc()
        return {}

def get_month_order():
    # Get the current month as an integer
    current_month = datetime.now().month

    # List of all months in order
    months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

    # Rotate the list so that the current month comes first
    month_order = months[current_month - 1:] + months[:current_month - 1]
    
    return month_order

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

    month_order = get_month_order()  # Get the month order based on the current month

    min_prices = []  # List to hold minimum price info for each destination

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

            # Get the outbound and inbound fares HTML
            outbound_html, inbound_html = get_fares_html(driver)

            # Extract the fares
            outbound_fares = extract_fares_from_html(outbound_html)
            inbound_fares = extract_fares_from_html(inbound_html)

            # Find the common months between outbound and inbound fares
            common_months = set(outbound_fares.keys()).intersection(inbound_fares.keys())

            # Combine the fares for the common months
            combined_fares = {}
            for month in common_months:
                combined_fares[month] = outbound_fares[month] + inbound_fares[month]

            # Find the minimum price and corresponding months
            if combined_fares:
                min_price = min(combined_fares.values())
                min_months = [month for month, price in combined_fares.items() if price == min_price]
                min_prices.append((place, '/'.join(min_months), min_price))

            print(f"Finished processing {place}")

        except Exception as e:
            print(f"Failed to process {place}: {e}")
            traceback.print_exc()
            continue

        print(f"Completed all steps for {place}")

    # Sort the destinations by the minimum price
    min_prices.sort(key=lambda x: x[2])

    # Print the sorted destinations
    print("\nSorted Destinations by Minimum Price:")
    for place, months, price in min_prices:
        print(f"{place} {months} {price:.2f}€")

    print("All destinations processed, quitting driver...")

    try:
        driver.quit()
    except Exception as e:
        print(f"Error quitting driver: {e}")


if __name__ == "__main__":
    scrape_aegean_places()