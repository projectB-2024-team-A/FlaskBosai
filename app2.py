import time
import requests
from flask import Flask, request, jsonify, render_template
from playwright.sync_api import sync_playwright

app = Flask(__name__)

def scrape_dynamic_content(latitude, longitude):
    collected_elements_info = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            geolocation={"latitude": latitude, "longitude": longitude},
            permissions=["geolocation"]
        )
        page = context.new_page()

        target_url = 'https://aedm.jp/'
        page.goto(target_url)
        print(f"ページにアクセスしました: {target_url}")

        page.wait_for_load_state('networkidle')
        print("ページの読み込みが完了しました")

        # Zoom out (if necessary)
        zoom_out_button = page.query_selector(".gmnoprint:nth-child(3) .gm-control-active:nth-child(3)")
        if zoom_out_button:
            zoom_out_button.click()
            print("ズームアウトボタンをクリックしました")
            time.sleep(3)

        elements = page.query_selector_all('div[title]')
        print(f"{len(elements)}個の要素が見つかりました")

        for index, div in enumerate(elements, start=1):
            if len(collected_elements_info) >= 5:
                break

            try:
                title = div.get_attribute('title')
                img_elements = div.query_selector_all('img')

                if not img_elements:
                    continue

                first_img = img_elements[0]
                first_img.click()
                print(f"画像 {index} をクリックしました")
                time.sleep(3)

                address_element = page.query_selector('//div[@class="row"]/div[@class="col-3 headline"]/span[@class="light" and text()="住所"]/parent::div/following-sibling::div[@class="col content"]')
                address = address_element.inner_text() if address_element else "住所が見つかりませんでした"
                print(f"画像 {index} の住所: {address}")

                collected_elements_info.append({"title": title, "address": address})

            except Exception as e:
                print(f"画像 {index} の処理中にエラーが発生しました: {e}")
                continue

        browser.close()
        print("ブラウザを閉じました")

    return collected_elements_info

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/scrape', methods=['POST'])
def scrape():
    data = request.json
    latitude = data.get('latitude')
    longitude = data.get('longitude')

    collected_elements_info = scrape_dynamic_content(latitude, longitude)
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
