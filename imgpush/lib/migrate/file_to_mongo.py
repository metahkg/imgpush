import logging
from pymongo import MongoClient
import gridfs
import os
import mimetypes
import sys

if __name__ == "__main__":
    myDir = os.getcwd()
    sys.path.append(myDir)
import imgpush.settings as settings

client: MongoClient = MongoClient(settings.MONGO_URI)
db = client["imgpush"]
fs: gridfs.GridFS = gridfs.GridFS(db, "images")


def file_to_mongo():
    logging.info("Migrating from file to mongo")

    files = os.listdir(settings.IMAGES_DIR)

    if not files:
        logging.info("No files found")
        return

    for file in os.listdir(settings.IMAGES_DIR):
        mimetype = mimetypes.guess_type(file)[0]
        if not fs.exists(file):
            logging.info(f"Migrating file {file}")
            fs.put(open(f"{settings.IMAGES_DIR}{file}", "rb"), filename=file, metadata={"type": mimetype})
            os.remove(f"{settings.IMAGES_DIR}{file}")

if __name__ == "__main__":
    file_to_mongo()
