import json
import logging
import os.path

import requests
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from src.classes.constant_ import Constants

class Cables():

    def __init__(self, device_name,owner):
        self.device_name = device_name
        self.owner = owner
        logging.debug("Start Cables Class")
        self.cables_file = Constants.root_cables
        self.session = None
        self.open_session()
        self.send_cables_request()
        logging.debug("End Cables Class")


    def open_session(self):
        try:
            self.session = requests.Session()
            headers = {}
            headers["Accept"] = "application/json"
            self.session.headers = headers
            self.session.auth = ('admin', '123456')
        except Exception as e:
            logging.error(f"Execution in open session for {self.device_name} {str(e)}")

    def send_cables_request(self):
        try:
            url = f"https://{self.device_name}/ufmRest/resources/links?cable_info=true&monitoring_counters_info=false&page_number=1&rpp=1000"
            res = self.session.get(url, verify=False, allow_redirects=True)
            if str(res.status_code) == str(200):
                j = json.loads(res.text)
                j["owner_name"] = self.owner
                j["device_name"] = self.device_name
                self.save_json(j)
            else:
                logging.critical(f"request of getting cable request ended with status code : {str(res.status_code)} altough ufm is running ")
        except Exception as e:
            logging.error('Exception was received in send cables request ' + str(e))

    def save_json(self, dict):
        dir = Constants.root_cables
        logging.debug(f"check if cables dir exist : {dir}" )
        try:
            if not os.path.exists(dir):
                logging.debug("not exist")
                os.mkdir(dir)
            try:
                new_dir = dir + os.sep + self.device_name
                logging.debug(f"checking if sub-directory was created : {str(new_dir)}")
                if not os.path.exists(new_dir):
                    logging.debug(f"creating new dir : {str(new_dir)}")
                    os.mkdir(new_dir)
                filename = f"{new_dir}{os.sep}cables.json"
                with open(filename, 'w') as outfile:
                    json.dump(dict, outfile)
            except Exception as e:
                logging.error(f"Exception in dumping json into file in device {self.device_name} : {str(e)}")
        except Exception as e:
            logging.error(f"Exception received in save json in cable class : {str(e)}")

        logging.debug(f"dumpping json of device : {self.device_name} has finished succussfully")

