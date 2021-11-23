
from .apl_host_ import Apl_Host
from .device_ import Device
from .hca_ import HCAs
from .linux_host_ import Linux_Host
from .switch_ import Switch
from .wrapper_ import Wapper
from .xlswriter_ import XlsWriter
import logging
import os 

class Constants():
    def __init__(self):
        pass

    if os.name == 'nt':
        root_folder = os.getcwd() + os.sep + 'result_files' + os.sep
    else:
        root_folder = "/qa/qa/arielwe/lab_report/result_files"

    root_report_lab = root_folder + os.sep + 'report' + os.sep
    root_switch = root_folder + os.sep + 'switches' + os.sep
    root_hcas = root_folder + os.sep + 'hcas' + os.sep
    root_servers = root_folder + os.sep + 'servers' + os.sep
