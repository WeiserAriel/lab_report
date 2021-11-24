
from .apl_host_ import Apl_Host

from .device_ import Device

from .linux_host_ import Linux_Host
from .switch_ import Switch

import logging

class Wapper():

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

        return devices
            
            
    


    @staticmethod
    def parse_device_list(device_list):
        dev_container = {}
        with open(device_list, 'r') as f:
            data = f.read()
            rows = data.splitlines()
            for row in rows:
                if row.startswith('#') or row == '\n' or row == '' :
                    continue
                else:
                    devs_in_row_dict = Wapper.get_devices_in_row(row)
                    for dev in devs_in_row_dict.keys():
                        # check if the device is already registered on any member, if it is registered
                        # we can skip it, if not we need to registered it as un used.
                        if (Wapper.is_device_in_list(dev_container, dev)):
                            logging.debug("skipping current device since it's already registered on someone : " + dev)
                            continue
                        dev_container[dev] = devs_in_row_dict[dev]

        return dev_container
       
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
    def is_device_in_list(dev_container, dev):
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
        logging.debug("connecting to r-ufm34 to create device list")
        dev = Device('10.209.36.92','r-ufm34','linux_host' ,'root', '3tango',None,'Nobody')
        device_list = []

        for device in device_list_ip.keys():
            logging.debug(" start Creating device object for :" + device)
            owner = device_list_ip[device]
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
                        device_name = row.split(';')[2]
                        device_ip = row.split(';')[0]
                        break
                else:
                    logging.debug("couldn't find device name and device ip according to DHCP output for device : "  + device)
                    logging.debug("out  : " + out)
                    logging.debug("regex : " + regex)
                    logging.debug("Continue to the next device... ")
                    continue
            
                if 'apl' in row:
                    #check if this is gen2 or gen1
                    logging.debug("device identiry as appliance : " + device_name)
                    if 'gen1' in row:
                        tmp_device = Apl_Host(device_ip, device_name, 'GEN1', dev,owner)
                    elif 'gen2.5' in row:
                        tmp_device = Apl_Host(device_ip, device_name, 'GEN2.5', dev, owner)
                    elif 'gen2' in row:
                        tmp_device = Apl_Host(device_ip, device_name, 'GEN2', dev, owner)
                    elif 'gen3' in row:
                        tmp_device = Apl_Host(device_ip, device_name, 'GEN3', dev,owner)
                    elif 'gen4' in row:
                        tmp_device = Apl_Host(device_ip, device_name, 'GEN4', dev,owner)
                    else:
                        logging.error('Couldn\'t recognize the generation of the ufm appliance ' + str(device_name))
                elif 'sw' in row:
                    logging.debug("device identify as switch : " + device_name)
                    tmp_device = Switch(device_ip, device_name, 'switch',dev,owner)
                else:
                    logging.debug("device identify as linux host : " + device_name)
                    tmp_device = Linux_Host(device_ip, device_name,'linux_host', dev,owner)
                logging.debug("append deivice after creation to device list : " + device_name)
                device_list.append(tmp_device)
            else:
                logging.debug("device not exist in dhcp : " + device + ", device will not be added to device list")
        return device_list

            #Print the results from the container.

