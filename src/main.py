#Import classes#



# from classes import Apl_

from src.classes.hca_ import HCAs

from classes.wrapper_ import Wapper
from classes.xlswriter_ import XlsWriter

###################################################


import argparse
import logging
import warnings
with warnings.catch_warnings():
    import paramiko
    warnings.filterwarnings(action='ignore', module='.*paramiko.*')

import os
import sys
import re
import platform    # For getting the operating system name
import subprocess  # For executing a shell command
import time
from datetime import date
import xlsxwriter
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import json
import time
import shutil


import csv
#from pyping.core import *
#import pyping




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
    tmp = HCAs()
    #exit(0)
    email_list = Wapper.parse_email_file(args.email)
    device_list_ip = Wapper.parse_device_list(args.device_list)
    devices_obj = Wapper.Create_devices_objects(device_list_ip)
    xls = XlsWriter(devices_obj,email_list)
    #counting number of error in log
    dir_ = os.getcwd()
    file = "lab_report.log"
    filename = dir_ + os.sep + file
    f = open(filename, "r")
    info = re.findall('ERROR', f.read())

    if info:
        print('\nScript has finished with :'+ str(len(info)) + ' errors')
    else:
        print('\nScript is ended with 0 errors')



if __name__ == '__main__':
    main()


