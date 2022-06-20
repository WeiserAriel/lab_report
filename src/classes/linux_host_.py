import re

from src.classes.Cables_ import Cables
from src.classes.constant_ import Constants
from src.classes.device_ import Device

import logging



class Linux_Host(Device):
    def __init__(self, device_ip, device_name, device_type,linux_device,owner,group_name):
        if device_type == 'GEN4':
            super().__init__(device_ip, device_name, device_type, 'root', 'UFMcyberAI', linux_device, owner,group_name)
        elif device_type == 'GEN3':
            super().__init__(device_ip, device_name, device_type, 'root', 'UFMappliance', linux_device, owner,group_name)
        else:
            super().__init__(device_ip,device_name,device_type,'root','3tango',linux_device,owner,group_name)
        self.ilo_ip = None
        self.ilo_works = None
        self.ports = ['n/a','n/a','n/a','n/a']
        self.memory = 'n/a'
        self.ofed = 'n/a'
        self.os_version = 'n/a'
        self.dmidecode = 'n/a'
        self.kernel = 'n/a'
        #start collecting information
        self.get_ilo_ip()
        self.check_ilo_works()
        if self.ssh_client:
            self.get_all_properties()
        logging.debug("finish building linux host class for " + device_name)

    def get_kernel_version(self):
        logging.debug('Start get kernel version')
        try:
            cmd = r'''uname -r'''
            out = super().run_command(cmd)
            super().dump_file('get_kernel_version', out, Constants.root_servers)

        except Exception as e:
            logging.error('Exception in get kernel version: ' + str(e))
        logging.debug('End get kernel version')

    def get_all_properties(self):

        #if we don't have shell to host we can skip the function below:
        if self.ssh_client:
            self.get_hw_address()
            self.get_ports()
            self.get_memory()
            self.get_ofed()
            self.get_os_version()
            self.get_dmidecode()
            self.lshca()
            self.getServerModelandType()
            self.get_kernel_version()
            if self.check_if_ufm_host():
                self.Cables_obj = Cables(self.device_name,self.owner)
                self.save_ufm_version()

    def save_ufm_version(self):
        super().save_ufm_version()

    def check_if_ufm_host(self):
        try:
            proccess = ['opensm','ModelMain.pyc']
            logging.debug(f"checking if {self.device_name} has ufm running ")
            for p in proccess:
                cmd = f"ps -ef | grep {p}"
                output = self.run_command(cmd=cmd,remove_asci='yes')
                if re.findall(f"\Sopt\S.*\S{p}", output):
                    logging.debug(f"server : {self.device_name} is  running {p} ")
                else:
                    logging.debug(f"server : {self.device_name} is  not running {p}")
                    self.is_ufm_host = False
                    return False

        except Exception as e:
            logging.error('Exception in check_if_ufm_host : ' + str(e))

        logging.debug(f"server : {self.device_name} is  ufm host")
        self.is_ufm_host = True
        self.get_ufm_version()
        return  True

    def get_ufm_version(self):
        try:
            cmd = f" cat /opt/ufm/version/release "
            out = super().run_command(cmd)
            if out:
                self.ufm_version = out
                self.ufm_version = str(self.ufm_version.replace("build", '.')).replace(" ", "")
                logging.debug(f"found ufm version for {self.device_name} : {self.ufm_version}")
            else:
                logging.debug(f"didn't find ufm version for {self.device_name}")
        except Exception as e:
            logging.error(f"Exception occured in get ufm version for {self.device_name}: {str(e)}")

    def getModel(self):
        logging.info('Starting Get Model function for device : ' + str(self.device_name))
        try:
            cmd = r'''dmidecode | grep -A3 '^System Information' | grep Product | cut -d ':' -f 2'''
            out = super().run_command(cmd)
            super().dump_file('product_model', out, Constants.root_servers)

        except Exception as e:
            logging.error('Exception in get model function : ' + str(e))

    def getManufacture(self):
        logging.info('Starting Get Manufacture function for device : ' + str(self.device_name))
        try:
            cmd = r'''dmidecode | grep -A3 '^System Information' | grep Manufacture | cut -d ':' -f 2'''
            out = super().run_command(cmd)
            super().dump_file('manufacture', out, Constants.root_servers)

        except Exception as e:
            logging.error('Exception in manufacture function : ' + str(e))

    def getServerModelandType(self):
        self.getManufacture()
        self.getModel()

    def lshca(self):
        logging.info('Starting lshca function for device : ' + str(self.device_name))
        try:
            tools = ['python','/hpc/local/bin/lshca']
            flag = True
            cmd = '/hpc/local/bin/lshca -m normal -j -w roce'
            for tool in tools:
                if not self.is_tool_installed(tool):
                    flag = False
                    break
            if not flag:
                logging.debug('tool does not install on : ' +self.device_name)
            else:
                out = super().run_command(cmd)
                super().dump_file('lshca', out, Constants.root_hcas)

        except Exception as e:
            logging.error('Exception in lshca function : ' + str(e))

    def get_all_values(self):
        #Owner,Device Name,Device_type, MGMT_ip, MGMT Ping, ilo IP, ilo ping. HW address, CA Type#1, CA Type #2, CA Type#3, CA Type#4, Total Memory, OFED Version, OS Version, dmidecode
        return self.owner,self.group_name,self.device_name, self.device_type, self.ip, self.ip_reply, self.ilo_ip, self.ilo_works, self.hw_address,\
               self.ports[0],self.ports[1],self.ports[2],self.ports[3], self.memory, self.ofed, self.os_version, self.dmidecode
    
    def get_dmidecode(self):
        self.dmidecode = super().get_dmidecode()

    def get_os_version(self):
        logging.debug("trying to get os version for : " + self.device_name)
        cmd = 'cat /etc/*-re*'
        out = super().run_command(cmd)
        if out:
            rows = out.splitlines()
            for row in rows:
                if 'PRETTY_NAME=' in row:
                    os = row.split('=')[1].replace("\"",'')
                    logging.debug("os version for device : " + self.device_name + " is" + str(os))
                    self.os_version = os
                    break
            else:
                logging.critical("Couldn't find os version for " + self.device_name)

    def get_ofed(self):
        self.ofed = super().get_ofed_version()




    def get_memory(self):
        self.memory = super().find_total_memory()

    def get_ports(self):
        self.ports = super().get_ports()
        
    def get_hw_address(self):
        super().set_hw_address()

    def check_ilo_works(self):
        if super().ping_device_pyping(self.ilo_ip):
            self.ilo_works = 'Yes'
        else:
            self.ilo_works = 'No'




    def get_ilo_ip(self):
        self.ilo_ip = super().get_device_ilo()
