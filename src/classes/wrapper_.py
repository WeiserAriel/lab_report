
from src.classes.apl_host_ import Apl_Host
from src.classes.linux_host_ import Linux_Host
from src.classes.switch_ import Switch
from src.classes.constant_ import Constants
from src.classes.device_ import Device
import glob
import re

import logging
import os
import datetime

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
    def debug_function_decorator(func):

        def inner(*args, **kwargs):
            now = datetime.datetime.now()
            logging.debug("starting the function :" + func.__name__ + " at : " + str(now))
            results = func(*args, **kwargs)

            end = datetime.datetime.now()
            logging.debug("Ending the function :" + func.__name__ + " at : " + str(end - now))
            return results

        return inner()


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
                            else:
                                logging.debug(f'adding {dev} into dev_container[dev]')
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
    def is_virutal_machine(dev, device_name):
        logging.debug(f"start check if {device_name} is virtual machine")
        try:
            try:
                logging.debug(f"checking if name of the device has only one '-' inside for : {device_name}")
                num_of_spaces = device_name.count("-")
                if num_of_spaces <= 1:
                    logging.debug(f"name contains only one space")
                    return False
                else:
                    device_name_short = str.join('-',str(device_name).split("-")[:-1])
            except Exception as e:
                logging.error(f"can't convert device name : {device_name_short}. Exception : {str(e)}")
            cmd = 'cat /auto/LIT/SCRIPTS/DHCPD/list | grep -i ' + device_name_short
            out = dev.run_command(cmd)
            logging.debug(f"grepping short name fron DHCP run succussfully ")
            out_lines = str(out).splitlines()
            counter = 0
            regex = device_name_short + r"-\d\d\d"
            matches = re.findall(regex,out)
            if not matches:
                return False

            if len(matches) > 1:
                return True
            else:
                return False
        except Exception as e:
            logging.error(f"Exception in  check if {device_name} is virtual machine : {str(e)}")
            return False

    @staticmethod
    def Create_devices_objects(device_list_ip):
        list_of_hosts =list(device_list_ip.keys())
        print(f'inside Create_devices_objects, list_of_hosts = : {len(list_of_hosts)}')
        #Create tempory SSH connection to be able to create device list:
        main_device = 'smg-ib-svr030'
        main_device_ip = '10.213.31.20'
        logging.debug("connecting to " + main_device+ " to create device list")
        does_not_exist_in_dhcp = []
        could_not_find_regex = []
        try:
            print(f'inside of try, list_of_hosts = : {len(list_of_hosts)}')
            dev = Device(main_device_ip, main_device,'linux_host' ,'root', '3tango',None,'Nobody','Nobody')
            if dev.ssh_client == None:
                logging.error('Couldnt create SSH connection for main device : ' + main_device + ' Exit script ')
                exit(-1)
        except Exception as e:
            logging.error('Exception in Creating mian device object : ' + main_device + ' ' + str(e))
        device_list = []
        #TODO
        breaks = 0
        try:
            print('inside Create_devices_objects')
            print(len(list(device_list_ip.keys())))
            print(sorted(list(device_list_ip.keys())))
            for device in device_list_ip.keys():
                logging.debug(" Inside Create_devices_objects : start Creating device object for :" + device)
                owner, group_name = device_list_ip[device][0], device_list_ip[device][1]
                #identify from DHCP what type of device is it:
                logging.debug("running cmd : " + 'cat /auto/LIT/SCRIPTS/DHCPD/list | grep -i ' + device)
                cmd = 'cat /auto/LIT/SCRIPTS/DHCPD/list | grep -i ' + device
                out = dev.run_command(cmd)
                #if device has no next server it means that it was not found in DHCP
                if 'next-server' in out:
                    logging.debug("device exist in dhcp : " + device)
                    rows = out.split('\n')
                    for row in rows:
                        regex = '\d{1,3}\.{1}\d{1,3}\.{1}\d{1,3}\.\d{1,3}.*next-server'
                        found = Device.search_in_regex(row, regex)
                        if found and (row.split('; ')[2].lower() == device.lower()):
                            device_name = str(row.split(';')[2]).replace(" ","")
                            device_ip = str(row.split(';')[0]).replace(" ","")
                            breaks = +1
                            break
                    else:
                        logging.debug("couldn't find device name and device ip according to DHCP output for device : "  + device)
                        logging.debug("out  : " + out)
                        logging.debug("regex : " + regex)
                        logging.debug("Continue to the next device... ")
                        could_not_find_regex.append(device)
                        continue
                    if device_name in Constants.ignore_devices:
                        continue
                    elif Wapper.is_exist_in_devices_list(device_list,device_name):
                        logging.debug(f'The device was exist in device_list : {device}. skipping')
                        continue
                    elif 'apl' in row:
                        if 'gen1' in row:
                            logging.debug("device identify as apl gen1 : " + device_name)
                            tmp_device = Apl_Host(device_ip, device_name, 'GEN1', dev,owner,group_name)
                        elif 'gen25' in row:
                            logging.debug("device identify as apl gen25 : " + device_name)
                            tmp_device = Apl_Host(device_ip, device_name, 'GEN2.5', dev, owner,group_name)
                        elif 'gen2' in row:
                            logging.debug("device identify as apl gen2 : " + device_name)
                            tmp_device = Apl_Host(device_ip, device_name, 'GEN2', dev, owner, group_name)
                        elif 'gen3' in row:
                            logging.debug("device identify as apl gen3 : " + device_name)
                            tmp_device = Linux_Host(device_ip, device_name, 'GEN3', dev, owner,group_name)
                        elif 'gen4' in row:
                            logging.debug("device identify as apl gen4 : " + device_name)
                            tmp_device = Linux_Host(device_ip, device_name, 'GEN4', dev, owner,group_name)
                        else:
                            logging.error('Couldn\'t recognize the generation of the ufm appliance ' + str(device_name))
                    elif 'sw' in row or 'gw' in row or 'olg' in row:
                        logging.debug("device identify as switch : " + device_name)
                        tmp_device = Switch(device_ip, device_name, 'switch',dev,owner,group_name)
                    else:
                        if Wapper.is_virutal_machine(dev,device_name):
                            logging.debug("device identify as virtual machine : " + device_name)
                            tmp_device = Linux_Host(device_ip, device_name,'virtual machine', dev,owner,group_name)
                        else:
                            logging.debug("device identify as linux_host: " + device_name)
                            tmp_device = Linux_Host(device_ip, device_name, 'linux_host', dev, owner, group_name)

                    logging.debug("append device after creation to device list : " + device)
                    device_list.append(tmp_device)
                else:
                    logging.debug("device not exist in dhcp : " + device + ", device will not be added to device list")
                    does_not_exist_in_dhcp.append(device)
        except Exception as e:
            logging.error('Exception in Create_devices_objects for device : ' + device + " " + str(e))

        print('device_list size')
        print(len(device_list))
        print(f'doesnt exist in dhcp : {str(len(does_not_exist_in_dhcp))}')
        print(f'could_not_find_regex: {str(len(could_not_find_regex))}')
        print(f'ignore list :{str(len(Constants.ignore_devices))}')
        print(f'number of breaks is : {str(breaks)}')
        return device_list

            #Print the results from the container.

    @staticmethod
    def is_exist_in_devices_list(device_list, device_name):
        logging.debug('Checking if the device was added for the device list already')
        try:
            for _d in device_list:
                if _d.device_name == device_name:
                    return True
            else:
                return False
        except Exception as e:
            logging.error('Exception in is_exist_in_devices_list function ' + str(e))
