from PIL import Image
import imgpush.settings as settings
import timeout_decorator

def resize_image(img: Image.Image, width, height):
    current_aspect_ratio = img.width / img.height

    if not width:
        width = int(current_aspect_ratio * height)

    if not height:
        height = int(width / current_aspect_ratio)

    desired_aspect_ratio = width / height

    # Crop the image to fit the desired AR
    if desired_aspect_ratio > current_aspect_ratio:
        newheight = int(img.width / desired_aspect_ratio)
        img.crop(
            (0, int((img.height / 2) - (newheight / 2)), img.width, int((img.height / 2) + (newheight / 2)))
        )
    else:
        newwidth = int(img.height * desired_aspect_ratio)
        img.crop(
            (int((img.width / 2) - (newwidth / 2)), 0, int((img.width / 2) + (newwidth / 2)), img.height)
        )

    @timeout_decorator.timeout(settings.RESIZE_TIMEOUT, use_signals=False)
    def resize(img, width, height):
        return img.resize((width, height))

    try:
        resized = resize(img, width, height)
        img = resized
    except timeout_decorator.TimeoutError:
        pass

    return img
