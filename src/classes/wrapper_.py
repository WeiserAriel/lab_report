
from src.classes.apl_host_ import Apl_Host
from src.classes.linux_host_ import Linux_Host
from src.classes.switch_ import Switch
from src.classes.constant_ import Constants
from src.classes.device_ import Device
import glob
import re

import logging
import os

class Wapper():

    @staticmethod
    def check_empty_files(root_path):
        logging.info('Make sure there is no empty files in root directory')
        os.chdir(root_path)

        for file in glob.glob(root_path + '/**/*.json', recursive=True):
            logging.debug('Check if ' + file + ' is empty :')
            if os.path.getsize(file) > 0:
                logging.debug('File is not Empty')
            else:
                logging.error('file : ' + str(file) + ' is empty')

        logging.info('finish function of check empty files ')


    @staticmethod
    def split_range(part):
        cointainer = []
        logging.debug("spliting range of hosts")
        base = part.split('[')[0]
        tail = part.split('[')[1]
        tail = tail.split(']')[0]
        num_of_zeros = 0
        tmp = tail.split('-')[0]
        structure = 3
        if 'r-hpc' in part:
            structure = 2


        starts = int(tail.split('-')[0])
        ends = int(tail.split('-')[1])
        while starts <= ends:
            num_of_zeros = structure - len(str(starts))
            tmp = '0'*num_of_zeros + str(starts)
            tmp_dev = base + tmp
            logging.debug("adding " + str(tmp_dev) + ' to container ')
            cointainer.append(tmp_dev)
            starts +=1


        return cointainer

    @staticmethod
    def get_devices_in_row(row):
        
        devices = {}
        #split the row to ',':
        try:
            owner = row.split(':')[0]
            row_without_owner = row.split(':')[1]
            row_commas = row_without_owner.split(',')
            for part in row_commas:
                if part == '':
                    continue
                if '[' in part:
                    devs = Wapper.split_range(part)
                    for dev in devs:
                        devices[dev] = owner
                        #devices.append(dev)
                else:
                    logging.debug('adding ' + str(part) + ' to container')
                    devices[part] = owner
                    #devices.append(part)
        except Exception as e:
            logging.error('Exceptopn on get devices in a row ')

        return devices
            
            
    


    @staticmethod
    def parse_device_list(device_list):
        dev_container = {}
        with open(device_list, 'r') as f:
            data = f.read()
            rows = data.splitlines()
            dictionary_of_groups = Wapper.split_to_groups(rows)
            for group_name,rows in dictionary_of_groups.items():
                for row in rows:
                    if row.startswith('#') or row == '\n' or row == '' :
                        continue
                    else:
                        devs_in_row_dict = Wapper.get_devices_in_row(row)
                        for dev in devs_in_row_dict.keys():
                            # check if the device is already registered on any member, if it is registered
                            # we can skip it, if not we need to registered it as un used.
                            if (Wapper.is_device_in_list(dev_container, dev, group_name)):
                                logging.debug("skipping current device since it's already registered on someone : " + dev)
                                continue
                            dev_container[dev] = devs_in_row_dict[dev],group_name

        return dev_container
    @staticmethod
    def split_to_groups(rows):
        dictionary_of_groups = {}

        logging.info('Splitting rows per groups started')
        try:
            for _r in rows:
                m = re.search('<.*>', _r)
                if m:
                    group_name = str(m.group(0))[1:-1]
                else:
                    if group_name in dictionary_of_groups.keys():
                        _l = dictionary_of_groups[group_name]
                        _l.append(_r)
                        dictionary_of_groups[group_name] =_l
                    else:
                        _l = list()
                        _l.append(_r)
                        dictionary_of_groups[group_name] = _l

        except Exception as e:
            logging.error('Exception in split to group ' + str(e))
            exit(-1)

        logging.info('Splitting rows per groups ends')
        return  dictionary_of_groups

    @staticmethod
    def parse_email_file(filename):
        lst = []
        logging.debug("parsing email list to a list")
        with open(filename, 'r') as f:
            data = f.read()
            rows = data.splitlines()
            for row in rows:
                logging.debug("adding new email address : " + row)
                lst.append(row)
        return lst

    @staticmethod
    def is_device_in_list(dev_container, dev,group_name):
        logging.debug("verifiying if the device is in the list")
        for device in dev_container.keys():
            if device == dev:
                logging.debug("device exist in device list : " + dev)
                return True
        else:
            logging.debug("device is not exist in device list : " + dev)
            return False

    @staticmethod
    def Create_devices_objects(device_list_ip):
        #Create tempory SSH connection to be able to create device list:
        main_device = 'r-build-05'
        main_device_ip = '10.209.36.54'
        logging.debug("connecting to " + main_device+ " to create device list")
        try:
            dev = Device(main_device_ip, main_device,'linux_host' ,'root', '3tango',None,'Nobody','Nobody')
            if dev.ssh_client == None:
                logging.error('Couldnt create SSH connection for main device : ' + main_device + ' Exit script ')
                exit(-1)
        except Exception as e:
            logging.error('Exception in Creating mian device object : ' + main_device + ' ' + str(e))
        device_list = []
        try:
            for device in device_list_ip.keys():
                logging.debug(" start Creating device object for :" + device)
                owner, group_name = device_list_ip[device][0], device_list_ip[device][1]
                #identify from DHCP what type of device is it:
                logging.debug("running cmd : " + 'cat /auto/LIT/SCRIPTS/DHCPD/list | grep -i ' + device)
                cmd = 'cat /auto/LIT/SCRIPTS/DHCPD/list | grep -i ' + device
                out = dev.run_command(cmd)
                #if device has no next server it means that it was not found in DHCP
                if 'next-server' in out:
                    logging.debug("device exist in dhcp : " + device)
                    #TODO - need to check which row starts with IP
                    rows = out.split('\n')
                    for row in rows:
                        regex = '\d{1,3}\.{1}\d{1,3}\.{1}\d{1,3}\.\d{1,3}.*next-server'
                        found = Device.search_in_regex(row, regex)
                        if found and (row.split('; ')[2] == device):
                            device_name = str(row.split(';')[2]).replace(" ","")
                            device_ip = str(row.split(';')[0]).replace(" ","")
                            break
                    else:
                        logging.debug("couldn't find device name and device ip according to DHCP output for device : "  + device)
                        logging.debug("out  : " + out)
                        logging.debug("regex : " + regex)
                        logging.debug("Continue to the next device... ")
                        continue
                    if device_name in Constants.ignore_devices:
                        continue
                    elif 'apl' in row:
                        #check if this is gen2 or gen1
                        logging.debug("device identiry as appliance : " + device_name)
                        if 'gen1' in row:
                            tmp_device = Apl_Host(device_ip, device_name, 'GEN1', dev,owner,group_name)
                        elif 'gen25' in row:
                            tmp_device = Apl_Host(device_ip, device_name, 'GEN2.5', dev, owner,group_name)
                        elif 'gen2' in row:
                            tmp_device = Apl_Host(device_ip, device_name, 'GEN2', dev, owner, group_name)
                        elif 'gen3' in row:
                            tmp_device = Linux_Host(device_ip, device_name, 'GEN3', dev, owner,group_name)
                        elif 'gen4' in row:
                            tmp_device = Linux_Host(device_ip, device_name, 'GEN4', dev, owner,group_name)
                            #tmp_device = Apl_Host(device_ip, device_name, 'GEN4', dev,owner)
                        else:
                            logging.error('Couldn\'t recognize the generation of the ufm appliance ' + str(device_name))
                    elif 'sw' in row or 'gw' in row or 'olg' in row:
                        logging.debug("device identify as switch : " + device_name)
                        tmp_device = Switch(device_ip, device_name, 'switch',dev,owner,group_name)
                    else:
                        logging.debug("device identify as linux host : " + device_name)
                        tmp_device = Linux_Host(device_ip, device_name,'linux_host', dev,owner,group_name)
                    logging.debug("append deivice after creation to device list : " + device_name)
                    device_list.append(tmp_device)
                else:
                    logging.debug("device not exist in dhcp : " + device + ", device will not be added to device list")
        except Exception as e:
            logging.error('Exception in Create_devices_objects for device : ' + device)
        return device_list

            #Print the results from the container.

