import time
import requests
from flask import Flask, request, jsonify, render_template
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

app = Flask(__name__)

def safe_find_elements(driver, by, value, timeout=10):
    try:
        return WebDriverWait(driver, timeout).until(
            EC.presence_of_all_elements_located((by, value))
        )
    except TimeoutException:
        print(f"Timeout waiting for elements: {value}")
        return []

def click_element(driver, element):
    driver.execute_script("arguments[0].scrollIntoView(true);", element)
    driver.execute_script("arguments[0].click();", element)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/scrape', methods=['POST'])
def scrape():
    data = request.json
    latitude = data.get('latitude')
    longitude = data.get('longitude')

    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.61 Safari/537.36')

    driver = webdriver.Chrome(options=chrome_options)
    wait = WebDriverWait(driver, 30)

    collected_elements_info = []

    try:
        driver.execute_cdp_cmd('Browser.grantPermissions', {
        "origin": "https://aedm.jp/",
        "permissions": ["geolocation"]
        })

        driver.execute_cdp_cmd('Emulation.setGeolocationOverride', {
            "latitude": latitude,
            "longitude": longitude,
            "accuracy": 100
        })
         
        target_url = 'https://aedm.jp/'
        driver.get(target_url)
        print(f"ページにアクセスしました: {target_url}")

        wait.until(lambda d: d.execute_script('return document.readyState') == 'complete')
        print("ページの読み込みが完了しました")

        zoom_out_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, ".gmnoprint:nth-child(3) .gm-control-active:nth-child(3)")))
        click_element(driver, zoom_out_button)
        print("ズームアウトボタンをクリックしました")

        time.sleep(3)

        elements = safe_find_elements(driver, By.CSS_SELECTOR, 'div[title]')
        print(f"{len(elements)}個の要素が見つかりました")

        for index, div in enumerate(elements, start=1):
            if len(collected_elements_info) >= 5:
                break

            try:
                title = div.get_attribute('title')
                img_elements = div.find_elements(By.TAG_NAME, 'img')

                if not img_elements:
                    continue

                first_img = img_elements[0]
                click_element(driver, first_img)
                print(f"画像 {index} をクリックしました")

                time.sleep(3)

                address_xpath = '//div[@class="row"]/div[@class="col-3 headline"]/span[@class="light" and text()="住所"]/parent::div/following-sibling::div[@class="col content"]'
                address_element = safe_find_elements(driver, By.XPATH, address_xpath, timeout=5)
                
                address = address_element[0].text if address_element else "住所が見つかりませんでした"
                print(f"画像 {index} の住所: {address}")

                collected_elements_info.append({"title": title, "address": address})

            except Exception as e:
                print(f"画像 {index} の処理中にエラーが発生しました: {e}")
                continue

    except Exception as e:
        print(f"エラーが発生しました: {e}")

    finally:
        driver.quit()
        print("ブラウザを閉じました")

    return jsonify({"elements": collected_elements_info})

@app.route('/geocode', methods=['POST'])
def geocode():
    data = request.json
    address = data.get('address')
    
    api_url = "https://msearch.gsi.go.jp/address-search/AddressSearch?q="
    
    try:
        response = requests.get(api_url + address)
        result = response.json()
        
        if result and len(result) > 0:
            lon, lat = result[0]['geometry']['coordinates']
            return jsonify({"latitude": lat, "longitude": lon})
        else:
            return jsonify({"error": "緯度経度が見つかりませんでした"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)