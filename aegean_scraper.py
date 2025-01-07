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

THREADS_NUM = 10  # Adjust as needed

# User-specified months, defaults to an empty list if not specified
user_specified_months = []

def init_driver(thread_id, retries=3):
    chrome_options = Options()
    
    # Use a unique temporary profile directory for each thread
    user_data_dir = os.path.join(tempfile.gettempdir(), f"chrome_profile_{thread_id}")
    chrome_options.add_argument(f"user-data-dir={user_data_dir}")

    # Chrome options for headless mode
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-software-rasterizer")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--remote-debugging-port=0")  # Avoid conflicts

    chrome_options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/91.0.4472.124 Safari/537.36"
    )

    for attempt in range(retries):
        try:
            return webdriver.Chrome(options=chrome_options)
        except Exception as e:
            print(f"Attempt {attempt + 1} to start Chrome failed for thread {thread_id}: {e}")
            time.sleep(2)
    print(f"Failed to initialize driver after {retries} attempts for thread {thread_id}")
    return None

def set_departure_from_athens(driver):
    """
    Clicks the 'From' input, types 'Athens', and picks 'Athens (ATH)'
    from the new dropdown structure.
    """
    try:
        from_field = WebDriverWait(driver, 20).until(
            EC.visibility_of_element_located((By.ID, 'AirportFromSelect'))
        )
        print(from_field.get_attribute('outerHTML'))
        from_field.click()
        from_field.clear()
        from_field.send_keys("")
        time.sleep(2)  # allow suggestions to appear

        # The new dropdown is typically "div.ddList.autocomplete..."
        dropdown_div = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, 'div.ddList.autocomplete.mCustomScrollbar')
            )
        )
        # Scroll it if needed
        driver.execute_script(
            "arguments[0].scrollTop = arguments[0].scrollHeight", dropdown_div
        )
        time.sleep(1)

        # Now find all possible li's inside the dropdown
        suggestions = dropdown_div.find_elements(By.CSS_SELECTOR, "ul li")
        for suggestion in suggestions:
            if "Athens (ATH)" in suggestion.text:
                suggestion.click()
                break
        time.sleep(1)
    except Exception as e:
        print(f"Error setting departure from Athens: {e}")
        traceback.print_exc()

def get_dropdown_div_html(driver):
    """
    Click 'To' field, wait for the new dropdown, scroll, return outer HTML.
    """
    try:
        to_field = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, 'AirportToSelect'))
        )
        to_field.click()
        time.sleep(2)  # let suggestions load

        dropdown_div = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, 'div.ddList.autocomplete.mCustomScrollbar')
            )
        )

        # Scroll the dropdown to load more items
        driver.execute_script(
            "arguments[0].scrollTop = arguments[0].scrollHeight", dropdown_div
        )
        time.sleep(1)
        
        return dropdown_div.get_attribute('outerHTML')

    except Exception as e:
        print(f"Error getting dropdown div: {e}")
        traceback.print_exc()
        return ""

def get_fares_html(driver):
    """
    Grabs outbound and inbound 'calendar' HTML from the low-fare widget
    """
    try:
        outbound_html = driver.find_element(
            By.CSS_SELECTOR, 'ul[ng-model="Outbound"]'
        ).get_attribute('outerHTML')
        inbound_html = driver.find_element(
            By.CSS_SELECTOR, 'ul[ng-model="Inbound"]'
        ).get_attribute('outerHTML')
        return outbound_html, inbound_html
    except Exception as e:
        print(f"Error getting fares HTML: {e}")
        traceback.print_exc()
        return "", ""

def extract_fares_from_html(fares_html):
    """
    Parse the low-fare <li> elements. Extract { month: price } pairs.
    """
    try:
        soup = BeautifulSoup(fares_html, 'html.parser')
        li_elements = soup.find_all('li')
        fares = {}
        for li in li_elements:
            # Ae.g. <p class='month'>Jul</p> <p class='price'>99€</p>
            month_el = li.find('p', class_='month')
            price_el = li.find('p', class_='price')
            if not (month_el and price_el):
                continue
            month = month_el.text.strip()
            price_text = price_el.text.strip().replace('€', '').replace(',', '')
            if price_text:
                try:
                    fares[month] = float(price_text)
                except ValueError:
                    print(f"Warning: Skipping invalid price for {month}: '{price_text}'")
        return fares
    except Exception as e:
        print(f"Error extracting fares from HTML: {e}")
        traceback.print_exc()
        return {}

def get_month_order():
    current_month = datetime.now().month
    months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
              'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    # reorder so current month is first
    return months[current_month - 1:] + months[:current_month - 1]

def get_destinations(dropdown_div_html):
    """
    Parse the outerHTML of the .ddList for <ul> ... <li> items 
    that hold the destination text.
    """
    try:
        soup = BeautifulSoup(dropdown_div_html, 'html.parser')
        # In the new Aegean markup, there is typically
        # <ul class="ui-menu ui-widget ui-widget-content ui-autocomplete ui-front" ...>
        #   <li>some place</li>
        #   <li>some place</li>
        # ...
        # If that fails, try generic "div.ddList ul li"
        li_elements = soup.select('ul.ui-menu.ui-widget.ui-widget-content.ui-autocomplete.ui-front li') 

        # If that returns nothing, you might fall back to:
        # li_elements = soup.select('div.ddList.autocomplete ul li')

        destinations = []
        for li in li_elements:
            text = li.get_text(strip=True)
            if text:
                destinations.append(text)
        return destinations
    except Exception as e:
        print(f"Error extracting destinations from HTML: {e}")
        traceback.print_exc()
        return []

def scrape_aegean_places(thread_id):
    print(f"Thread {thread_id} started.")
    driver = init_driver(thread_id)
    if driver is None:
        return  # Exit if driver could not be initialized

    url = 'https://en.aegeanair.com/flight-deals/low-fare-calendar/'
    driver.get(url)
    time.sleep(2)

    # Step 1: Set departure from Athens
    set_departure_from_athens(driver)
    # Step 2: Get the 'To' dropdown HTML
    dropdown_div_html = get_dropdown_div_html(driver)
    # Step 3: Extract destinations
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
                continue
            processed_destinations.append(place)

        print(f"Thread {thread_id} - Starting to process {place}...")

        try:
            # Type the place in the 'To' field
            input_field = WebDriverWait(driver, 10).until(
                EC.visibility_of_element_located((By.ID, 'AirportToSelect'))
            )
            input_field.clear()
            input_field.send_keys(place)
            time.sleep(2)
            input_field.send_keys(Keys.RETURN)

            print(f"Thread {thread_id} - Entered {place} and triggered search")

            search_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.ID, 'lfc_mask_searchbutton'))
            )
            driver.execute_script("arguments[0].click();", search_button)
            time.sleep(5)

            outbound_html, inbound_html = get_fares_html(driver)
            outbound_fares = extract_fares_from_html(outbound_html)
            inbound_fares = extract_fares_from_html(inbound_html)

            common_months = set(outbound_fares.keys()).intersection(inbound_fares.keys())
            if user_specified_months:
                common_months = {m for m in common_months if m in user_specified_months}

            combined_fares = {
                m: outbound_fares[m] + inbound_fares[m]
                for m in common_months
            }

            if combined_fares:
                min_price = min(combined_fares.values())
                min_months = [m for m, p in combined_fares.items() if p == min_price]
                local_min_prices.append((place, '/'.join(min_months), min_price))

            print(f"Thread {thread_id} - Finished processing {place}")

        except Exception as e:
            print(f"Thread {thread_id} - Failed to process {place}: {e}")
            traceback.print_exc()
            continue

    with lock:
        global_min_prices.extend(local_min_prices)

    print(f"Thread {thread_id} - All destinations processed, quitting driver...")
    try:
        driver.quit()
    except Exception as e:
        print(f"Thread {thread_id} - Error quitting driver: {e}")

def main():
    global user_specified_months
    
    months_input = input("Enter specific months (e.g., May Aug) or leave blank for all months: ").strip()
    if months_input:
        user_specified_months = months_input.split()

    threads = []
    for i in range(THREADS_NUM):
        thread = threading.Thread(target=scrape_aegean_places, args=(i+1,))
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()

    global_min_prices.sort(key=lambda x: x[2])

    with open("destinations2.txt", "w", encoding="utf-8") as file:
        file.write("Final Sorted Destinations by Minimum Price:\n")
        for place, months, price in global_min_prices:
            file.write(f"{place} {months} {price:.2f}€\n")
            print(f"{place} {months} {price:.2f}€")

if __name__ == "__main__":
    main()
