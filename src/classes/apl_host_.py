import re

from src.classes.device_ import Device
from src.classes.Cables_ import Cables

import logging
import time



class Apl_Host(Device):
    def __init__(self, device_ip, device_name, device_type,linux_device,owner,group_name):
        super().__init__(device_ip,device_name,device_type,'admin','admin',linux_device,owner,group_name)
        self.ilo_ip = 'n/a'
        self.ilo_works = 'n/a'
        self.ports = ['n/a','n/a','n/a','n/a','n/a']
        self.memory = 'n/a'
        self.ofed = 'n/a'
        self.os_version = 'n/a'
        self.dmidecode = 'n/a'
        #if self.ip_reply != 'n/a':
        if self.ssh_client:
            has_shell = self.initial_apl_shell()
        # start collecting information
            self.get_all_properties(has_shell)
        logging.debug("finish building appliance class for :" + device_name)

    # start collecting information

    def save_ufm_version(self):
        super().save_ufm_version()

    def get_all_properties(self, has_shell):
        self.get_ilo_ip()
        self.check_ilo_works()
        if self.ssh_client and has_shell:
            #Commands after '_shell':
            self.get_ports()
            self.get_memory()
            self.get_ofed()
            self.get_dmidecode()

            # Some of the commands need to run after 'cli':
            self.change_to_cli()
            self.set_enable_configure_terminal()
            self.get_os_version()
            self.get_hw_address()
            if self.check_if_ufm_host():
                self.Cables = Cables(self.device_name)
                self.save_ufm_version()

    def get_ufm_version(self):
        if self.is_ufm_host:
            logging.debug(f"get ufm version for {self.device_name}")
            cmd = "show version"
            output = self.run_command('cmd', remove_asci='yes')
            try:
                res = re.match('UFM\s*Running', output)
                if res:
                    self.ufm_version = res
                    return True
                else:
                    return False
            except Exception as e:
                logging.error(f"Exeception occured in get version for {self.device_name}: {str(e)}")

    def check_if_ufm_host(self):
        try:
            logging.debug(f"checking if ufmapl is running on server {self.device_name}")
            output = self.run_command('show ufm status',remove_asci='yes')
            if output:
                res = re.match('UFM\s*Running',output)
            else:
                logging.error(f"the output returns as None in : {__name__}")
            if res:
                self.is_ufm_host = True
                logging.debug(f"ufm is running on server {self.device_name}")
                self.ufm_version = self.get_ufm_version()
                return  True
            else:
                self.is_ufm_host = False
                logging.debug(f"ufm isn't running on server {self.device_name}")
                return  False

        except Exception as e:
            logging.error(f"Exception in check_if_ufm_host on ufmapl {self.device_name}:  {str(e)}")

        logging.debug(f"server : {self.device_name} is  ufm host")
        self.is_ufm_host = True
        self.ufm_version = self.get_ufm_version()

    def change_to_cli(self):
        logging.debug("Changing to cli mode in : " + self.device_name )
        cmd = 'cli'
        out = self.run_command(cmd)


    def get_all_values(self):
        #Owner.Device_name , Device_type, MGMT_ip, MGMT Ping, ilo IP, ilo ping. HW address, CA Type#1, CA Type #2, CA Type#3, CA Type#4, Total Memory, OFED Version, OS Version, dmidecode
        return self.owner,self.group_name,self.device_name, self.device_type, self.ip, self.ip_reply, self.ilo_ip, self.ilo_works, self.hw_address,\
               self.ports[0],self.ports[1],self.ports[2],self.ports[3], self.memory, self.ofed, self.os_version, self.dmidecode
        
    def get_dmidecode(self):
        self.dmidecode = super().get_dmidecode()
        
    def get_os_version(self):
        logging.debug('running get os version for : ' + str(self.device_name))
        cmd = 'show version'
        regex = '(Version summary:)(\s*)(\S*)(\s*)(\S*)(.*)'
        out = super().run_command(cmd)
        if out:
            list = super().search_in_regex(out, regex)
            self.os_version = list[0][4]
        else:
            logging.critical("Couldn't retrived apl version for : " + super().device_name)
            self.os_version = 'n/a'


    def get_ofed(self):
        self.ofed = super().get_ofed_version()

    def get_memory(self):
        self.memory = super().find_total_memory()

    def get_ports(self):
        self.ports  = super().get_ports()

    def get_hw_address(self):
        super().set_hw_address()

    def check_ilo_works(self):
        if super().ping_device_pyping(self.ilo_ip):
            self.ilo_works = 'Yes'
        else:
            self.ilo_works = 'No'

    def get_ilo_ip(self):
        self.ilo_ip = super().get_device_ilo()


    def initial_apl_shell(self):
        self.set_enable_configure_terminal()
        self.get_hw_address()
        has_shell = self.confiure_appliance_license()
        return has_shell



    def confiure_appliance_license(self):
        logging.debug("start to confiure license to " + self.device_name)
        mac = self.hw_address
        cmd = '/builds2/genlicense 2   RESTRICTED_CMDS "secret" -o 3 ' + mac
        license = self.run_command(cmd,run_on_global='Yes')

        
        rows = license.splitlines()
        for row in rows:
            if '-RESTRICTED_CMDS-' in row:
                license = row
                break
        else:
            logging.error("couldn't get restricted license for : " +self.device_name)

        cmd = 'fae license install ' + license
        out = self.run_command(cmd)
        has_shell = self.change_to_shell()
        return has_shell

    def change_to_shell(self):
        logging.debug("Change to shell mode in : " + self.device_name)
        cmd = '_shell'
        out = self.run_command(cmd)
        if 'admin' in out:
            logging.debug("change to shell mode successfully in : " + self.device_name)
            return True
        else:
            logging.fatal(" couldn't change to shell mode in : " + self.device_name)
            return False


    def get_hw_address(self):
        try:
            if '(config)' not in self.ssh_client.find_prompt():
                logging.debug('Running configure terminal for ' + self.device_name)
                self.set_enable_configure_terminal()
                logging.debug('Running configure terminal is done : ' +self.device_name)

            interfaces = ['eth0','mgmt0']
            for interface in interfaces:
                cmd = 'show interfaces ' +interface +' brief'
                logging.debug('running command on : ' + self.device_name + ' cmd = ' + cmd )
                regex = '(HW address.*:)\s*(.{2}:.{2}:.{2}:.{2}:.{2}:.{2})'
                out = self.run_command(cmd)
                if not 'Unrecognized' in out:
                    logging.debug(' get HW address seccussded with : ' + 'cmd=' + cmd)
                    break
            else:
                logging.error("Couldn't find HW address for : " + self.device_name)
                self.hw_address = 'n/a'

            hw_list = Device.search_in_regex(out, regex)
            if hw_list:
                self.hw_address = hw_list[0][1]
            else:
                logging.fatal("Couldn't find HW address in regex to : " + self.device_name)
                self.hw_address = 'n/a'
        except Exception as e:
            logging.error('Exception in get_hw_address ' + str(e))
