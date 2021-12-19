
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
    ignore_devices = ['smg-ib-sw009','smg-ib-sw010','r-hpc-mg14']
