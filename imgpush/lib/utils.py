from imgpush.lib.errors import InvalidSize
import imgpush.settings as settings
from io import BytesIO
from PIL import Image

def pil_to_file(img: Image, img_type: str) -> BytesIO:
    outfile = BytesIO()
    img.save(outfile, format=img_type)
    # Reset the buffer cursor to the beginning of the buffer.
    outfile.seek(0)
    return outfile

def pil_to_binary(img: Image.Image, format: str = "png"):
    binary_buffer = BytesIO()
    img.save(binary_buffer, format=format)
    binary_data = binary_buffer.getvalue()
    return binary_data

def get_size_from_string(size):
    """
    The _get_size_from_string function takes a string and returns an integer.
    If the string is not a valid size, it returns an empty string.

    :param size: Determine the size of the image to be returned
    :return: The size as an integer or &quot;&quot;
    :doc-author: Trelent
    """
    try:
        size = int(size)
        if len(settings.VALID_SIZES) and size not in settings.VALID_SIZES:
            raise InvalidSize
    except ValueError:
        size = ""
    return size
