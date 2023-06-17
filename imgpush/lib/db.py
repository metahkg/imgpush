
import gridfs
import imgpush.settings as settings
from pymongo import MongoClient

client = MongoClient(settings.MONGO_URI) if settings.USE_MONGO else None
db = client["imgpush"] if settings.USE_MONGO else None
fs: gridfs.GridFS = gridfs.GridFS(db, "images") if settings.USE_MONGO else None
cachefs: gridfs.GridFS = gridfs.GridFS(db, "cache") if settings.USE_MONGO else None
