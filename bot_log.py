from datetime import datetime
import requests
from logging import getLogger, Formatter, StreamHandler, FileHandler, INFO

line_config = "ON"
log_config = "ON"
line_token = "r2bskf53K9MkZLIqVSdyy9qQ2H2lgxm7vppuV4q15oD"

timestamp = datetime.now().strftime('%Y-%m-%d-%H-%M')

BACKTEST = "ON"
if BACKTEST == "ON":
    log_file_path = f"backtest-log/samplebot_{timestamp}.log"
    line_config = "OFF"
    log_config = "ON"
else:
    log_file_path = f"bot-log/samplebot_{timestamp}.log"


if log_config == "ON":
    logger = getLogger(__name__)
    handlerSh = StreamHandler()
    handlerFile = FileHandler(log_file_path)
    handlerSh.setLevel(INFO)
    handlerFile.setLevel(INFO)
    logger.setLevel(INFO)
    logger.addHandler(handlerSh)
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
        logger.info(text)
    else:
        print(text)