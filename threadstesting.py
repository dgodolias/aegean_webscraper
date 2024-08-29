from selenium import webdriver
from selenium.webdriver.common.keys import Keys
import time

# Setup the WebDriver (Make sure to have the corresponding WebDriver executable in your PATH)
driver = webdriver.Chrome()  # or webdriver.Firefox() if using Firefox

# Open the first tab
driver.get('https://en.aegeanair.com/flight-deals/low-fare-calendar/')

# Open a new tab and navigate to the URL
driver.execute_script("window.open('https://en.aegeanair.com/flight-deals/low-fare-calendar/', '_blank');")

# Switch to the new tab
driver.switch_to.window(driver.window_handles[1])

# Open another new tab and navigate to the URL
driver.execute_script("window.open('https://en.aegeanair.com/flight-deals/low-fare-calendar/', '_blank');")

# Switch to the new tab
driver.switch_to.window(driver.window_handles[2])

# Give some time to load
time.sleep(5)

# Close the driver after the operations
driver.quit()
