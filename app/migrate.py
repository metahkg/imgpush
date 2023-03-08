from pymongo import MongoClient
import gridfs
from app import get_image, upload_image, delete_image
import os
import settings

client: MongoClient = MongoClient(settings.MONGO_URI)
db = client["imgpush"]
fs: gridfs.GridFS = gridfs.GridFS(db)


def migrate():
    # for file in os.listdir("images"):
    #         if file.endswith(".jpg"):
    #             with open(os.path.join("images", file), "rb") as image:
    #                 upload_image(image.read(), file)
    return None
