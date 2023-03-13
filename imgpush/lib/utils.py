from typing import Optional
from imgpush.lib.convert_format import convert_format_type
from imgpush.lib.errors import InvalidSize
import imgpush.settings as settings
from io import BytesIO
from PIL import Image

def pil_to_file(img: Image, format: str, fps: Optional[int] = None) -> BytesIO:
    outfile = BytesIO()
    print("format: ", format)
    if format.upper() == "GIF":
        frames = []
        try:
            while 1:
                img.seek(len(frames))
                frames.append(img.copy())
        except EOFError:
            pass

        delay = int(1000/fps) if fps else 100
        frames[0].save(outfile, save_all=True, append_images=frames[1:], format="GIF", loop=0, duration=delay)
    else:
        img.save(outfile, format=convert_format_type(format))
    # Reset the buffer cursor to the beginning of the buffer.
    outfile.seek(0)
    return outfile

def pil_to_binary(img: Image.Image, format: str = "PNG"):
    if format.upper() == "GIF":
        binary_buffer = BytesIO()
        frames = []
        try:
            while True:
                img.seek(len(frames))
                frames.append(img.copy())
        except EOFError:
            pass

        if len(frames) > 1:
            frames[0].save(binary_buffer, save_all=True, append_images=frames[1:], format="GIF")
        else:
            frames[0].save(binary_buffer, format="GIF")
        binary_data = binary_buffer.getvalue()

        return binary_data

    binary_buffer = BytesIO()
    img.save(binary_buffer, format=convert_format_type(format))
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
