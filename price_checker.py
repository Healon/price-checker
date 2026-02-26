import requests
from bs4 import BeautifulSoup
import os
import re
import asyncio
from datetime import datetime
from playwright.async_api import async_playwright

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

products = [
    {
        "name": "Royal Canin UC33 貓飼料 10KG",
        "pchome_search": "Royal Canin 法國皇家泌尿道保健成貓UC33 10KG",
        "momo_url": "https://www.momoshop.com.tw/goods/GoodsDetail.jsp?i_code=14175117"
    },
    {
        "name": "大研生醫瑪卡粉包5盒",
        "pchome_search": "大研生醫精氣神瑪卡粉包7.4g 30包 5盒",
        "momo_url": "https://www.momoshop.com.tw/goods/GoodsDetail.jsp?i_code=12215009"
    },
    {
        "name": "大研生醫魚油5盒",
        "pchome_search": "大研生醫德國頂級魚油Omega-3 84% 60粒 5盒",
        "momo_url": "https://www.momoshop.com.tw/goods/GoodsDetail.jsp?i_code=8133412"
    },
    {
        "name": "大研生醫B群5盒",
        "pchome_search": "大研生醫B群緩釋雙層錠 30錠 5盒",
        "momo_url": ""  # 待補
    },
    {
        "name": "SK-II青春露330ml",
        "pchome_search": "SK-II青春露330ml",
        "momo_url": "https://www.momoshop.com.tw/goods/GoodsDetail.jsp?i_code=12772333"
    },
]

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"}
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Telegram 發送失敗：{e}")

def get_pchome_detail(prod_id):
    url = f"https://24h.pchome.com.tw/prod/{prod_id}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
    }
    try:
        res = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(res.text, "html.parser")
        prices = re.findall(r'\$([0-9,]+)', res.text)
        prices = [int(p.replace(",", "")) for p in prices if int(p.replace(",", "")) > 100]
        if len(prices) >= 2:
            return str(prices[0]), str(prices[1])
        elif len(prices) == 1:
            return str(prices[0]), None
        return None, None
    except:
        return None, None

def get_pchome_price(keyword):
    url = "https://ecshweb.pchome.com.tw/search/v3.3/all/results"
    params = {"q": keyword, "page": 1, "sort": "rnk/dc"}
    headers = {"User-Agent": "Mozilla/5.0"}
    res = requests.get(url, params=params, headers=headers)
    data = res.json()
    results = []
    for item in data.get("prods", [])[:3]:
        prod_id = item["Id"]
        list_price = item.get("price")
        sale_price, origin_price = get_pchome_detail(prod_id)
        final_price = sale_price if sale_price else list_price
        results.append({
            "name": item["name"],
            "origin_price": origin_price,
            "final_price": final_price,
            "url": f"https://24h.pchome.com.tw/prod/{prod_id}"
        })
    return results

async def get_momo_price(url):
    if not url:
        return None
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
        )
        try:
            await page.goto(url, timeout=30000)
            await page.wait_for_timeout(4000)

            try:
                name = await page.inner_text("h1.prdName")
            except:
                name = "N/A"
            try:
                price = (await page.inner_text(".salePrice .price")).replace(",", "")
            except:
                price = None
            try:
                origin = (await page.inner_text(".originPrice .price")).replace(",", "")
            except:
                origin = None

            # 如果 selector 抓不到，用 regex 從頁面找
            if not price:
                content = await page.content()
                m = re.search(r'"salePrice"\s*:\s*"?(\d+)"?', content)
                if m:
                    price = m.group(1)

            return {"name": name, "price": price, "origin_price": origin, "url": url}
        except Exception as e:
            print(f"Momo 錯誤：{e}")
            return None
        finally:
            await browser.close()

def generate_report():
    now = datetime.now().strftime('%Y/%m/%d %H:%M')
    report = f"📦 <b>每日價格報告 {now}</b>\n"
    report += "=" * 30 + "\n"

    for product in products:
        report += f"\n📌 <b>{product['name']}</b>\n"

        # PChome
        report += "🛒 PChome\n"
        items = get_pchome_price(product["pchome_search"])
        if items:
            for item in items:
                report += f"  • {item['name'][:30]}\n"
                if item["origin_price"] and str(item["origin_price"]) != str(item["final_price"]):
                    report += f"    💰 原價 NT${item['origin_price']} → 折扣價 NT${item['final_price']}\n"
                else:
                    report += f"    💰 售價 NT${item['final_price']}\n"
                report += f"    🔗 {item['url']}\n"
        else:
            report += "  ⚠️ 查無結果\n"

        # Momo
        report += "🛍️ Momo\n"
        momo = asyncio.run(get_momo_price(product["momo_url"]))
        if momo and momo.get("price"):
            if momo.get("origin_price") and momo["origin_price"] != momo["price"]:
                report += f"  • {momo['name'][:30]}\n"
                report += f"    💰 原價 NT${momo['origin_price']} → 折扣價 NT${momo['price']}\n"
            else:
                report += f"  • {momo['name'][:30]}\n"
                report += f"    💰 售價 NT${momo['price']}\n"
            report += f"    🔗 {momo['url']}\n"
        else:
            report += "  ⚠️ 查無結果\n"

    print(report)
    send_telegram(report)

if __name__ == "__main__":
    generate_report()
