import re
import time
import requests
from bs4 import BeautifulSoup
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
import os
from datetime import datetime

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

products = [
    {
        "name": "Royal Canin UC33 貓飼料 10KG",
        "pchome_search": "Royal Canin 法國皇家泌尿道保健成貓UC33 10KG",
        "momo_code": "14175117"
    },
    {
        "name": "大研生醫瑪卡粉包5盒",
        "pchome_search": "大研生醫精氣神瑪卡粉包7.4g 30包 5盒",
        "momo_code": "12215009"
    },
    {
        "name": "大研生醫魚油5盒",
        "pchome_search": "大研生醫德國頂級魚油Omega-3 84% 60粒 5盒",
        "momo_code": "8133412"
    },
    {
        "name": "大研生醫B群5盒",
        "pchome_search": "大研生醫B群緩釋雙層錠 30錠 5盒",
        "momo_code": "11873852"
    },
    {
        "name": "SK-II青春露330ml",
        "pchome_search": "SK-II青春露330ml",
        "momo_code": "12772333"
    },
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0 Safari/537.36",
    "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Connection": "keep-alive",
}

def make_session():
    s = requests.Session()
    retry = Retry(
        total=2,
        backoff_factor=0.5,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry)
    s.mount("https://", adapter)
    s.mount("http://", adapter)
    return s

def fetch_html(url, timeout=15):
    s = make_session()
    r = s.get(url, headers=HEADERS, timeout=timeout, allow_redirects=True)
    r.raise_for_status()
    return r.text

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"}
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Telegram 發送失敗：{e}")

def get_pchome_price(keyword):
    url = "https://ecshweb.pchome.com.tw/search/v3.3/all/results"
    params = {"q": keyword, "page": 1, "sort": "rnk/dc"}
    try:
        res = requests.get(url, params=params, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
        data = res.json()
        results = []
        prods = data.get("prods") or []
        for item in prods[:3]:
            prod_id = item["Id"]
            sale_price = item.get("price")
            origin_price = item.get("originPrice")
            results.append({
                "name": item["name"],
                "origin_price": str(origin_price) if origin_price else None,
                "final_price": str(sale_price) if sale_price else None,
                "url": f"https://24h.pchome.com.tw/prod/{prod_id}"
            })
        return results
    except Exception as e:
        print(f"PChome 錯誤：{e}")
        return []

def extract_momo_price(html):
    soup = BeautifulSoup(html, "lxml")
    text = soup.get_text(" ", strip=True)

    # 1. 折扣後價格
    m = re.search(r"折扣後價格\s*([0-9,]+)\s*元", text)
    if m:
        return int(m.group(1).replace(",", ""))

    # 2. 促銷價（魚油等商品用這個）
    m2 = re.search(r"促銷價\s*([0-9,]+)\s*元", text)
    if m2:
        return int(m2.group(1).replace(",", ""))

    # 3. 關鍵字附近最小價格
    for kw in ["限時折後價", "折後價", "現折價", "折扣價"]:
        idx = text.find(kw)
        if idx != -1:
            window = text[max(0, idx-30): idx+80]
            nums = re.findall(r'(\d{1,3}(?:,\d{3})+|\d{4,5})', window)
            prices = [int(n.replace(",", "")) for n in nums if int(n.replace(",", "")) > 100]
            if prices:
                return min(prices)

    return None

def get_momo_price(goods_code):
    if not goods_code:
        return None
    ts = int(time.time())
    # 行動版優先（比桌機版更少被封鎖）
    urls_to_try = [
        f"https://m.momoshop.com.tw/describe.momo?goodsCode={goods_code}&timeStamp={ts}",
        f"https://www.momoshop.com.tw/goods/GoodsDetail.jsp?i_code={goods_code}",
    ]
    for try_url in urls_to_try:
        try:
            html = fetch_html(try_url, timeout=15)
            price = extract_momo_price(html)
            if price:
                momo_link = f"https://www.momoshop.com.tw/goods/GoodsDetail.jsp?i_code={goods_code}"
                return {"price": str(price), "url": momo_link}
        except Exception as e:
            print(f"Momo 失敗：{e}")
            continue
    return None

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
        momo = get_momo_price(product["momo_code"])
        if momo and momo.get("price"):
            report += f"    💰 折扣價 NT${momo['price']}\n"
            report += f"    🔗 {momo['url']}\n"
        else:
            report += "  ⚠️ 查無結果\n"

    print(report)
    send_telegram(report)

if __name__ == "__main__":
    generate_report()
