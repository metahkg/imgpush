import imgpush.settings as settings
import glob
import random
import string
import uuid

def get_random_filename():
    """
    The _get_random_filename function generates a random filename for an image.
    It does this by generating a random string of length settings.RANDOM_STRING_LENGTH,
    and then appending the appropriate file extension based on the MIME type of the image.
    If that filename already exists in IMAGES_DIR, it will generate another one and check if it exists again.

    :return: A random string of length 8
    :doc-author: Trelent
    """
    random_string = generate_random_filename()
    if settings.NAME_STRATEGY == "randomstr":
        file_exists = len(glob.glob(f"{settings.IMAGES_DIR}/{random_string}.*")) > 0
        if file_exists:
            return get_random_filename()
    return random_string


def generate_random_filename():
    """
    The _generate_random_filename function generates a random filename for the uploaded file.
    The function is called by the upload_file() function, which uses it to generate a filename
    for each uploaded file.
    The _generate_random_filename() function accepts no arguments and returns a string containing
    the randomly generated filename.

    :return: A random string of length 6
    :doc-author: Trelent
    """
    if settings.NAME_STRATEGY == "uuidv4":
        return str(uuid.uuid4())
    if settings.NAME_STRATEGY == "randomstr":
        return "".join(
            random.choices(
                string.ascii_lowercase + string.digits + string.ascii_uppercase, k=8
            )
        )
    return None
