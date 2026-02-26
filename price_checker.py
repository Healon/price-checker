import requests
from bs4 import BeautifulSoup
import os
from datetime import datetime

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

products = [
    {"name": "Royal Canin UC33 貓飼料 10KG", "search": "Royal Canin 法國皇家泌尿道保健成貓UC33 10KG"},
    {"name": "大研生醫瑪卡粉包5盒", "search": "大研生醫精氣神瑪卡粉包7.4g 30包 5盒"},
    {"name": "大研生醫魚油5盒", "search": "大研生醫德國頂級魚油Omega-3 84% 60粒 5盒"},
    {"name": "大研生醫B群5盒", "search": "大研生醫B群緩釋雙層錠 30錠 5盒"},
    {"name": "SK-II青春露330ml", "search": "SK-II青春露330ml"},
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
        res = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")
        
        # 找頁面內嵌的 JSON 價格資料
        import re
        scripts = soup.find_all("script")
        for script in scripts:
            if script.string and "finalPrice" in script.string:
                match = re.search(r'"finalPrice"\s*:\s*(\d+)', script.string)
                origin_match = re.search(r'"originPrice"\s*:\s*(\d+)', script.string)
                if match:
                    final_price = match.group(1)
                    origin_price = origin_match.group(1) if origin_match else None
                    return final_price, origin_price
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

def generate_report():
    now = datetime.now().strftime('%Y/%m/%d %H:%M')
    report = f"📦 <b>每日價格報告 {now}</b>\n"
    report += "=" * 30 + "\n"

    for product in products:
        report += f"\n📌 <b>{product['name']}</b>\n"
        report += "🛒 PChome\n"
        items = get_pchome_price(product["search"])
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

    print(report)
    send_telegram(report)

if __name__ == "__main__":
    generate_report()
