from io import BytesIO
import requests
import os
from PIL import Image
import dotenv

dotenv.load_dotenv()

url = "https://www.w3schools.com/w3images/fjords.jpg"
response = requests.get(url)

img = BytesIO(response.content).getbuffer()

hostname = os.getenv("HOSTNAME") or "localhost"
port = os.getenv("PORT") or "5000"
upload_route = os.getenv("UPLOAD_ROUTE") or "/"


data = requests.post(f'http://{hostname}:{port}/{upload_route}', files={'file': img})

if data.status_code == 200:
    print("Upload and Download OK")
else:
    raise Exception(data.text)

print(data.json())

url = data.json()['url']

print(f"url: {url}")
data = requests.get(url)

resized_url = url + "?w=1000&h=1000"
print(f"resized url: {resized_url}")

response = requests.get(resized_url)

if response.status_code == 200:
    resized_data = response.content
    resized_img = Image.open(BytesIO(resized_data))
    # check the image size
    # Check if generated resized image has the expected dimensions
    width, height = resized_img.size
    expected_width, expected_height = 1000, 1000

    if (width, height) == (expected_width, expected_height):
        print("Dimensions of the generated resized image are as expected OK")
    else:
        raise ValueError(f"Dimensions of the generated resized image are not as expected. Width: {width}, Height: {height}, Expected Width: {expected_width}, Expected Height: {expected_height}")
else:
    raise Exception(response.text)
