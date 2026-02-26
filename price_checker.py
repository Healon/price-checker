# import requests
from datetime import datetime

products = [
    {"name": "Royal Canin UC33 貓飼料 10KG", "search": "Royal Canin 法國皇家泌尿道保健成貓UC33 10KG"},
    {"name": "大研生醫瑪卡粉包5盒",           "search": "大研生醫精氣神瑪卡粉包7.4g 30包 5盒"},
    {"name": "大研生醫魚油5盒",               "search": "大研生醫德國頂級魚油Omega-3 84% 60粒 5盒"},
    {"name": "大研生醫B群5盒",                "search": "大研生醫B群緩釋雙層錠 30錠 5盒"},
    {"name": "SK-II青春露330ml",              "search": "SK-II青春露330ml"},
]

def get_pchome_detail(prod_id):
    url = f"https://ecshweb.pchome.com.tw/prod/v2/items/{prod_id}/price"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        res = requests.get(url, headers=headers, timeout=10)
        data = res.json()
        origin_price = data.get("originPrice")
        sale_price = data.get("salePrice") or data.get("price")
        return sale_price, origin_price
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
            "list_price": list_price,
            "origin_price": origin_price,
            "final_price": final_price,
            "url": f"https://24h.pchome.com.tw/prod/{prod_id}"
        })
    return results

def generate_report():
    print("=" * 60)
    print(f"📦 每日價格報告 {datetime.now().strftime('%Y/%m/%d %H:%M')}")
    print("=" * 60)
    for product in products:
        print(f"\n📌 {product['name']}")
        print("  🛒 PChome")
        items = get_pchome_price(product["search"])
        if items:
            for item in items:
                print(f"    - {item['name'][:35]}")
                if item["origin_price"] and str(item["origin_price"]) != str(item["final_price"]):
                    print(f"       💰 原價 NT${item['origin_price']} → 折扣價 NT${item['final_price']}")
                else:
                    print(f"       💰 售價 NT${item['final_price']}")
                print(f"       🔗 {item['url']}")
        else:
            print("    ⚠️ 查無結果")

if __name__ == "__main__":
    generate_report()
