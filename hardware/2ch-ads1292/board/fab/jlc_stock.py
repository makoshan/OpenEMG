"""查嘉立创贴片库（JLCPCB 国际站公开接口，与国内贴片库同源）：python jlc_stock.py <C号或型号>... 。
每个关键字取「componentCode 精确等于 C 号」或「型号精确相等」的那条，输出 JSON 行：C 号、型号、封装、基础/扩展、库存、
最小贴装数、损耗数、1 片单价。下单当天的库存和归属以嘉立创 SMT 匹配页为准，这里是出包前的预核。"""
import json, sys, time, urllib.request

URL = 'https://jlcpcb.com/api/overseas-pcb-order/v1/shoppingCart/smtGood/selectSmtComponentList'


def query(kw):
    req = urllib.request.Request(URL, data=json.dumps({'keyword': kw, 'currentPage': 1, 'pageSize': 25}).encode(),
                                 headers={'Content-Type': 'application/json', 'User-Agent': 'Mozilla/5.0'})
    for i in range(5):   # 接口会限流断开，退避重试
        try:
            d = json.load(urllib.request.urlopen(req, timeout=40)); break
        except Exception:
            if i == 4: raise
            time.sleep(3 * (i + 1))
    lst = ((d.get('data') or {}).get('componentPageInfo') or {}).get('list') or []
    hit = [c for c in lst if c.get('componentCode') == kw or (c.get('componentModelEn') or '').upper() == kw.upper()]
    out = []
    for c in hit:
        pr = sorted(c.get('componentPrices') or [], key=lambda p: p['startNumber'])
        out.append(dict(key=kw, lcsc=c.get('componentCode'), mpn=c.get('componentModelEn'), package=c.get('componentSpecificationEn'),
                        lib={'base': '基础', 'expand': '扩展'}.get(c.get('componentLibraryType'), c.get('componentLibraryType')),
                        preferred=c.get('preferredComponentFlag'), stock=c.get('stockCount'),
                        least=c.get('leastPatchNumber'), loss=c.get('lossNumber'), price1=pr[0]['productPrice'] if pr else None,
                        brand=c.get('componentBrandEn')))
    return out or [dict(key=kw, lcsc=None, note='未命中')]


for kw in sys.argv[1:]:
    for r in query(kw): print(json.dumps(r, ensure_ascii=False), flush=True)
    time.sleep(1.0)
