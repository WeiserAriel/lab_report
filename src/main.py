import sys

from src.classes.hca_ import HCAs
from src.classes.constant_ import Constants
from src.classes.wrapper_ import Wapper
from src.classes.xlswriter_ import XlsWriter

###################################################

import argparse
import logging
import warnings
with warnings.catch_warnings():
    import paramiko
    warnings.filterwarnings(action='ignore', module='.*paramiko.*')

import os
import re
import datetime





def main():
    parser = argparse.ArgumentParser(description='This is tool generate report for all lab devices')
    parser.add_argument('--device_list',     dest='device_list', help='path to device list file', required=True)
    parser.add_argument('--email', dest='email', help='email list written in text file', required=True)
    parser.add_argument('--debug', dest='debug', action='store_true', help='change to debug mode')

    args = parser.parse_args()

    if args.debug:
        level = logging.DEBUG
    else:
        level = logging.INFO
    log_file = os.path.dirname(os.path.abspath(__file__)) + os.sep + 'lab_report.log'
    logging.basicConfig(filename=log_file,
                        level=level,
                        format='%(asctime)s %(levelname)-8s %(message)s',
                        datefmt='%m-%d %H:%M',
                        filemode='w')

    logging.info("lab report Script Start...")
    print('Log file Path: ' + log_file)
    begin_time = datetime.datetime.now()
    Constants.create_directories()
    tmp = HCAs()
    email_list = Wapper.parse_email_file(args.email)
    device_list_ip = Wapper.parse_device_list(args.device_list)

    devices_obj = Wapper.Create_devices_objects(device_list_ip)
    xls = XlsWriter(devices_obj,email_list)
    #counting number of error in log
    dir_ = os.getcwd()
    file = "lab_report.log"
    filename = log_file
    f = open(filename, "r")
    Wapper.check_empty_files(Constants.root_folder)
    info = re.findall('ERROR', f.read())



    print('Script finished after : '+  str(datetime.datetime.now() - begin_time))



    print('Log file Path: ' + log_file)


    if info:
        print('\nScript has finished with :'+ str(len(info)) + ' errors')
        return int(len(info))
    else:
        print('\nScript is ended with 0 errors')
        return 0




if __name__ == '__main__':
    sys.exit(main())











