import time
import os
import tempfile
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import traceback
from datetime import datetime
import threading

# Global lock for shared resource
lock = threading.Lock()
processed_destinations = []
global_min_prices = []

THREADS_NUM = 10


def init_driver(thread_id):
    chrome_options = Options()
    
    # Use a pre-configured user data directory if available, or create a new one.
    user_data_dir = os.path.join(tempfile.gettempdir(), f"chrome_profile_{thread_id}")
    chrome_options.add_argument(f"user-data-dir={user_data_dir}")
    
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("start-maximized")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--no-first-run")
    chrome_options.add_argument("--no-default-browser-check")
    chrome_options.add_argument("--disable-popup-blocking")
    chrome_options.add_argument("--disable-infobars")
    chrome_options.add_argument("--disable-notifications")

    return webdriver.Chrome(options=chrome_options)

def set_departure_from_athens(driver):
    try:
        from_field = WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.ID, 'AirportFromSelect')))
        from_field.click()
        from_field.clear()
        from_field.send_keys("Athens")
        time.sleep(1)
        
        suggestions = WebDriverWait(driver, 10).until(
            EC.visibility_of_all_elements_located((By.CSS_SELECTOR, 'ul.ui-menu.ui-widget.ui-widget-content.ui-autocomplete.ui-front li.ui-menu-item'))
        )
        
        for suggestion in suggestions:
            if "Athens (ATH)" in suggestion.text:
                suggestion.click()
                break
        time.sleep(0.5)
    except Exception as e:
        print(f"Error setting departure from Athens: {e}")
        traceback.print_exc()

def get_dropdown_div_html(driver):
    try:
        to_field = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.ID, 'AirportToSelect')))
        to_field.click()
        time.sleep(1)

        dropdown_div = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'div.ddList.autocomplete.mCustomScrollbar'))
        )

        driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", dropdown_div)
        time.sleep(1)
        
        return dropdown_div.get_attribute('outerHTML')

    except Exception as e:
        print(f"Error getting dropdown div: {e}")
        traceback.print_exc()
        return ""

def get_fares_html(driver):
    try:
        outbound_html = driver.find_element(By.CSS_SELECTOR, 'ul[ng-model="Outbound"]').get_attribute('outerHTML')
        inbound_html = driver.find_element(By.CSS_SELECTOR, 'ul[ng-model="Inbound"]').get_attribute('outerHTML')
        return outbound_html, inbound_html
    except Exception as e:
        print(f"Error getting fares HTML: {e}")
        traceback.print_exc()
        return "", ""

def extract_fares_from_html(fares_html):
    try:
        soup = BeautifulSoup(fares_html, 'html.parser')
        li_elements = soup.find_all('li')
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
    current_month = datetime.now().month
    months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    month_order = months[current_month - 1:] + months[:current_month - 1]
    
    return month_order

def get_destinations(dropdown_div_html):
    try:
        soup = BeautifulSoup(dropdown_div_html, 'html.parser')
        li_elements = soup.find_all('li', class_='ui-menu-item')
        destinations = [li.text.strip() for li in li_elements if li.text.strip()]
        return destinations
    
    except Exception as e:
        print(f"Error extracting destinations from HTML: {e}")
        return []

def scrape_aegean_places(thread_id):
    print(f"Thread {thread_id} started.")
    driver = init_driver(thread_id)
    url = 'https://en.aegeanair.com/flight-deals/low-fare-calendar/'
    driver.get(url)
    time.sleep(2)

    set_departure_from_athens(driver)
    dropdown_div_html = get_dropdown_div_html(driver)

    destinations = get_destinations(dropdown_div_html)

    print(f"Thread {thread_id} - Available destinations:")
    for place in destinations:
        print(place)
    print("------")

    month_order = get_month_order()

    local_min_prices = []

    for place in destinations:
        with lock:
            if place in processed_destinations:
                print(f"Thread {thread_id} - Skipping {place} as it has already been processed.")
                continue  # Skip if another thread already processed this destination

            # Mark this destination as being processed
            processed_destinations.append(place)

        print(f"Thread {thread_id} - Starting to process {place}...")

        try:
            input_field = WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.ID, 'AirportToSelect')))
            input_field.clear()
            input_field.send_keys(place)
            time.sleep(2)
            input_field.send_keys(Keys.RETURN)

            print(f"Thread {thread_id} - Entered {place} and triggered search")

            search_button = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.ID, 'lfc_mask_searchbutton')))
            driver.execute_script("arguments[0].click();", search_button)
            time.sleep(5)

            outbound_html, inbound_html = get_fares_html(driver)

            outbound_fares = extract_fares_from_html(outbound_html)
            inbound_fares = extract_fares_from_html(inbound_html)

            common_months = set(outbound_fares.keys()).intersection(inbound_fares.keys())

            combined_fares = {}
            for month in common_months:
                combined_fares[month] = outbound_fares[month] + inbound_fares[month]

            if combined_fares:
                min_price = min(combined_fares.values())
                min_months = [month for month, price in combined_fares.items() if price == min_price]
                local_min_prices.append((place, '/'.join(min_months), min_price))

            print(f"Thread {thread_id} - Finished processing {place}")

        except Exception as e:
            print(f"Thread {thread_id} - Failed to process {place}: {e}")
            traceback.print_exc()
            continue

        print(f"Thread {thread_id} - Completed all steps for {place}")

    # Merge local min prices with the global list
    with lock:
        global_min_prices.extend(local_min_prices)

    print(f"Thread {thread_id} - All destinations processed, quitting driver...")

    try:
        driver.quit()
    except Exception as e:
        print(f"Thread {thread_id} - Error quitting driver: {e}")

def main():
    threads = []
    for i in range(THREADS_NUM):  # Create 3 threads
        thread = threading.Thread(target=scrape_aegean_places, args=(i+1,))
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()

    # Print the combined results once all threads are done
    global_min_prices.sort(key=lambda x: x[2])

    print("\nFinal Sorted Destinations by Minimum Price:")
    for place, months, price in global_min_prices:
        print(f"{place} {months} {price:.2f}€")

if __name__ == "__main__":
    main()
