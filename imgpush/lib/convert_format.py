import imgpush.settings as settings
from PIL import Image

def convert_format_type(format: str, default_format: str = settings.OUTPUT_TYPE):
    format = format.upper()

    acceptable_formats = ['JPEG', 'JPG', 'PNG', 'BMP', 'GIF', 'JIFF', 'TIFF', 'WEBP']

    # Check if the output type is an acceptable format
    if format not in acceptable_formats:
        return default_format

    if format == 'JPG' or format == 'JIFF':
        return "JPEG"

    return format

def convert_image(image: Image.Image, output_format: str):
    output_format = convert_format_type(output_format)

    # Determine the output format
    if output_format == 'JPEG':
        mode = 'RGB'
    elif output_format == 'PNG':
        mode = 'RGBA'
    elif output_format == 'GIF':
        mode = 'P'
    else:
        mode = 'RGB'

    # Convert the image
    image = image.convert(mode)

    return image
