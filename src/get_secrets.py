import json
import os
from bot_log import print_log

def get_secrets(filepath):

    if os.path.exists(filepath):
        with open(filepath) as secrets_json:
            secrets = json.load(secrets_json)
            if secrets["SECRETS"]["API_KEY"] and secrets["SECRETS"]["API_SECRET"]:
                return secrets
            else:
                print(f"{filepath}にデータが存在しません。プログラムを終了します。")
                quit()

    else:
        print(f"{filepath}が存在しません。プログラムを終了します。")
        quit()