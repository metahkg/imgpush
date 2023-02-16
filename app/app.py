import datetime
import time
import glob
import os
import random
import string
import urllib.request
from urllib.parse import urlparse
import uuid
import ipaddress
import socket

import filetype
import timeout_decorator
from flask import Flask, jsonify, request, send_from_directory, Response, g
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from wand.exceptions import MissingDelegateError
from wand.image import Image
from werkzeug.middleware.proxy_fix import ProxyFix
from jwt import verify

import settings

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app)

CORS(app, origins=settings.ALLOWED_ORIGINS)
app.config["MAX_CONTENT_LENGTH"] = settings.MAX_SIZE_MB * 1024 * 1024
limiter = Limiter(app, default_limits=[])

app.USE_X_SENDFILE = True


@app.before_request
def before_request():
    """
    The before_request function is called before the request handler function.
    It sets g.user to the user object if a valid authorization header is provided,
    otherwise it sets g.user to None.

    :return: The user object if a valid token is
    :doc-author: Trelent
    """
    try:
        user = verify(request.headers.get('Authorization')[7:])
        if user:
            g.user = user
        else:
            g.user = None
    except Exception:
        g.user = None


@app.after_request
def after_request(resp):
    """
    The after_request function is a Flask decorator that modifies the response
    object before it is returned to the client. The X-Sendfile header allows for
    the use of Nginx as a proxy server, which can significantly speed up file
    transfers. This function also sets Referrer-Policy to &quot;no-referrer-when-downgrade&quot;.

    :param resp: Return the response to the user
    :return: The response object
    :doc-author: Trelent
    """
    x_sendfile = resp.headers.get("X-Sendfile")
    if x_sendfile:
        resp.headers["X-Accel-Redirect"] = "/nginx/" + x_sendfile
        del resp.headers["X-Sendfile"]
    resp.headers["Referrer-Policy"] = "no-referrer-when-downgrade"
    return resp


class InvalidSize(Exception):
    """
    Raised when the size of the image is invalid.
    """
    pass


class CollisionError(Exception):
    """
    Raised when the filename is already present.
    """
    pass


def _get_size_from_string(size):
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


def _clear_imagemagick_temp_files():
    """
    A bit of a hacky solution to prevent exhausting the cache ImageMagick uses on disk.
    It works by checking for imagemagick cache files under /tmp/
    and removes those that are older than settings.MAX_TMP_FILE_AGE in seconds.
    """
    imagemagick_temp_files = glob.glob("/tmp/magick-*")
    for filepath in imagemagick_temp_files:
        modified = datetime.datetime.strptime(
            time.ctime(os.path.getmtime(filepath)), "%a %b %d %H:%M:%S %Y",
        )
        diff = datetime.datetime.now() - modified
        seconds = diff.seconds
        if seconds > settings.MAX_TMP_FILE_AGE:
            os.remove(filepath)


def _get_random_filename():
    """
    The _get_random_filename function generates a random filename for an image.
    It does this by generating a random string of length settings.RANDOM_STRING_LENGTH,
    and then appending the appropriate file extension based on the MIME type of the image.
    If that filename already exists in IMAGES_DIR, it will generate another one and check if it exists again.

    :return: A random string of length 8
    :doc-author: Trelent
    """
    random_string = _generate_random_filename()
    if settings.NAME_STRATEGY == "randomstr":
        file_exists = len(glob.glob(f"{settings.IMAGES_DIR}/{random_string}.*")) > 0
        if file_exists:
            return _get_random_filename()
    return random_string


def _generate_random_filename():
    """
    The _generate_random_filename function generates a random filename for the uploaded file.
    The function is called by the upload_file() function, which uses it to generate a filename for each uploaded file.
    The _generate_random_filename() function accepts no arguments and returns a string containing the randomly generated filename.

    :return: A random string of length 6
    :doc-author: Trelent
    """
    if settings.NAME_STRATEGY == "uuidv4":
        return str(uuid.uuid4())
    if settings.NAME_STRATEGY == "randomstr":
        return "".join(
            random.choices(
                string.ascii_lowercase + string.digits + string.ascii_uppercase, k=6
            )
        )
    return None


def _resize_image(path, width, height):
    """
    The _resize_image function takes a path to an image and resizes it to the specified width and height.
    If either width or height is not specified, the function will resize the image so that its current aspect ratio matches that of
    the desired dimensions. If both are not specified, then no resizing occurs.

    :param path: Specify the image to be resized
    :param width: Set the width of the image
    :param height: Resize the image to a specific height
    :return: An image object
    :doc-author: Trelent
    """

    with Image(filename=path) as src:
        img = src.clone()

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
            0,
            int((img.height / 2) - (newheight / 2)),
            width=img.width,
            height=newheight,
        )
    else:
        newwidth = int(img.height * desired_aspect_ratio)
        img.crop(
            int((img.width / 2) - (newwidth / 2)), 0, width=newwidth, height=img.height,
        )

    @timeout_decorator.timeout(settings.RESIZE_TIMEOUT)
    def resize(img, width, height):
        img.sample(width, height)

    try:
        resize(img, width, height)
    except timeout_decorator.TimeoutError:
        pass

    return img


@app.route("/", methods=["GET"])
def root():
    """
    The root function returns a string containing the HTML for an upload form.

    :return: A form that will allow the user to upload a file
    :doc-author: Trelent
    """
    if settings.DISABLE_UPLOAD_FORM:
        return jsonify(error="Not found"), 404
    return f"""
<form action="{settings.UPLOAD_ROUTE}" method="post" enctype="multipart/form-data">
    <input type="file" name="file" id="file">
    <input type="submit" value="Upload" name="submit">
</form>
"""


@app.route("/liveness", methods=["GET"])
def liveness():
    """
    The liveness function is used to determine if the server is still alive.
    It returns a status code of 200, indicating that the server is alive.

    :return: A status code of 200, indicating that the function is running
    :doc-author: Trelent
    """
    return Response(status=200)


@app.route(settings.UPLOAD_ROUTE, methods=["POST"])
@limiter.limit(
    "".join(
        [
            f"{settings.MAX_UPLOADS_PER_DAY}/day;",
            f"{settings.MAX_UPLOADS_PER_HOUR}/hour;",
            f"{settings.MAX_UPLOADS_PER_MINUTE}/minute",
        ]
    ),
    key_func=lambda: f"user{g.get('user')['id']}" if g.get("user") else get_remote_address()
)
def upload_image():
    """
    The upload_image function is used to upload an image file to the server.
    It accepts a POST request with either a file or url field, and returns the filename of the uploaded image.
    If there is an error uploading, it will return a 400 response with an error message.

    :return: A json object containing the filename,
    :doc-author: Trelent
    """
    if (
        settings.UPLOAD_REQUIRE_AUTH is True
        and not g.get("user")
    ):
        return jsonify(error="Unauthorized"), 401
    _clear_imagemagick_temp_files()

    random_string = _get_random_filename()
    tmp_filepath = os.path.join("/tmp/", random_string)

    if "file" in request.files:
        file = request.files["file"]
        file.save(tmp_filepath)
    elif settings.DISABLE_URL_UPLOAD is not True and "url" in request.json:
        if request.json["url"].lower().startswith('http'):
            ip: (ipaddress.IPv4Address | ipaddress.IPv6Address) = None
            try:
                ip = ipaddress.ip_address(socket.gethostbyname(urlparse(request.json["url"]).netloc))
            except Exception:
                return jsonify(error="Failed to resolve host"), 400
            if ip.is_private or ip.is_loopback or ip.is_link_local:
                return jsonify(error="Refusing to connect to local or private address"), 400
            urllib.request.urlretrieve(request.json["url"], tmp_filepath)
        else:
            return jsonify(error="Invalid URL"), 400
    else:
        return jsonify(error="File is missing!"), 400

    output_type = settings.OUTPUT_TYPE or filetype.guess_extension(tmp_filepath)
    error = None

    output_filename = os.path.basename(tmp_filepath) + f".{output_type}"
    output_path = os.path.join(settings.IMAGES_DIR, output_filename)

    try:
        if os.path.exists(output_path):
            raise CollisionError
        with Image(filename=tmp_filepath) as img:
            img.strip()
            if output_type not in ["gif"]:
                with img.sequence[0] as first_frame, Image(image=first_frame) as first_frame_img, first_frame_img.convert(output_type) as converted:
                    converted.save(filename=output_path)
            else:
                with img.convert(output_type) as converted:
                    converted.save(filename=output_path)
    except MissingDelegateError:
        error = "Invalid Filetype"
    finally:
        if os.path.exists(tmp_filepath):
            os.remove(tmp_filepath)

    if error:
        return jsonify(error=error), 400

    return jsonify(filename=output_filename,
                    path=f"{settings.IMAGES_ROOT}/{output_filename}",
                    url=f"{request.host_url[:-1]}{settings.IMAGES_ROOT}/{output_filename}"), 200


@app.route(f"{settings.IMAGES_ROOT}/<string:filename>")
@limiter.exempt
def get_image(filename):
    """
    The get_image function is responsible for serving up images from the
       image directory. It accepts a filename as an argument, and returns an
       image file from the cache directory if it exists, or else it will return
       the original image file itself. If resize parameters are passed in with
       the request (e.g., w=100), then get_image will create a resized version of
       that image and serve that back instead.

    :param filename: Determine the path to the image file
    :return: The image with the given filename
    :doc-author: Trelent
    """
    if settings.GET_REQUIRE_AUTH is True and not g.get("user"):
        return jsonify(error="Unauthorized"), 401
    width = request.args.get("w", "")
    height = request.args.get("h", "")

    path = os.path.join(settings.IMAGES_DIR, filename)

    if settings.DISABLE_RESIZE is not True and ((width or height) and (os.path.isfile(path))):
        try:
            width = _get_size_from_string(width)
            height = _get_size_from_string(height)
        except InvalidSize:
            return (
                jsonify(error=f"size value must be one of {settings.VALID_SIZES}"),
                400,
            )

        filename_without_extension, extension = os.path.splitext(filename)
        dimensions = f"{width}x{height}"
        resized_filename = filename_without_extension + f"_{dimensions}.{extension}"

        resized_path = os.path.join(settings.CACHE_DIR, resized_filename)

        if not os.path.isfile(resized_path) and (width or height):
            _clear_imagemagick_temp_files()
            resized_image = _resize_image(path, width, height)
            resized_image.strip()
            resized_image.save(filename=resized_path)
            resized_image.close()
        return send_from_directory(settings.CACHE_DIR, resized_filename)

    return send_from_directory(settings.IMAGES_DIR, filename)

# https://github.com/hauxir/imgpush/pull/33


@app.route(f"{settings.IMAGES_ROOT}/<string:filename>", methods=["DELETE"])
def delete_image(filename):
    """
    The delete_image function deletes an image from the images directory.
    It takes a filename as its only argument and returns nothing.

    :param filename: Specify the filename of the image to be deleted
    :return: A response object with status code 204
    :doc-author: Trelent
    """
    if getattr(g.get("user"), "role", None) != "admin":
        return jsonify(error="Permission denied"), 403
    path = os.path.join(settings.IMAGES_DIR, filename)
    if os.path.isfile(path):
        os.remove(path)
    else:
        return jsonify(error="File not found"), 404

    return Response(status=204)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=settings.PORT, threaded=True)
