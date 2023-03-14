import logging
import os
from datetime import datetime, timedelta
import imgpush.settings as settings
from imgpush.lib.db import cachefs

def autodel_cache():
    logging.info("doing cache autodelete")
    # Check if Mongo is being used
    if settings.USE_MONGO:
        # logic to delete files from MongoDB
        # Get the current time
        now = datetime.now()
        # Get the files from the database
        files = cachefs.find({"metadata.uploadDate": {"$lt": now - timedelta(seconds=settings.MAX_TMP_FILE_AGE)}})
        # Loop through all the files
        for file in files:
            logging.info(f"deleting cache {file.filename}")
            # Check if the file is older than MAX_TMP_FILE_AGE
            cachefs.delete(file._id)
    else:
        # Get the cache directory path
        cache_dir = settings.CACHE_DIR
        # Get the current time
        now = datetime.now()

        # Loop through all the files in the cache directory
        for filename in os.listdir(cache_dir):
            file_path = os.path.join(cache_dir, filename)

            # Check if the file is older than MAX_TMP_FILE_AGE
            if os.stat(file_path).st_mtime < (now - timedelta(seconds=settings.MAX_TMP_FILE_AGE)).timestamp():
                os.remove(file_path)
                logging.info(f"deleting cache {filename}")
