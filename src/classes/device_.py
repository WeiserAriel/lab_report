

import logging
import os
import re
import json
import time
import platform
import subprocess
import paramiko


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


    def set_enable_configure_terminal(self):
        time.sleep(5)
        logging.debug("running 'enable' and ' configure terminal'")
        i = 0
        commandsList = ['enable', 'configure terminal']
        expectedList = ['#', '(config)']
        for cmd, expect in zip(commandsList, expectedList):
            out = self.run_command(cmd)
            if expect in out:
                logging.info(cmd + " command run successfully")
            else:
                logging.error("can't run " + cmd + " command")
            i += 1
            time.sleep(2)

        logging.debug('returning shell after running enable and configure terminal')
    
    def get_all_device_properties(self):
        #checking ping to MGMT
        if self.shell:
            if self.ping_device(self.ip):
                self.ip_reply = 'Yes'
            else:
                self.ip_reply= 'No'
        else:
            self.ip_reply = 'No'

    def get_name_of_json(self,function):
        if 'get_version_json' in function:
            return 'version.json'
        elif 'interface_ib_status' in function:
            return'interface_ib_status.json'
        elif 'asic-version' in function:
            return 'asic_version.json'
        elif 'lshca' in function:
            return 'lshca.json'
        elif 'manufacture'in function:
            return 'manufacture.json'
        elif 'model' in function:
            return 'model.json'
        else:
            logging.error('could not get name of json')

    def dump_file(self, function, data, root_path):
        try:
            logging.debug('Trying to dump file for ' + function + 'of device name : ' + str(self.device_name))
            location = root_path + str(self.device_name).replace(' ', "") + os.sep
            filename = location + self.get_name_of_json(function)
            if not os.path.exists(location):
                # need to create a new folder
                os.makedirs(location, exist_ok=True)
            try:
                logging.debug('dump json to file: ')
                #WA
                if function == 'manufacture' or function == 'product_model':
                    value = None
                    try:
                        value = re.findall('\r\n(.*)\r\n', data)
                        if value:
                            dic_ = dict()
                            dic_[function] = value[0]
                            dic_['Device_Name'] = str(self.device_name)
                            with open(filename, 'w') as outfile:
                                json.dump(dic_, outfile)
                            logging.info('wrote ' + str(function) + ' of device : ' + str(self.device_name))
                            return
                            #exit from function
                    except Exception as e:
                            logging.error('could not find manufacture or model for ' + str(self.device_name) + ' ' + str(e))
                elif function == 'lshca':
                    s_index = str(data).index('[')
                    e_index = str(data).rindex(']')
                else:
                    s_index = str(data).index('{')
                    e_index = str(data).rindex('}')
                final_string = str(data[s_index:e_index + 1]).replace('\n', '').replace('\r', '')
                final_string = self.remove_hostname(final_string, str(self.device_name).replace(' ',''))
                j = json.loads(final_string)
                with open(filename, 'w') as outfile:
                    # some commands return list:
                    if type(j) == type(list()):

                        try:
                            for d in j:
                                d['Device_Name'] = str(self.device_name)
                                json.dump(j, outfile)
                        except Exception as e:
                            logging.error('Exception in adding device name to dictionary ' + str(e))
                    else:
                        j['Device_Name'] = str(self.device_name)
                        json.dump(j, outfile)
            except Exception as e:
                logging.error('Exception in dumping json to device : '+ str(self.device_name) + ' ' + str(e))

        except Exception as e:
            logging.error('Exception recieive in dump file for :' + self.device_name)

    def remove_hostname(self,final_string, device_name ):
        logging.debug('Checking if the hostname returned in the output')
        str = final_string
        try:
            reg = '\[root@.*]'
            result = re.findall(reg,final_string)
            if result:
                str = re.sub(reg, "", final_string)
                return str

            else:
                return str
        except Exception as e:
            logging.error('Exception in remove hostname ' +  device_name + " "+ str(e))


    def get_dmidecode(self):
        logging.debug("trying to find dmidecode for : " + self.device_name)
        cmd = 'dmidecode -s system-serial-number'
        out = self.run_command(cmd)
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
        out = self.run_command(cmd)
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
        out = self.run_command(cmd)
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
        out = self.run_command(cmd)
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
        out = self.run_command(cmd)
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
            out = self.run_command(cmd)
        else:
            out = self.run_command(cmd)
            time.sleep(3)
        if out:
            rows = out.split('\n')
            for row in rows:
                if 'next-server' in row:
                    ilo_ip = row.split(';')[0]
                    return ilo_ip

        logging.critical("Couldn't find ilo IP for " + self.device_name)
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
            logging.critical(msg="SSH Client wasn't established! Device name : " + str(self.device_name))

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
                logging.critical(" Exception number " + str(i) + " in create shell : "+ str(e))
                continue
            break

        if shell:
            return shell
        else:
            return None

    def run_command(self, cmd):

        if self.device_name == 'switch':
            pass
        elif self.device_name == 'linux_host':
            try:
                stdin, stdout, stderr = self.shell.exec_command(cmd)
                if stderr.read():
                    logging.critical('stderr is not emply ')
                else:
                    return stdout.read().decode('utf-8')
            except Exception as e:
                logging.error('Excpetion in run command for Linux host : ' + str(e))


        elif self.device_name == 'UFMAPL':
            pass
        '''
        self.shell.send(cmd + '\n')
        out = ''
        while True:
            try:
                tmp = self.shell.recv(1024)
                if not tmp:
                    break
            except Exception as e:
                break
            out += tmp.decode("utf-8")
        ansi_escape = re.compile(r'\x1B\[[0-?]*[ -/]*[@-~]')
        out = ansi_escape.sub('', out)
        return out
    '''
    @staticmethod
    def search_in_regex(output, regex):
        prog = re.compile(regex)
        result = prog.findall(output)
        return result

