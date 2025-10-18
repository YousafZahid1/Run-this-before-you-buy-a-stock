import yfinance as yf
from newsapi import NewsApiClient
import finnhub
from datetime import date, timedelta
import requests
import json
import time

newsapi = NewsApiClient(api_key='API_KEY')
finnhub_client = finnhub.Client(api_key="API_KEY")
LLAMA_API_KEY = "API_KEY"
LLAMA_API_URL = "https://api.llama.com/v1/chat/completions"

today = date.today().strftime('%Y-%m-%d')
two_days_ago = (date.today() - timedelta(days=2)).strftime('%Y-%m-%d')
ticker = 'ABAT'
company = 'American Battery Technology Company'

print(f"\ngetting data for {ticker}...\n")

data = {
    'news': [], 'twits': [], 'reddit': [], 'sa': [],
    'fh': [], 'yahoo': [], 'stock': {}, 'ytext': []
}

print("checking news...")
try:
    res = newsapi.get_everything(
        q=f'{ticker} OR {company}',
        domains='bloomberg.com,businessinsider.com,cnbc.com,fortune.com,wsj.com,reuters.com,techcrunch.com,seekingalpha.com,marketwatch.com,benzinga.com,yahoo.com',
        from_param=two_days_ago, to=today, language='en', sort_by='relevancy'
    )
    for a in res['articles'][:10]:
        data['news'].append({
            'title': a['title'],
            'source': a['source']['name'],
            'desc': a.get('description', ''),
            'url': a['url'],
            'date': a['publishedAt']
        })
    print(f"found {len(data['news'])} articles")
except Exception as e:
    print(e)

print("checking stocktwits...")
try:
    url = f"https://api.stocktwits.com/api/2/streams/symbol/{ticker}.json"
    r = requests.get(url)
    if r.status_code == 200:
        j = r.json()
        for m in j.get('messages', [])[:20]:
            data['twits'].append({
                'user': m['user']['username'],
                'text': m['body'],
                'sent': m.get('entities', {}).get('sentiment', {}).get('basic', 'None'),
                'likes': m.get('likes', {}).get('total', 0)
            })
        print(f"found {len(data['twits'])} posts")
except Exception as e:
    print(e)

print("checking reddit...")
try:
    subs = ['wallstreetbets', 'stocks', 'investing', 'stockmarket', 'pennystocks']
    for s in subs:
        u = f"https://www.reddit.com/r/{s}/search.json"
        p = {'q': ticker, 'restrict_sr': 1, 'sort': 'relevance', 'limit': 25, 't': 'week'}
        h = {'User-Agent': 'Mozilla/5.0'}
        try:
            r = requests.get(u, params=p, headers=h, timeout=10)
            time.sleep(1)
            if r.status_code == 200:
                posts = r.json().get('data', {}).get('children', [])
                for post in posts:
                    d = post['data']
                    data['reddit'].append({
                        'sub': s,
                        'title': d['title'],
                        'score': d['score'],
                        'ups': d.get('upvote_ratio', 0),
                        'comments': d['num_comments'],
                        'body': d.get('selftext', '')[:300]
                    })
        except:
            continue
    print(f"found {len(data['reddit'])} reddit posts")
except Exception as e:
    print(e)

print("checking seeking alpha...")
try:
    r = requests.get(f"https://seekingalpha.com/api/v3/symbols/{ticker}/news",
                     headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
    if r.status_code == 200:
        for a in r.json().get('data', [])[:5]:
            at = a.get('attributes', {})
            data['sa'].append({'title': at.get('title', 'N/A'), 'date': at.get('publishOn', 'N/A')})
    print(f"found {len(data['sa'])} SA articles")
except Exception as e:
    print(e)

print("getting finnhub news...")
try:
    fn = finnhub_client.company_news(ticker, _from=two_days_ago, to=today)
    for n in fn[:10]:
        data['fh'].append({'headline': n['headline'], 'source': n['source'], 'sum': n.get('summary', '')})
    print(f"found {len(data['fh'])} news items")
except Exception as e:
    print(e)

print("getting stock data...")
try:
    s = yf.Ticker(ticker)
    i = s.info
    data['stock'] = {
        'name': i.get('longName', 'N/A'),
        'price': i.get('currentPrice', i.get('regularMarketPrice', 'N/A')),
        'high': i.get('fiftyTwoWeekHigh', 'N/A'),
        'low': i.get('fiftyTwoWeekLow', 'N/A'),
        'cap': i.get('marketCap', 'N/A'),
        'vol': i.get('volume', 'N/A'),
        'avgvol': i.get('averageVolume', 'N/A')
    }
    news = s.news
    txt = ""
    for i in news:
        try:
            res = requests.get(i["link"], timeout=10)
            if res.ok:
                txt += res.text
        except:
            continue
    data['ytext'].append(txt)
    for n in news[:5]:
        data['yahoo'].append({'title': n.get('title', 'N/A'), 'pub': n.get('publisher', 'N/A')})
    print(f"got stock + {len(data['yahoo'])} yahoo articles\n")
except Exception as e:
    print(e)

summary = f"""analyze sentiment for {ticker} ({company}):

STOCK:
price: ${data['stock'].get('price', 'N/A')}
52w high: ${data['stock'].get('high', 'N/A')}
52w low: ${data['stock'].get('low', 'N/A')}
cap: ${data['stock'].get('cap', 'N/A')}
vol: {data['stock'].get('vol', 'N/A')}

NEWS ({len(data['news'])}):
yahoo text: {data['ytext']}"""

for i, a in enumerate(data['news'][:8], 1):
    summary += f"\n{i}. [{a['source']}] {a['title']}"
    if a.get('desc'):
        summary += f"\n   {a['desc'][:200]}"

if data['fh']:
    summary += f"\n\nFINNHUB ({len(data['fh'])}):"
    for i, n in enumerate(data['fh'][:5], 1):
        summary += f"\n{i}. {n['headline']}"
        if n.get('sum'):
            summary += f"\n   {n['sum'][:150]}"

summary += f"\n\nTWITS ({len(data['twits'])}):"
sent = {'Bullish': 0, 'Bearish': 0, 'None': 0}
for p in data['twits']:
    sent[p['sent']] += 1
summary += f"\nBullish: {sent['Bullish']}, Bearish: {sent['Bearish']}, Neutral: {sent['None']}"

summary += f"\n\nREDDIT ({len(data['reddit'])}):"
top = sorted(data['reddit'], key=lambda x: x['score'], reverse=True)[:5]
for i, p in enumerate(top, 1):
    summary += f"\n{i}. r/{p['sub']} - {p['title']}"
    summary += f"\n   Score: {p['score']}, Comments: {p['comments']}"
    if p.get('body') and len(p['body']) > 10:
        summary += f"\n   {p['body'][:200]}"

if data['yahoo']:
    summary += f"\n\nYAHOO ({len(data['yahoo'])}):"
    for i, a in enumerate(data['yahoo'][:3], 1):
        summary += f"\n{i}. [{a['pub']}] {a['title']}"

summary += """

Give me a clear breakdown:
1. Overall sentiment (bullish/bearish/neutral)
2. Main themes
3. Significant news
4. Social mood
5. What investors should know
6. Should I buy or not?

Be direct.


"""

print("\nAnalyzing...\n")

try:
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {LLAMA_API_KEY}"}
    payload = {
        "model": "Llama-4-Maverick-17B-128E-Instruct-FP8",
        "messages": [
            {"role": "system", "content": "You are a financial analyst. Give direct, concise analysis."},
            {"role": "user", "content": summary}
        ]
    }
    r = requests.post(LLAMA_API_URL, headers=headers, json=payload, timeout=90)
    if r.status_code == 200:
        j = r.json()
        print("\n--- ANALYSIS ---\n")
        if 'choices' in j and len(j['choices']) > 0:
            print(j['choices'][0]['message']['content'])
        else:
            print(j)
        print("\n----------------\n")
    else:
        print("api error", r.status_code, r.text)
except Exception as e:
    print("error", e)

print(f"\nnews: {len(data['news'])}, twits: {len(data['twits'])}, reddit: {len(data['reddit'])}")
