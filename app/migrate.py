from pymongo import MongoClient
import gridfs
import os
import settings
import mimetypes

client: MongoClient = MongoClient(settings.MONGO_URI)
db = client["imgpush"]
fs: gridfs.GridFS = gridfs.GridFS(db)


def migrate():
    for file in os.listdir("images"):
        mimetype = mimetypes.guess_type(file)[0]
        fs.put(open(f"images/{file}", "rb"), filename=file, metadata={"type": mimetype})
    return None


migrate()
