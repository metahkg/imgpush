import requests
import sys
import os

img = open(sys.argv[1], 'rb')

data = requests.post(f'http://{os.environ["HOSTNAME"] or "localhost"}:5000', files={'file': img})

url = data.json()['url']

print(f"url: {url}")
data = requests.get(url)

if data.status_code == 200:
    print("OK")
else:
    raise Exception(data.text)
