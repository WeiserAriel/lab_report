import argparse
import logging
import warnings
with warnings.catch_warnings():
    import paramiko
    warnings.filterwarnings(action='ignore', module='.*paramiko.*')

import os
import sys
import re
import platform    # For getting the operating system name
import subprocess  # For executing a shell command
import time
from datetime import date
import xlsxwriter
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders

import csv
#from pyping.core import *
#import pyping

class Device:
    def __init__(self, device_ip, device_name, device_type, username, password, linux_device, owner):
        self.owner = owner
        self.linux_device = linux_device
        self.ip = device_ip
        self.ip_reply = 'n/a'
        self.device_name = device_name
        self.device_type = device_type
        self.hw_address = 'n/a'
        self.shell = None
        self.init_ssh(username,password)
        self.hw_address = 'n/a'
        #start collecting device properties:
        self.get_all_device_properties()
        logging.debug("finish building device class for :" + device_name)
    
    def get_all_device_properties(self):
        #checking ping to MGMT
        if self.shell:
            if self.ping_device(self.ip):
                self.ip_reply = 'Yes'
            else:
                self.ip_reply= 'No'
        else:
            self.ip_reply = 'No'
        
    
    def get_dmidecode(self):
        logging.debug("trying to find dmidecode for : " + self.device_name)
        cmd = 'dmidecode -s system-serial-number'
        out = self.run_command(cmd, self.shell)
        time.sleep(6)
        if 'not found' in out:
            return 'n/a'
        elif out:
            return out.splitlines()[1]
        else:
            logging.fatal("couldn't find dmidecode for : " + self.device_name)
            return 'n/a'
        
    def get_ofed_version(self):
        logging.debug("Find ofed version on : " + self.device_name)
        cmd = 'ofed_info -s'
        out = self.run_command(cmd, self.shell)
        regex = '(MLNX_OFED_LINUX-)(.*)'
        if out and 'command not found' not in out:
            ofed = self.search_in_regex(out, regex)
            if ofed:
                return str(ofed[0][1]).replace('\r','').replace(' ','')
            else:
                return 'n/a'
        else:
            if 'command not found' in out:
                logging.debug("OFED is not installed on :" + self.device_name)
                ofed = 'Not Installed'
            else:
                logging.critical("couldn't find ofed version on " + self.device_name)
                ofed = 'n/a'
        return ofed

    def find_total_memory(self):
        logging.debug("Find Total Memory on : " + self.device_name)
        cmd = 'cat /proc/meminfo | grep MemTotal'
        out = self.run_command(cmd, self.shell)
        regex = '(\s*)(\d*)(\s*)(kB)'
        if out:
            memory = self.search_in_regex(out,regex)
            if memory:
                return memory[0][1]
            else:
                return 'n/a'
        else:
            logging.critical("couldn't find memory on " + self.device_name)
            memory = 'n/a'
            return memory

    def get_ports(self):
        logging.debug("Running ibstat on : " + self.device_name)
        cmd = 'ibstat | grep \'CA type\''
        out = self.run_command(cmd, self.shell)
        totalPorts = 4
        i = 0
        ports = []
        flag = False
        if out:
            list_rows = out.splitlines()
            #count number of ports:
            for row in list_rows:
                if 'CA type' in row:
                    if row == list_rows[0]:
                        continue
                    ports.append(row.split(':')[1])
                    i += 1
            for _ in range(totalPorts - i):
                ports.append('n/a')

            logging.debug("found " +str(i) + "ports on " + self.device_name)
            return ports
        else:
            logging.critical("No HCA-s install on : " + self.device_name)
            ports = ['n/a', 'n/a', 'n/a', 'n/a']
            return ports



    def set_hw_address(self):
        logging.debug("search for HW address to " + self.device_name)
        device_name = self.device_name
        cmd = 'cat /auto/LIT/SCRIPTS/DHCPD/list | egrep -i ' + device_name
        out = self.run_command(cmd, self.shell)
        time.sleep(7)
        regex = '(.{2}:.{2}:.{2}:.{2}:.{2}:.{2})'
        if out:
            rows = out.split('\n')
            for row in rows:
                match_list = self.search_in_regex(row,regex)
                if len(match_list) > 0:
                    self.hw_address = row.split(';')[1]
                    break
        else:
            logging.fatal('HW address not apear in DHCP :' + device_name)
            self.hw_address = 'n/a'



    def get_device_ilo(self):
        cmd = 'cat /auto/LIT/SCRIPTS/DHCPD/list | grep -i ' + self.device_name + '-ilo'
        if self.linux_device is not None or self.ip_reply != 'Yes':
            out = self.run_command(cmd,self.linux_device.shell)
        else:
            out = self.run_command(cmd, self.shell)
            time.sleep(3)
        if out:
            rows = out.split('\n')
            for row in rows:
                if 'next-server' in row:
                    ilo_ip = row.split(';')[0]
                    return ilo_ip

        logging.error("Couldn't find ilo IP for " + self.device_name)
        return 'n/a'


    def init_ssh(self, username , password):
        logging.debug("start init_ssh ")
        ip = self.ip
        #check if i have a ping before starting ssh session:
        if self.ping_device(ip) == True:
            try:
                logging.debug("try to connect via SSH to :" + self.device_name)
                ssh = self.SSHConnect(ip, username, password)
            except Exception as e:
                logging.debug("SSH failed which means no ping to host : " + self.device_name)
                self.ip_reply = 'No'
            self.shell = self.createshell(ssh)
            logging.debug("end init_ssh")
        else:
            logging.debug("skip ssh to : " + self.device_name + " because no ping to MGMT")



    def ping_device(self, host):

        logging.debug("Sending ping to " + str(host))
        # Option for the number of packets as a function of
        param = '-n' if platform.system().lower() == 'windows' else '-c'

        # Building the command. Ex: "ping -c 1 google.com"
        command = ['ping', param, '1', host]

        return subprocess.call(command) == 0



    def SSHConnect(self, ip, username, passowrd):
        ssh = paramiko.SSHClient()
        logging.debug(msg="Open SSH Client to :" + str(ip))
        try:
            ssh.set_missing_host_key_policy(policy=paramiko.AutoAddPolicy())
            ssh.connect(ip, port=22, username=username, password=passowrd, allow_agent=False, look_for_keys=True)
        except Exception as ex:
            logging.error(msg="SSH Client wasn't established!")

        logging.info(msg="Open SSH Client to :" + str(ip) + " established!")
        return ssh

    @staticmethod
    def createshell(ssh):
        shell =None
        for i in range(3):
            try:
                shell = ssh.invoke_shell()
                shell.settimeout(10)
                shell.recv(1024)
                # time.sleep(10)
            except Exception as e:
                logging.error(" Exception number " + str(i) + "in create shell : " + str(e))
                continue
            break

        if shell:
            return shell
        else:
            return None



    @staticmethod
    def run_command(cmd,shell):
        '''

          :param shell:
          :param cmd: cmd command like ' show version'
          :param expect: string to look for like '
          :return: 0 if the expected string was found in output.
          '''
        # sleeping for 3 seconds to the command will be executed after shell prompt is printed.
        shell.send(cmd + '\n')
        out = ''
        while True:
            try:
                tmp = shell.recv(1024)
                if not tmp:
                    break
            except Exception as e:
                break
            out += tmp.decode("utf-8")
        ansi_escape = re.compile(r'\x1B\[[0-?]*[ -/]*[@-~]')
        out = ansi_escape.sub('', out)
        return out

    @staticmethod
    def search_in_regex(output, regex):
        prog = re.compile(regex)
        result = prog.findall(output)
        return result



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

    def get_all_properties(self):
        logging.debug("Getting all properties for switch : " + self.device_name)
        if self.shell:
            self.get_os_version()


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
        out = super().run_command(cmd, self.shell)
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
            self.os_version = out[4]
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

    def set_enable_configure_terminal(self):
        time.sleep(5)
        logging.debug("running 'enable' and ' configure terminal'")
        i = 0
        commandsList = ['enable', 'configure terminal']
        expectedList = ['#', '(config)']
        for cmd, expect in zip(commandsList, expectedList):
            out = super().run_command(cmd=cmd, shell=self.shell)
            if expect in out:
                logging.info(cmd + " command run successfully")
            else:
                logging.error("can't run " + cmd + " command")
            i += 1
            time.sleep(2)

    def initial_apl_shell(self):

        self.set_enable_configure_terminal()
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
        self.set_enable_configure_terminal()
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
            devs = split_range(part)
            for dev in devs:
                devices[dev] = owner
                #devices.append(dev)
        else:
            logging.debug('adding ' + str(part) + ' to container')
            devices[part] = owner
            #devices.append(part)

    return devices
            
            
    



def parse_device_list(device_list):
    
    dev_container = {}
    with open(device_list, 'r') as f:
        data = f.read()
        rows = data.splitlines()
        for row in rows:
            if row.startswith('#') or row == '\n' or row == '' :
                continue
            else:
                devs_in_row_dict = get_devices_in_row(row)
                for dev in devs_in_row_dict.keys():
                    dev_container[dev] = devs_in_row_dict[dev]

    return dev_container
                
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


def Create_devices_objects(device_list_ip):
    #Create tempory SSH connection to be able to create device list:
    logging.debug("connecting to r-ufm34 to create device list")
    dev = Device('10.209.36.92','r-ufm34','Linux' ,'root', '3tango',None,'Nobody')
    device_list = []

    for device in device_list_ip.keys():
        logging.debug(" start Creating device object for :" + device)
        owner = device_list_ip[device]
        #identify from DHCP what type of device is it:
        logging.debug("running cmd : " + 'cat /auto/LIT/SCRIPTS/DHCPD/list | grep -i ' + device)
        cmd = 'cat /auto/LIT/SCRIPTS/DHCPD/list | grep -i ' + device
        out = dev.run_command(cmd,dev.shell)
        #if device has no next server it means that it was not found in DHCP
        if 'next-server' in out:
            logging.debug("device exist in dhcp : " + device)
            #TODO - need to check which row starts with IP
            rows = out.split('\n')
            for row in rows:
                regex = '\d{1,3}\.{1}\d{1,3}\.{1}\d{1,3}\.\d{1,3}.*next-server'
                found = Device.search_in_regex(row, regex)
                if found:
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

                else:
                    tmp_device = Apl_Host(device_ip, device_name, 'GEN2', dev,owner)
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


class XlsWriter():
    def __init__(self, devices_obj, recepients):
        self.devices_objects = devices_obj
        self.recepients = recepients
        self.create_xls()
        self.filename =None
        


    def create_xls(self):
        # Start from the first cell. Rows and columns are zero indexed.
        logging.info("Create the xls file with all the Data")
        row = 0
        col = 0
        
        self.filename = 'Lab_report.xlsx'
        if os.path.exists(self.filename):
            os.remove(self.filename)

        # Create a workbook and add a worksheet.
        workbook = xlsxwriter.Workbook(self.filename)
        worksheet = workbook.add_worksheet()
        fieldnames = ['Owner','Device Name', 'Device Type', 'MGMT IP', 'MGMT PING', 'ILO IP', 'IPO PING', 'HW ADDRESS', 'CA Type#1',
                      'CA Type#2', 'CA Type#3', 'CA Type #4', 'Total Memory', 'OFED Version','OS Version', 'dmidecode']
        logging.debug("adding fildnames into xls file")
        for field in fieldnames:
            worksheet.write(row, col, field)
            col = col +1

        row = row + 1

        for device in self.devices_objects:
            logging.debug("Adding data to xls file of device : " + device.device_name)
            attributes_tup_device = device.get_all_values()
            logging.debug("printing all values of device: " +device.device_name )
            col = 0
            for attribute in attributes_tup_device:
                worksheet.write(row, col, attribute)
                col = col +1
            row = row +1
            logging.debug("finish writing all values to xls file of device: " + device.device_name)

        #adding autofilter
        logging.debug("adding autofiler")
        #trying to do autofit for columns
        logging.debug("trying to add column auto fit")

        worksheet.autofilter(0,0,int(len(self.devices_objects)+1),int(len(fieldnames) - 1))
        logging.debug("closing workbook")
        workbook.close()
        self.send_email_to_recipient(self.recepients)


    def send_email_to_recipient(self, recepients):
        logging.debug("Start sending email with xls file")
        email_user = 'memory.tester1234@gmail.com'
        email_password = '2wsx@WSX'
        
        from datetime import date
        today = date.today()
        date = today.strftime("%d/%m/%Y")
        subject = 'Lab Report for QA_SMG_IB team for ' + date

        #changing list to string comma seperated.
        rec_str = ''
        for recipient in recepients:
            rec_str = rec_str + recipient +','
        rec_str = rec_str[:-1]

        msg = MIMEMultipart()
        msg['From'] = email_user
        msg['To'] = rec_str
        msg['Subject'] = subject

        body = 'Hi there, attahced is the lab report xls file for qa_smg_ib '
        msg.attach(MIMEText(body, 'plain'))
         
        logging.info("Sending result for recepients")
        try:
            full_path = self.filename 
            attachment = open(full_path, 'rb')

            part = MIMEBase('application', 'octet-stream')
            part.set_payload((attachment).read())
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', "attachment; filename= " + self.filename)
            msg.attach(part)
            text = msg.as_string()
        except Exception as e:
            print("exception in sending graphs via email\n" + str(e))
        logging.info("All graphs were sent to recepients successfully")

        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(email_user, email_password)
        if full_path:
            server.sendmail(email_user, recepients, text)
        server.quit()
        logging.info("Email sending is done")




def main():
    parser = argparse.ArgumentParser(description='This is tool generate report for all lab devices')
    parser.add_argument('--device_list', dest='device_list', help='path to device list file', required=True)
    parser.add_argument('--email', dest='email', help='email list written in text file', required=True)
    parser.add_argument('--debug', dest='debug', action='store_true', help='change to debug mode')

    args = parser.parse_args()

    if args.debug:
        level = logging.DEBUG
    else:
        level = logging.INFO
    log_file = os.path.dirname(os.path.abspath(__file__)) + os.sep + 'lab_report.log'
    logging.basicConfig(filename=log_file,
                        level=level,
                        format='%(asctime)s %(levelname)-8s %(message)s',
                        datefmt='%m-%d %H:%M',
                        filemode='w')

    logging.info("lab report Script Start...")
    email_list = parse_email_file(args.email)
    device_list_ip = parse_device_list(args.device_list)
    devices_obj = Create_devices_objects(device_list_ip)
    xls = XlsWriter(devices_obj,email_list)


    b = 1


if __name__ == '__main__':
    main()


