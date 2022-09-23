import requests
from logging import getLogger, Formatter, StreamHandler, FileHandler, INFO

line_config = "OFF"
log_config = "OFF"
log_file_path = "test.log"
line_token = ""

if log_config == "ON":
    logger = getLogger(__name__)
    handlerSh = StreamHandler()
    handerFile = FileHandler(log_file_path)
    handlerSh.setLevel(INFO)
    handlerFile.setLevel(INFO)
    logger.setLevel(INFO)
    logger.addHandler(handlerSj)
    logger.addHandler(handlerFile)


def print_log(text):

    if line_config == "ON":
        url = "https://notify-api.line.me/api/notify"
        data = {"message": str(text)}
        headers = {"Authorization": "Bearer " + line_token}
        try:
            requests.post(url, data=data, headers=headers)
        except requests.exceptions.RequestException as e:
            if log_config == "ON":
                logger.info(str(e))
            else:
                print(text)

    if log_config == "ON":
        logger.info(str(e))
    else:
        print(text)