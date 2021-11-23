
from .constant_ import Constants
from .device_ import Device
from .hca_ import HCAs
from .linux_host_ import Linux_Host
from .switch_ import Switch
from .wrapper_ import Wapper
from .xlswriter_ import XlsWriter
import logging
import time


class Apl_Host(Device):
    def __init__(self, device_ip, device_name, device_type,linux_device,owner):
        super().__init__(device_ip,device_name,device_type,'admin','admin',linux_device,owner)
        self.ilo_ip = 'n/a'
        self.ilo_works = 'n/a'
        self.ports = ['n/a','n/a','n/a','n/a','n/a']
        self.memory = 'n/a'
        self.ofed = 'n/a'
        self.os_version = 'n/a'
        self.dmidecode = 'n/a'
        #if self.ip_reply != 'n/a':
        if self.shell:
            has_shell = self.initial_apl_shell()
        # start collecting information
            self.get_all_properties(has_shell)
        logging.debug("finish building appliance class for :" + device_name)

    # start collecting information
    def get_all_properties(self, has_shell):
        self.get_ilo_ip()
        self.check_ilo_works()
        if self.shell and has_shell:
            #Commands after '_shell':
            self.get_ports()
            self.get_memory()
            self.get_ofed()
            self.get_dmidecode()
            # Some of the commands need to run after 'cli':
            self.change_to_cli()
            self.get_os_version()
            self.get_hw_address()

    def change_to_cli(self):
        logging.debug("Changing to cli mode in : " + self.device_name )
        cmd = 'cli'
        out = self.run_command(cmd, self.shell)


    def get_all_values(self):
        #Owner.Device_name , Device_type, MGMT_ip, MGMT Ping, ilo IP, ilo ping. HW address, CA Type#1, CA Type #2, CA Type#3, CA Type#4, Total Memory, OFED Version, OS Version, dmidecode
        return self.owner,self.device_name, self.device_type, self.ip, self.ip_reply, self.ilo_ip, self.ilo_works, self.hw_address,\
               self.ports[0],self.ports[1],self.ports[2],self.ports[3], self.memory, self.ofed, self.os_version, self.dmidecode
        
    def get_dmidecode(self):
        self.dmidecode = super().get_dmidecode()
        
    def get_os_version(self):
        cmd = 'show version'
        regex = '(Version summary:)(\s*)(\S*)(\s*)(\S*)(.*)'
        out = super().run_command(cmd, self.shell)
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
        if super().ping_device(self.ilo_ip):
            self.ilo_works = 'Yes'
        else:
            self.ilo_works = 'No'

    def get_ilo_ip(self):
        self.ilo_ip = super().get_device_ilo()

    @staticmethod
    def set_enable_configure_terminal(shell):
        time.sleep(5)
        logging.debug("running 'enable' and ' configure terminal'")
        i = 0
        commandsList = ['enable', 'configure terminal']
        expectedList = ['#', '(config)']
        for cmd, expect in zip(commandsList, expectedList):
            out = Device.run_command(cmd=cmd, shell=shell)
            if expect in out:
                logging.info(cmd + " command run successfully")
            else:
                logging.error("can't run " + cmd + " command")
            i += 1
            time.sleep(2)

        logging.debug('returning shell after running enable and configure terminal')
        return shell

    def initial_apl_shell(self):

        self.shell = self.set_enable_configure_terminal()
        self.get_hw_address()
        has_shell = self.confiure_appliance_license()
        return has_shell



    def confiure_appliance_license(self):
        logging.debug("start to confiure license to " + self.device_name)
        mac = self.hw_address
        cmd = '/builds/genlicense 2   RESTRICTED_CMDS "secret" -o 3 ' + mac 
        license = self.run_command(cmd,self.linux_device.shell)

        
        rows = license.splitlines()
        for row in rows:
            if '-RESTRICTED_CMDS-' in row:
                license = row
                break
        else:
            logging.error("couldn't get restricted license for : " +self.device_name)

        cmd = 'fae license install ' + license
        out = self.run_command(cmd, self.shell)
        has_shell = self.change_to_shell()
        return has_shell

    def change_to_shell(self):
        logging.debug("Change to shell mode in : " + self.device_name)
        cmd = '_shell'
        out = self.run_command(cmd, self.shell)
        time.sleep(3)
        if 'admin' in out:
            logging.debug("change to shell mode successfully in : " + self.device_name)
            return True
        else:
            logging.fatal(" couldn't change to shell mode in : " + self.device_name)
            return False


    def get_hw_address(self):
        #No need to call again configure terminal
        #self.set_enable_configure_terminal()
        interfaces = ['eth0','mgmt0']
        for interface in interfaces:
            cmd = 'show interfaces ' +interface +' brief'
            regex = '(HW address:)\s*(.{2}:.{2}:.{2}:.{2}:.{2}:.{2})'
            out = self.run_command(cmd, shell=self.shell)
            time.sleep(6)
            if not 'Unrecognized' in out:
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
