import sys
import os

myDir = os.getcwd()
sys.path.append(myDir)

import ipaddress
import logging
import socket
import urllib.request
from io import BytesIO
from urllib.parse import urlparse
import filetype
import gridfs
from bson import ObjectId
from flask import Flask, jsonify, request, send_from_directory, Response, g, send_file
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from pymongo import MongoClient
from werkzeug.middleware.proxy_fix import ProxyFix
from PIL import Image, ImageOps, UnidentifiedImageError
from imgpush.lib.utils import pil_to_file, pil_to_binary, get_size_from_string
from imgpush.lib.resize_image import resize_image
from imgpush.lib.filename import get_random_filename
from imgpush.lib.errors import CollisionError, InvalidSize
import settings
from imgpush.lib.jwt import verify

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app)
app.logger.setLevel(logging.INFO)

use_mongo: bool = settings.USE_MONGO
if use_mongo:
    logger.info("Using mongodb gridfs for storage")
    client: MongoClient = MongoClient(settings.MONGO_URI)
    db = client["imgpush"]
    fs: gridfs.GridFS = gridfs.GridFS(db)
else:
    logger.info("Using local filesystem for storage")
    client, db, fs = None, None, None

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

    random_string = get_random_filename()
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
            try:
                urllib.request.urlretrieve(request.json["url"], tmp_filepath)
            except:
                return jsonify(error="Failed to download file"), 500
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
        with Image.open(tmp_filepath) as img:
            img = ImageOps.exif_transpose(img)
            if use_mongo:
                output_file = fs.put(pil_to_binary(img, output_type),
                                     filename=output_filename, metadata={"type": output_type})
                logger.info(f"Uploaded file {output_filename} with ObjectID({str(output_file)}) to GridFS")
            with img.convert("RGBA") as converted:
                converted.save(output_path, format=output_type)
    except UnidentifiedImageError:
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

    try:
        width = get_size_from_string(width)
        height = get_size_from_string(height)
    except InvalidSize:
        return (
            jsonify(error=f"size value must be one of {settings.VALID_SIZES}"),
            400,
        )

    if use_mongo:
        try:
            if fs.exists({"filename": filename}) is False:
                raise FileNotFoundError
            fs_id = fs.find_one({"filename": filename})
            file = fs.get(ObjectId(fs_id._id))
        except Exception as e:
            logger.error(e)
            return jsonify(error="File not found"), 404

        if settings.DISABLE_RESIZE is True or not (width or height):
            return send_file(BytesIO(file.read()), mimetype=str(file.metadata['type']))

        dimensions = f"{width}x{height}"
        filename_without_extension, extension = os.path.splitext(filename)
        resized_filename = filename_without_extension + f"_{dimensions}{extension}"
        if fs.exists({"filename": resized_filename}) is False:
            try:
                resized_image = resize_image(Image.open(file), width, height)
                fs.put(pil_to_binary(resized_image, extension[1:]), filename=resized_filename)
                resized_image = pil_to_file(resized_image, extension[1:])
                logger.info(f"Resized file {filename} to {width}x{height}, type: {file.metadata['type']}")
            except Exception as e:
                logger.error(e)
                return jsonify(error="Failed to resize image"), 500
        else:
            fs_id = fs.find_one({"filename": resized_filename})
            resized_image = BytesIO(fs.get(ObjectId(fs_id._id)).read())

        return send_file(resized_image, file.metadata['type'])

    if settings.DISABLE_RESIZE is not True and ((width or height) and (os.path.isfile(path))):
        dimensions = f"{width}x{height}"
        filename_without_extension, extension = os.path.splitext(filename)
        resized_filename = filename_without_extension + f"_{dimensions}{extension}"
        resized_path = os.path.join(settings.CACHE_DIR, resized_filename)

        if not os.path.isfile(resized_path) and (width or height):
            try:
                resized_image = resize_image(Image.open(path), width, height)
                resized_image = ImageOps.exif_transpose(resized_image)
                resized_image.save(resized_path, format=extension[1:])
                resized_image.close()
                logger.info(f"Resized file {filename} to {width}x{height}, type: {file.metadata['type']}")
            except Exception as e:
                logger.error(e)
                return jsonify(error="Failed to resize image"), 500
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
    if use_mongo:
        try:
            if fs.exists({"filename": filename}):
                fs.delete(fs.find_one({"filename": filename}))
                return jsonify(success=True), 204
            else:
                raise FileNotFoundError
        except Exception as e:
            logger.error(e)
            return jsonify(error="File not found"), 404
    path = os.path.join(settings.IMAGES_DIR, filename)
    if os.path.isfile(path):
        os.remove(path)
    else:
        return jsonify(error="File not found"), 404

    return Response(status=204)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=settings.PORT, threaded=True)
