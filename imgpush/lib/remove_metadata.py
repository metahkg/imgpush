from PIL import Image

def remove_metadata(img: Image.Image):
    if 'exif' in img.info:
        del img.info['exif']

    return img
