import logging
from pymongo import MongoClient
import gridfs
import os
import sys

if __name__ == "__main__":
    myDir = os.getcwd()
    sys.path.append(myDir)
import imgpush.settings as settings

client: MongoClient = MongoClient(settings.MONGO_URI)
db = client["imgpush"]
fs: gridfs.GridFS = gridfs.GridFS(db, "images")


def mongo_to_file():
    logging.info("Migrating from mongo to file")

    try:
        files = fs.find()
    except:
        logging.warning("Cannot access mongodb. NOT migrating.")
        return

    if not files:
        logging.info("No files found")
        return

    for f in files:
        path = f"{settings.IMAGES_DIR}{f.filename}"
        try:
            os.stat(path)
        except FileNotFoundError:
            logging.info(f"Migrating file {f.filename}")
            # get the image from mongodb and save it to local filesystem
            with open(path, "wb") as fp:
                fp.write(fs.get(f._id).read())
            fs.delete(f._id)

if __name__ == "__main__":
    mongo_to_file()
