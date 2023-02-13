import datetime
import time
import glob
import os
import random
import string
import urllib.request
import uuid

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
    try:
        user = verify(request.headers.get('Authorization')[7:])
        if user:
            g.user = user
        else:
            g.user = None
    except:
        g.user = None


@app.after_request
def after_request(resp):
    x_sendfile = resp.headers.get("X-Sendfile")
    if x_sendfile:
        resp.headers["X-Accel-Redirect"] = "/nginx/" + x_sendfile
        del resp.headers["X-Sendfile"]
    resp.headers["Referrer-Policy"] = "no-referrer-when-downgrade"
    return resp


class InvalidSize(Exception):
    pass


class CollisionError(Exception):
    pass


def _get_size_from_string(size):
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
    random_string = _generate_random_filename()
    if settings.NAME_STRATEGY == "randomstr":
        file_exists = len(glob.glob(f"{settings.IMAGES_DIR}/{random_string}.*")) > 0
        if file_exists:
            return _get_random_filename()
    return random_string


def _generate_random_filename():
    if settings.NAME_STRATEGY == "uuidv4":
        return str(uuid.uuid4())
    if settings.NAME_STRATEGY == "randomstr":
        return "".join(
            random.choices(
                string.ascii_lowercase + string.digits + string.ascii_uppercase, k=6
            )
        )


def _resize_image(path, width, height):
    filename_without_extension, extension = os.path.splitext(path)

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
    if (settings.UPLOAD_REQUIRE_AUTH == True or settings.UPLOAD_REQUIRE_AUTH == "true"):
        if not g.get("user"):
            return jsonify(error="Unauthorized"), 401
    _clear_imagemagick_temp_files()

    random_string = _get_random_filename()
    tmp_filepath = os.path.join("/tmp/", random_string)

    if "file" in request.files:
        file = request.files["file"]
        file.save(tmp_filepath)
    elif (settings.DISABLE_URL_UPLOAD != True and settings.DISABLE_URL_UPLOAD != "true") and "url" in request.json:
        urllib.request.urlretrieve(request.json["url"], tmp_filepath)
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
                with img.sequence[0] as first_frame:
                    with Image(image=first_frame) as first_frame_img:
                        with first_frame_img.convert(output_type) as converted:
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

    return jsonify(filename=output_filename, path=f"{settings.IMAGES_ROOT}/{output_filename}", url=f"{request.host_url[:-1]}{settings.IMAGES_ROOT}/{output_filename}"), 200


@app.route(f"{settings.IMAGES_ROOT}/<string:filename>")
@limiter.exempt
def get_image(filename):
    if (settings.GET_REQUIRE_AUTH == True or settings.GET_REQUIRE_AUTH == "true"):
        if not g.get("user"):
            return jsonify(error="Unauthorized"), 401
    width = request.args.get("w", "")
    height = request.args.get("h", "")

    path = os.path.join(settings.IMAGES_DIR, filename)

    if (settings.DISABLE_RESIZE != True and settings.DISABLE_RESIZE != "true") and ((width or height) and (os.path.isfile(path))):
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
