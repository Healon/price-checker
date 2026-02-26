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

def get_momo_price(url, goods_code):
    if not goods_code:
        return None
    import time
    ts = int(time.time())
    # 先試行動版，再試桌機版
    urls_to_try = [
        f"https://m.momoshop.com.tw/describe.momo?goodsCode={goods_code}&timeStamp={ts}",
        f"https://www.momoshop.com.tw/goods/GoodsDetail.jsp?i_code={goods_code}"
    ]
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/122.0 Safari/537.36",
        "Accept-Language": "zh-TW,zh;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }
    for try_url in urls_to_try:
        try:
            res = requests.get(try_url, headers=headers, timeout=20)
            soup = BeautifulSoup(res.text, "html.parser")
            raw = soup.get_text(" ", strip=True)

            # 先找折扣關鍵字附近的價格
            keywords = ["限時折後價", "折後價", "折價後", "現折", "促銷價", "折扣後"]
            for kw in keywords:
                idx = raw.find(kw)
                if idx != -1:
                    window = raw[max(0, idx-80): idx+120]
                    nums = re.findall(r'(\d{1,3}(?:,\d{3})+|\d{3,5})', window)
                    prices = [int(n.replace(",", "")) for n in nums if int(n.replace(",", "")) > 100]
                    if prices:
                        return {"price": str(min(prices)), "url": try_url}

            # 退一步：找頁面所有價格取最小值
            nums = re.findall(r'(\d{1,3}(?:,\d{3})+)', raw)
            prices = [int(n.replace(",", "")) for n in nums if int(n.replace(",", "")) > 100]
            if prices:
                return {"price": str(min(prices)), "url": try_url}
        except Exception as e:
            print(f"Momo 嘗試失敗：{e}")
            continue
    return None

# Momo
report += "🛍️ Momo\n"
momo = get_momo_price("", product["momo_code"])
if momo and momo.get("price"):
    report += f"    💰 折扣價 NT${momo['price']}\n"
    report += f"    🔗 {momo['url']}\n"
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
