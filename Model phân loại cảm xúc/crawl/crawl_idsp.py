
import requests
import time
import random
import pandas as pd

cookies = {
     'TIKI_GUEST_TOKEN': '8jWSuIDBb2NGVzr6hsUZXpkP1FRin7lY',
     'TOKENS': '{%22access_token%22:%22fHZrtNKWCbqs4TdlSiy6vkFj8PApE3Qe%22%2C%22expires_in%22:157680000%2C%22expires_at%22:1852785535877%2C%22guest_token%22:%22fHZrtNKWCbqs4TdlSiy6vkFj8PApE3Qe%22}',
     'amp_99d374': 'hgRAKwT9Og2yFbhA7CXuf8...1hao30m2s.1hao3118h.1p.2q.4jhgRAKwT9Og2yFbhA7CXuf8...1hao30m2s.1hao3118h.1p.2q.4j',
     'amp_99d374_tiki.vn': 'eSc-_0HT1um7cb57E7dwA0...1enloc6a2.1enlp8817.3.1.1',
     '_gcl_au': '1.1.501547246.1695105543',
     '_ants_utm_v2': '',
     '_pk_id.638735871.2fc5': 'b92ae025fbbdb31f.1605974236.1.1605975278.1605974236.',
     '_pk_ses.638735871.2fc5': '*',
     '_trackity': '60a6467a-4603-1ac4-aba3-ef03ae1d3c9b',
     '_ga_NKX31X43RV': 'GS1.1.1605974235.1.1.1605975326.0',
     '_ga': 'GA1.1.1538029887.1695105539',
     'ai_client_id': '11935756853.1605974227',
     'an_session': 'zizkzrzjzlzizqzlzqzjzdzizizqzgzmzkzmzlzrzmzgzdzizlzjzmzqzkznzhzhzkzdzizhzdzizlzjzmzqzkznzhzhzkzdzizlzjzmzqzkznzhzhzkzdzjzdzhzqzdzizd2f27zdzjzdzlzmzmznzq',
     'au_aid': '11935756853',
     'dgs': '1605975268%3A3%3A0',
     'au_gt': '1605974227146',
     '_ants_services': '%5B%22cuid%22%5D',
     '__admUTMtime': '1605974236',
     '__iid': '749',
     '__su': '0',
     '_bs': 'bb9a32f6-ab13-ce80-92d6-57fd3fd6e4c8',
     '_gid': 'GA1.2.1978719018.1695105539',
     '_fbp': 'fb.1.1605974237134.1297408816',
     '_hjid': 'f152cf33-7323-4410-b9ae-79f6622ebc48',
     '_hjFirstSeen': '1',
     '_hjIncludedInPageviewSample': '1',
     '_hjAbsoluteSessionInProgress': '0',
     '_hjIncludedInSessionSample': '1',
     'tiki_client_id': '1538029887.1695105539',
     '__gads': 'ID=ae56424189ecccbe-227eb8e1d6c400a8:T=1605974229:RT=1605974229:S=ALNI_MZFWYf2BAjzCSiRNLC3bKI-W_7YHA',
     'proxy_s_sv': '1605976041662',
     'TKSESSID': '8bcd49b02e1e16aa1cdb795c54d7b460',
     'TIKI_RECOMMENDATION': '21dd50e7f7c194df673ea3b717459249',
     'cto_bundle': 'V9Dkml9NVXNkQmJ6aEVLcXNqbHdjcVZoQ0l5RXpOMlRybjdDT0JrUnNxVXc2bHd0N2J3Y2FCdmZVQXdYY1QlMkJYUmxXSHZ2UEFwd3IzRHhzRWJYMlQlMkJsQjhjQlA1JTJCcExyRzlUQk5CYUdMdjl2STNQanVsa3cycHd3SHElMkJabnI3dzNhREpZcFVyandyM1d1QWpJbWYxT1UyWDdHZyUzRCUzRA',
     'TIKI_RECENTLYVIEWED': '58259141',
     '_ants_event_his': '%7B%22action%22%3A%22view%22%2C%22time%22%3A1605974691247%7D',
     '_gat': '1',
 }

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36 Edg/117.0.2045.31',
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'vi-VN,vi;q=0.8,en-US;q=0.5,en;q=0.3',
    'Referer': 'https://tiki.vn/dien-thoai-may-tinh-bang/c1789',
    'x-guest-token': 'fHZrtNKWCbqs4TdlSiy6vkFj8PApE3Qe',
    'Connection': 'keep-alive',
    'TE': 'Trailers',
}

params = {
    'limit': '40',
    'include': 'advertisement',
    'aggregations': '2',
    'trackity_id': '60a6467a-4603-1ac4-aba3-ef03ae1d3c9b',
    'category': '1789',
    'page': '1',
    'src': 'c1789',
    'urlKey':  'dien-thoai-may-tinh-bang',
}

product_id = []
for i in range(1, 21):
    params['page'] = i
    response = requests.get('https://tiki.vn/api/v2/products', headers=headers, params=params)#, cookies=cookies)
    if response.status_code == 200:
        print('request success!!!')
        for record in response.json().get('data'):
            product_id.append({'id': record.get('id')})
    time.sleep(random.randrange(3, 10))

df = pd.DataFrame(product_id)
df.to_csv('product_id_ncds.csv', index=False)