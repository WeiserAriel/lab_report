import logging
import os
import shutil


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
    root_cables = root_folder + os.sep + 'cables' + os.sep
    root_ufm_versions = root_folder + os.sep + 'ufm_versions' + os.sep
    root_gpu_versions = root_folder + os.sep + 'gpu_versions' + os.sep
    ignore_devices = ['smg-ib-sw009','smg-ib-sw010','r-hpc-mg14','smg-ib-olg001-mgmt01','smg-ib-sim001','smg-ib-apl007-gen2','smg-ib-apl012-gen2','smg-ib-apl008-gen2','r-hpc09']


    @staticmethod
    def create_directories():
        logging.info('Start creating directories for all Constants folders')
        folders = [Constants.root_report_lab, Constants.root_switch, Constants.root_hcas, Constants.root_servers, ]
        try:
            for folder in folders:
                if os.path.isdir(folder):
                    shutil.rmtree(folder)

                os.makedirs(folder, exist_ok=True)
                os.chmod(folder, 0o777)
        except Exception as e:
            logging.error('could not create/give permission for folder : '+ folder + ' ' + str(e))
            exit(-1)

        logging.info('Start creating directories for all Constants folders are done ')

