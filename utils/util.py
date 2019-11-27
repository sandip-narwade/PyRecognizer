# -*- coding: utf-8 -*-
"""
Common method for reuse code

Generate certificate

openssl req -x509 -out localhost.crt -keyout localhost.key \
  -newkey rsa:2048 -nodes -sha256 \
  -subj '/CN=localhost' -extensions EXT -config <( \
   printf "[dn]\nCN=localhost\n[req]\ndistinguished_name = dn\n[EXT]\nsubjectAltName=DNS:localhost\nkeyUsage=digitalSignature\nextendedKeyUsage=serverAuth")


"""
import json
import logging
import os
import pickle
import random
import shutil
import string
import zipfile
from logging.handlers import TimedRotatingFileHandler

import PIL
import numpy as np
from PIL import Image, ImageDraw

levels = {
    'debug': logging.DEBUG,
    'info': logging.INFO,
    'warning': logging.WARNING,
    'error': logging.ERROR,
    'critical': logging.CRITICAL
}


def print_prediction_on_image(img_path, predictions, path_to_save, file_to_save):
    """
    Shows the face recognition results visually.

    :param path_to_save:
    :param file_to_save:
    :param img_path: path to image to be recognized
    :param predictions: results of the predict function
    :return:
    """
    pil_image = Image.open(img_path).convert("RGB")
    draw = ImageDraw.Draw(pil_image)

    for name, (top, right, bottom, left) in predictions:
        # Draw a box around the face using the Pillow module
        draw.rectangle(((left, top), (right, bottom)), outline=(0, 0, 255))

        # There's a bug in Pillow where it blows up with non-UTF-8 text
        # when using the default bitmap font
        name = name.encode("UTF-8")

        # Draw a label with a name below the face
        _, text_height = draw.textsize(name)
        draw.rectangle(((left, bottom - text_height - 10),
                        (right, bottom)), fill=(0, 0, 255), outline=(0, 0, 255))
        draw.text((left + 6, bottom - text_height - 5),
                  name, fill=(255, 255, 255, 255))
    # Remove the drawing library from memory as per the Pillow docs
    del draw

    # Display the resulting image
    # pil_image.show()
    pil_image.save(os.path.join(path_to_save, file_to_save), "PNG")


def init_main_data(config_file):
    """
    Parse the configuration file and return the necessary data for initalize the tool
    :param config_file:
    :return:
    """
    try:
        with open(config_file) as f:
            CFG = json.load(f)
    except json.decoder.JSONDecodeError:
        raise Exception("Unable to load JSON File: {}".format(config_file))

    log = load_logger(CFG["logging"]["level"], CFG["logging"]
                      ["path"], CFG["logging"]["prefix"])

    # NOTE: create a directory every time that you need to use this folder
    TMP_UPLOAD_PREDICTION = CFG["PyRecognizer"]["temp_upload_predict"]
    TMP_UPLOAD_TRAINING = CFG["PyRecognizer"]["temp_upload_training"]
    TMP_UPLOAD = CFG["PyRecognizer"]["temp_upload"]

    if not os.path.exists(TMP_UPLOAD_PREDICTION):
        os.makedirs(TMP_UPLOAD_PREDICTION)
    if not os.path.exists(TMP_UPLOAD_TRAINING):
        os.makedirs(TMP_UPLOAD_TRAINING)
    if not os.path.exists(TMP_UPLOAD):
        os.makedirs(TMP_UPLOAD)

    return CFG, log, TMP_UPLOAD_PREDICTION, TMP_UPLOAD_TRAINING, TMP_UPLOAD


def load_logger(level, path, name):
    """

    :param level:
    :param path:
    :param name:
    """
    logger = logging.getLogger()  # set up root logger
    if not os.path.exists(path):
        os.makedirs(path)
    filename = '{0}{1}'.format(path, name)
    handler = TimedRotatingFileHandler(filename, when='H')
    handler.suffix = "%Y-%m-%d.log"
    handler.extMatch = r"^\d{4}-\d{2}-\d{2}\.log$"

    level = levels[level]
    handler.setLevel(level)  # set level for handler
    formatter = '%(asctime)s - %(name)s - %(levelname)s | [%(filename)s:%(lineno)d] | %(message)s'
    handler.setFormatter(logging.Formatter(formatter))
    logger.addHandler(handler)
    logger.setLevel(level)
    return logger


def random_string(string_length=10):
    """
    Generate a random string of fixed length
    :param string_length:
    :return:
    """
    letters = string.ascii_lowercase
    data = ""
    for _ in range(string_length):
        data += random.choice(letters)
    return data


def zip_data(file_to_zip, path):
    """

    :param file_to_zip:
    :param path:
    :return:
    """

    shutil.make_archive(file_to_zip, 'zip', path)


def unzip_data(unzipped_folder, zip_file):
    """
    Unzip the zip file in input in the given 'unzipped_folder'
    :param unzipped_folder:
    :param zip_file:
    :return: The name of the folder in which find the unzipped data
    """
    log = logging.getLogger()
    folder_name = os.path.join(unzipped_folder, random_string())
    log.debug("unzip_data | Unzipping {} into {}".format(zip_file, folder_name))
    zip_ref = zipfile.ZipFile(zip_file)
    zip_ref.extractall(folder_name)
    zip_ref.close()
    log.debug("unzip_data | File uncompressed!")
    return folder_name


def dump_dataset(X, Y, path):
    """

    :param X:
    :param Y:
    :param path:
    :return:
    """
    log = logging.getLogger()
    dataset = {
        'X': X,
        'Y': Y
    }
    log.debug("dump_dataset | Dumping dataset int {}".format(path))
    if not os.path.exists(path):
        os.makedirs(path)
        log.debug("dump_dataset | Path {} exist".format(path))
        dataset_name = os.path.join(path, "model.dat")
        with open(dataset_name, 'wb') as f:
            pickle.dump(dataset, f)
    else:
        log.error(
            "dump_dataset | Path {} ALREDY EXIST exist, avoiding to overwrite".format(path))


def remove_dir(directory):
    """
    Wrapper for remove a directory
    :param directory:
    :return:
    """
    log = logging.getLogger()
    log.debug("remove_dir | Removing directory {}".format(directory))
    if os.path.isdir(directory):
        shutil.rmtree(directory)


def verify_extension(file):
    """
    Wrapper for validate file
    :param file:
    :return:
    """
    log = logging.getLogger()
    extension = os.path.splitext(file)[1]
    log.debug("verify_extension | File: {} | Ext: {}".format(file, extension))

    if extension == ".zip":
        zp = zipfile.ZipFile(file)
        size = sum([zinfo.file_size for zinfo in zp.filelist])
        zip_kb = float(size)/(1000*1000)  # MB
        if zip_kb > 1000:
            raise Exception("Zip file size is to much ...")
        return "zip"

    elif extension == ".dat":
        # Photos have been alredy analyzed, dataset is ready!
        return "dat"
    return None


def retrieve_dataset(folder_uncompress, zip_file, clf):
    """

    :param folder_uncompress:
    :param zip_file:
    :param clf:
    :return:
    """
    log = logging.getLogger()
    log.debug("retrieve_dataset | Parsing dataset ...")
    check = verify_extension(zip_file.filename)
    if check == "zip":  # Image provided
        log.debug("retrieve_dataset | Zip file uploaded")
        folder_name = unzip_data(folder_uncompress, zip_file)
        log.debug("retrieve_dataset | zip file uncompressed!")
        clf.init_peoples_list(peoples_path=folder_name)
        dataset = clf.init_dataset()
        log.debug("retrieve_dataset | Removing [{}]".format(folder_name))
        remove_dir(folder_name)
    elif check == "dat":
        log.debug("retrieve_dataset | Pickle data uploaded")
        dataset = pickle.load(zip_file)
    else:
        dataset = None
    log.debug("tune_network | Dataset parsed!")
    return dataset


def secure_request(request, ssl):
    """

    :param ssl:
    :param request:
    :return:
    """
    # request.headers['Content-Security-Policy'] = "script-src 'self' cdnjs.cloudflare.com ; "
    request.headers['Feature-Policy'] = "geolocation 'none'; microphone 'none'; camera 'self'"
    request.headers['Referrer-Policy'] = 'no-referrer'
    request.headers['Strict-Transport-Security'] = "max-age=60; includeSubDomains; preload"
    request.headers['x-frame-options'] = 'SAMEORIGIN'
    request.headers['X-Content-Type-Options'] = 'nosniff'
    request.headers['X-Permitted-Cross-Domain-Policies'] = 'none'
    request.headers['X-XSS-Protection'] = '1; mode=block'
    if ssl:
        request.headers['expect-ct'] = 'max-age=60, enforce'

    return request


def load_image_file(file, mode='RGB',):
    """
    Loads an image file (.jpg, .png, etc) into a numpy array

    :param file: image file name or file object to load
    :param mode: format to convert the image to. Only 'RGB' (8-bit RGB, 3 channels) and 'L' (black and white) are supported.
    :return: image contents as numpy array
    """

    im = PIL.Image.open(file)
    width, height = im.size
    w, h = width, height
    log = logging.getLogger()
    log.debug("load_image_file | Image dimension: ({}:{})".format(w,h))
    # Resize in case of to bigger dimension
    if 1200 <= width <= 1600:
        w = width * (1/2)
        h = height * (1/2)
    elif 1600 <= width <= 3600:
        w = width * (1/3)
        h = height * (1/3)
    # TODO: Prettify the algorithm instead of set 800
    else:
        w = (800/width) * width
        h = (800/height) * height

    if w != width:
        maxsize = (w, h)
        log.debug(
            "load_image_file | Image have to high dimension, avoiding memory error. Resizing to {}".format(maxsize))
        im.thumbnail(maxsize, PIL.Image.ANTIALIAS)

    if mode:
        im = im.convert(mode)
    return np.array(im)
