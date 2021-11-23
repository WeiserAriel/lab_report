
from .apl_host_ import Apl_Host
from .constant_ import Constants
from .device_ import Device
from .hca_ import HCAs
from .switch_ import Switch
from .wrapper_ import Wapper
from .xlswriter_ import XlsWriter
import logging



class Linux_Host(Device):
    def __init__(self, device_ip, device_name, device_type,linux_device,owner):
        super().__init__(device_ip,device_name,device_type,'root','3tango',linux_device,owner)
        self.ilo_ip = None
        self.ilo_works = None
        self.ports = ['n/a','n/a','n/a','n/a']
        self.memory = 'n/a'
        self.ofed = 'n/a'
        self.os_version = 'n/a'
        self.dmidecode = 'n/a'
        #start collecting information
        self.get_ilo_ip()
        self.check_ilo_works()
        if self.shell:
            self.get_all_properties()
        logging.debug("finish building linux host class for " + device_name)


    def get_all_properties(self):

        #if we don't have shell to host we can skip the function below:
        if self.shell:
            self.get_hw_address()
            self.get_ports()
            self.get_memory()
            self.get_ofed()
            self.get_os_version()
            self.get_dmidecode()
            self.lshca()
            self.getServerModelandType()

    def getModel(self):
        logging.info('Starting Get Model function for device : ' + str(self.device_name))
        try:
            cmd = r'''dmidecode | grep -A3 '^System Information' | grep Product | cut -d ':' -f 2'''
            out = super().run_command(cmd, self.shell)
            super().dump_file('product_model', out, Constants.root_servers)

        except Exception as e:
            logging.error('Exception in get model function : ' + str(e))

    def getManufacture(self):
        logging.info('Starting Get Manufacture function for device : ' + str(self.device_name))
        try:
            cmd = r'''dmidecode | grep -A3 '^System Information' | grep Manufacture | cut -d ':' -f 2'''
            out = super().run_command(cmd, self.shell)
            super().dump_file('manufacture', out, Constants.root_servers)

        except Exception as e:
            logging.error('Exception in manufacture function : ' + str(e))

    def getServerModelandType(self):
        self.getManufacture()
        self.getModel()

    def lshca(self):
        logging.info('Starting lshca function for device : ' + str(self.device_name))
        try:
            cmd = '/hpc/local/bin/lshca -m normal -j -w roce'
            out = super().run_command(cmd, self.shell)
            super().dump_file('lshca', out, Constants.root_hcas)

        except Exception as e:
            logging.error('Exception in lshca function : ' + str(e))

    def get_all_values(self):
        #Owner,Device Name,Device_type, MGMT_ip, MGMT Ping, ilo IP, ilo ping. HW address, CA Type#1, CA Type #2, CA Type#3, CA Type#4, Total Memory, OFED Version, OS Version, dmidecode
        return self.owner,self.device_name, self.device_type, self.ip, self.ip_reply, self.ilo_ip, self.ilo_works, self.hw_address,\
               self.ports[0],self.ports[1],self.ports[2],self.ports[3], self.memory, self.ofed, self.os_version, self.dmidecode
    
    def get_dmidecode(self):
        self.dmidecode = super().get_dmidecode()

    def get_os_version(self):
        logging.debug("trying to get os version for : " + self.device_name)
        cmd = 'cat /etc/*-re*'
        out = super().run_command(cmd , self.shell)
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
        if super().ping_device(self.ilo_ip):
            self.ilo_works = 'Yes'
        else:
            self.ilo_works = 'No'




    def get_ilo_ip(self):
        self.ilo_ip = super().get_device_ilo()