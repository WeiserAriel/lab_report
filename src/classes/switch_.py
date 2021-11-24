
from .apl_host_ import Apl_Host
from .constant_ import Constants
from .device_ import Device
import logging
import time



class Switch(Device):
    def __init__(self,device_ip, device_name, device_type, linux_device,owner):
        super().__init__(device_ip,device_name,device_type,'admin', 'admin',linux_device,owner)
        self.ilo = 'n/a'
        self.ilo_works = 'n/a'
        self.ports = ['n/a', 'n/a', 'n/a', 'n/a']
        self.memory = 'n/a'
        self.ofed = 'n/a'
        self.os_version = 'n/a'
        self.dmidecode = 'n/a'
        
        #collect switch proper
        self.get_all_properties()
        logging.debug("finish building switch class for : " + device_name)






    def get_version_json(self):
        logging.debug("Getting get_version_json for switch : " + self.device_name)
        cmd = 'show version | json-print'
        # shell Object is not ready so sleeping for 3 seconds.
        time.sleep(3)
        try:
            out = super().run_command(cmd)
            super().dump_file('get_version_json', out, Constants.root_switch)
        except Exception as e:
            logging.error("Exception in get_version_json : " + str(e))
        logging.info('Done with get_verion ')

    def get_interface_ib_status(self):
        logging.debug("Sending get_interface_ib_status for switch : " + self.device_name)
        cmd = "show interfaces ib status | json-print"
        # shell Object is not ready so sleeping for 3 seconds.
        time.sleep(3)
        try:
            out = super().run_command(cmd)
            super().dump_file('get_interface_ib_status', out,Constants.root_switch)
        except Exception as e:
            logging.error("Exception in get_interface_ib_status: " + str(e))
        logging.info('Done with get interfaces ib status ')

    def get_asic_version(self):
        logging.debug("Sending get_asic_version for switch : " + self.device_name)
        cmd = 'show asic-version | json-print'
        # shell Object is not ready so sleeping for 3 seconds.
        time.sleep(3)
        try:
            out = super().run_command(cmd)
            super().dump_file('show asic-version', out,Constants.root_switch)
        except Exception as e:
            logging.error("Exception in show asic-version | json-print " + str(e))


    def get_switch_info(self):
        self.get_version_json()
        #self.get_interface_ib_status()
        self.get_asic_version()



    def get_all_properties(self):
        logging.debug("Getting all properties for switch : " + self.device_name)
        if self.shell:
            self.shell = Apl_Host.set_enable_configure_terminal(self.shell)
            self.get_os_version()
            self.get_switch_info()


    def get_all_values(self):
        #Owner,device_name, Device_type, MGMT_ip, MGMT Ping, ilo IP, ilo ping. HW address, CA Type#1, CA Type #2, CA Type#3, CA Type#4, Total Memory, OFED Version, OS Version, dmidecode
        return self.owner, self.device_name,self.device_type, self.ip, self.ip_reply, self.ilo, self.ilo_works, self.hw_address,\
               self.ports[0],self.ports[1],self.ports[2],self.ports[3], self.memory, self.ofed,\
               self.os_version, self.dmidecode

    def get_os_version(self):
        cmd = 'show version'
        #shell Object is not ready so sleeping for 3 seconds.
        import time
        time.sleep(3)
        out = super().run_command(cmd)
        regex = '(Version summary:\s*)(\S*\s*\S*)'
        if out:
            list = super().search_in_regex(out, regex)
            if list:
                self.os_version = list[0][1]
            else:
                logging.fatal('Can find regex for switch version : ' + self.device_name)
                self.os_version = 'n/a'
        else:
            logging.critical("couldn't get os version for switch : " + self.device_name)
            self.os_version = 'n/a'
