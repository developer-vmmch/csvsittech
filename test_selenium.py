import http.server, socketserver, threading, time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains

server = socketserver.TCPServer(('', 8126), http.server.SimpleHTTPRequestHandler)
t = threading.Thread(target=server.serve_forever)
t.daemon = True
t.start()
time.sleep(1)

try:
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    driver = webdriver.Chrome(options=options)
    driver.get("http://127.0.0.1:8126/test_dropdown.html")

    input_el = driver.find_element(By.CSS_SELECTOR, ".vss-input")
    input_el.click()
    input_el.send_keys("Bret")
    time.sleep(2)

    items = driver.find_elements(By.CSS_SELECTOR, ".vss-item")
    print(f"Found {len(items)} items")
    if items:
        print("Clicking item...")
        ActionChains(driver).move_to_element(items[0]).click().perform()
        time.sleep(1)
        print("Input value after click:", input_el.get_attribute("value"))
        
        logs = driver.get_log("browser")
        for log in logs:
            print("LOG:", log['message'])
    else:
        print("No items found")
        
    driver.quit()
finally:
    server.shutdown()
    server.server_close()
