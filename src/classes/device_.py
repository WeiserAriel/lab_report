

import logging
import os
import re
import json
import time
import platform
import subprocess
import paramiko
from netmiko import ConnectHandler
import string
from ping3 import ping
import abc

from  src.classes.constant_ import Constants

class Device:
    global_deivce_obj = None
    counter = 0
    def __init__(self, device_ip, device_name, device_type, username, password, linux_device, owner,group_name):
        self.owner = owner
        self.group_name = group_name
        self.linux_device = linux_device
        self.ip = device_ip
        self.ip_reply = 'n/a'
        self.device_name = device_name
        self.device_type = device_type
        self.hw_address = 'n/a'
        self.ssh_client = None
        self.init_ssh(username,password)
        self.hw_address = 'n/a'
        #start collecting device properties:
        self.get_all_device_properties()
        self.save_global_obj()
        self.is_ufm_host = False
        self.is_ufm_host_is_running = False
        self.ufm_version = None
        self.master = None
        self.slave = None
        self.ufm_mode = None
        self.ufm_ha_ip_type = 'IPV4'
        self.username = username
        self.password = password


        logging.debug("finish building device class for :" + device_name)

    def parse_ufm_mode_output(self,output):

        #Relevant for GEN2/2.5/3.0 only
        if self.device_type in ['GEN2','GEN25',]:
            logging.debug(f'running find prompt for : {self.device_name}')
            if self.ssh_client.find_prompt() == '>':
                logging.debug(f'need to recreate shell since we entered \'>\' mode in : {self.device_name}')
                try:
                    self.SSHConnect(self.ip,self.username,self.password)
                except Exception as e:
                    logging.error(f'Exception in recreation of SSH for : {self.device_name}')

        logging.debug(f'found ufm in HA : {self.device_name}')
        self.ufm_mode = 'HA'
        cmds = [r'''ufm_ha_cluster status  | grep Masters''', \
                r'''ufm_ha_cluster status  | grep Slaves''']
        try:
            for cmd in cmds:
                out = self.run_command(cmd)
                if 'Master' in cmd:
                    self.master = str(out).split('[')[-1].split(']')[0].replace(' ','')
                else:
                    #slave
                    self.slave = str(out).split('[')[-1].split(']')[0].replace(' ','')
            logging.debug(f'start parsing the output of : {self.device_name}')
        except Exception as e:
            logging.error(f'Exception in parsing ufm mode output on : {self.device_name} : {str(e)}')

        self.check_ufm_ha_ipv()
        logging.debug(f'parsing ufm master and slave data finished succussfully for : {self.device_name}')
    def check_ufm_ha_ipv(self):
        logging.debug(f'checking ufm IPV4 or IPV6')
        if self.device_type == 'GEN4':
            file = f"cat /opt/ha_data/ufm-enterprise/files/ufm_ha/ha_settings | grep ha_ip_type= | cut -d= -f2''"
        else:
            file = f'cat /opt/ufm/files/ufm_ha/ha_settings | grep ha_ip_type= | cut -d= -f2'
        if self.device_name == self.master:
            logging.debug(f'current host is the UFM master which means he has the file : {str(file)} : {self.device_name}')
            self.ufm_ha_ip_type = self.run_command(f'sudo {file}')
            logging.debug(f'found ha_ip_type : {self.ufm_ha_ip_type} for : {self.device_name}')
        else:
            #ssh user@remotehost 'pwd'
            try:
                logging.debug(f'trying to run command from master to slave via ssh : {self.device_name}')
                cmd = f'ssh root@{self.master} {file}'
                out = self.run_command(cmd)
                self.ufm_ha_ip_type = str(out).replace('\n','')
            except Exception as e:
                logging.error(f'Exception in running command from slave to master : {self.device_name} : {str(e)}')
    def get_info_of_ufm_mode(self):
        logging.debug(f'retreive information of ufm mode on : {self.device_name}')
        #files =[f'/opt/ufm/ufm-enterprise/files/ufm_ha/ha_settings',f'/opt/ufm/files/ufm_ha/ha_settings']
        cmd = f'ufm_ha_cluster status'
        try:
            output = self.run_command(cmd)
            if 'command not found' in output or 'cluster is not currently running on this node' in output or 'DRBD resource is not configured' in output or output == '':
                self.ufm_mode = 'SA'
            else:
                self.parse_ufm_mode_output(output)
        except Exception as e:
            logging.error(f'Exception received on get ufm mode for : {self.device_name} : {str(e)}')
    def save_gpu_version(self, gpu_dic):
        logging.debug(f"saving gpu version into json file")
        try:
            gpu_dic["owner_name"] = self.owner
            gpu_dic["device_name"] = self.device_name
            dir = f"{Constants.root_gpu_versions}{self.device_name}"
            filename = f"{dir}{os.sep}gpu.json"
            if not os.path.exists(dir):
                os.makedirs(dir)
            with open(filename, 'w') as fp:
                json.dump(gpu_dic, fp)
        except Exception as e:
            logging.error(f"Exception in save gpu version for {self.device_name} : {str(e)}")
        logging.debug(f"finish dumpping gpu version for : {self.device_name}")
    def save_ufm_data(self):
        if self.is_ufm_host:
            logging.debug(f"saving ufm version into json file")
            try:
                dic = {}
                dic["owner_name"] = self.owner
                dic["device_name"] = self.device_name
                dic["ufm_version"] = self.ufm_version
                dic["ufm_type"] = self.ufm_ha_ip_type
                dic["ufm_master"] = self.master
                dic["ufm_slave"] = self.slave
                dic["ufm_mode"] = self.ufm_mode

                dir =f"{Constants.root_ufm_versions}{self.device_name}"
                filename = f"{dir}{os.sep}ufm_data.json"
                if not os.path.exists(dir):
                    os.makedirs(dir)
                with open(filename, 'w') as fp:
                    json.dump(dic,fp)
            except Exception as e:
                logging.error(f"Exception in save ufm version for {self.device_name} : {str(e)}")
            logging.debug(f"finish dumpping ufm version for : {self.device_name}")

    def save_global_obj(self):
        try:
            if Device.counter == 0:
                Device.global_deivce_obj = self

            Device.counter = Device.counter +1
        except Exception as e:
            logging.error('Exception in save global object ' + str(e))





    def set_enable_configure_terminal(self):
        try:
            logging.debug("running 'enable' and ' configure terminal'")
            self.ssh_client.send_command_timing('enable')
            self.ssh_client.send_command_timing('configure terminal')
            if '(config)' in self.ssh_client.find_prompt():
                logging.debug('configure terminal command successded')
            else:
                pass
        except Exception as e:
            logging.error('Exception received in set configuration terminal : ' + str(e))

    
    def get_all_device_properties(self):
        #checking ping to MGMT
        if self.ssh_client:
            if self.ping_device_pyping(self.ip):
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
        elif 'get_inventory_json' in function:
            return 'inventory.json'
        elif 'system_type' in function:
            return 'system_type.json'
        elif 'get_kernel_version' in function:
            return 'kernel_version.json'
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
                if function == 'manufacture' or function == 'product_model' or function == 'get_kernel_version':
                    try:
                        dic_ = dict()
                        dic_[function] = data
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
                if function == 'get_version_json':
                    logging.debug('Removing unnessacryy keys from version dictionay ')
                with open(filename, 'w') as outfile:
                    dictionary = {}
                    if function == 'get_inventory_json':
                        try:
                            if not 'MGMT' in j.keys():
                                logging.critical('switch has no MGMT in his json which can break the functionality. skip it. ')
                                outfile.close()
                                os.remove(filename)
                                return
                            dictionary['Device_Name'] = str(self.device_name)
                            dictionary['Part Number'] = j['CHASSIS'][0]['Part Number']
                            json.dump(dictionary, outfile)
                            return
                        except Exception as e:
                            logging.error('Exception in get inventory dump :' + str(e))
                    elif function == 'system_type':
                        try:
                            dictionary['Device_Name'] = str(self.device_name)
                            dictionary['System Type'] = j['value'][0]
                            json.dump(dictionary, outfile)
                            return
                        except Exception as e:
                            logging.error('Exception in get inventory dump :' + str(e))
                    else:
                        # some commands return list:
                        if type(j) == type(list()):
                            try:
                                for d in j:
                                    d['Device_Name'] = str(self.device_name)

                                json.dump(j, outfile)
                            except Exception as e:
                                logging.error('Exception in adding device name to dictionary ' + str(e))
                        else:
                            # could be 'show asic-version' or 'show version'
                            j['Device_Name'] = str(self.device_name)
                            if 'show asic-version' not in function:
                                j['Version summary'] = str.join(" ",str(j['Version summary']).split(' ')[0:2])
                            if 'asic' in function:
                                if not 'MGMT' in j.keys():
                                    logging.critical('switch has no MGMT in his json which can break the functionality. skip it. ')
                                    return
                            json.dump(j, outfile)
            except Exception as e:
                logging.error('Exception in dumping json to device in function: ' + str(function) + ' for device : ' + str(self.device_name) + ' ' + str(e))

        except Exception as e:
            logging.error('Exception recieive in dump file for :' + self.device_name  + ' ' + str(e) )


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
        if not self.is_tool_installed(cmd):
            logging.debug('dmidecode does not installed on : ' + self.device_name)
            return 'n/a'
        else:
            out = self.run_command(cmd)
            if 'not found' in out:
                return 'n/a'
            elif out:
                if type(out) == str:
                    return out
                else:
                    return out.splitlines()[1]
            else:
                logging.fatal("couldn't find dmidecode for : " + self.device_name)
                return 'n/a'
        
    def get_ofed_version(self):
        logging.debug("Find ofed version on : " + self.device_name)
        cmd = 'ofed_info -s'
        if not self.is_tool_installed(cmd):
            logging.debug('ofed does not exist on device : ' + self.device_name)
            return 'n/a'
        else:
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

    def is_tool_installed(self, tool_name):
        logging.debug('Checking if the tool name exist on : ' + self.device_name + ' tool name : ' + str(tool_name))
        try:
            cmd = 'which ' + tool_name
            out = self.run_command(cmd)
            if 'no' in out or 'Not' in out or out == "":
                logging.debug('tool ' + tool_name + ' is not exist on ' + self.device_name)
                return False
            else:
                logging.debug('tool ' + tool_name + ' exist on ' + self.device_name)
                return True
        except Exception as e:
            logging.error('Exception on is tool installed : ' + str(e))


    def get_ports(self):
        try:
            logging.debug("Running ibstat on : " + self.device_name)
            if not self.is_tool_installed('ibstat'):
                ports = ['n/a', 'n/a', 'n/a', 'n/a']
                return ports

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
                        ports.append(row.split(':')[1])
                        i += 1
                for _ in range(totalPorts - i):
                    ports.append('n/a')

                logging.debug("found " +str(i) + " ports on " + self.device_name)
                return ports
            else:
                logging.critical("No HCA-s install on : " + self.device_name)
                ports = ['n/a', 'n/a', 'n/a', 'n/a']
                return ports
        except Exception as e:
            logging.error(f"exception in get_ports function, device : {self.device_name} {str(e)}")



    def set_hw_address(self):
        logging.debug("search for HW address to " + self.device_name)
        device_name = self.device_name
        cmd = 'cat /auto/LIT/SCRIPTS/DHCPD/list | egrep -i ' + device_name
        out = self.run_command(cmd, run_on_global='Yes')
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
            out = self.run_command(cmd,run_on_global='Yes')
        else:
            out = self.run_command(cmd, run_on_global='Yes')
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
        if self.ping_device_pyping(ip) == True:
            try:
                logging.debug("try to connect via SSH to :" + self.device_name)
                ssh_client = self.SSHConnect(ip, username, password)
            except Exception as e:
                logging.debug("SSH failed which means no ping to host : " + self.device_name)
                self.ip_reply = 'No'
            self.ssh_client = ssh_client
            if self.ssh_client:
                self.ssh_client.fast_cli = False
            logging.debug("end init_ssh")
        else:
            logging.debug("skip ssh to : " + self.device_name + " because no ping to MGMT")



    def ping_device(self, host):

        logging.debug("'Sending ping to " + str(host))
        # Option for the number of packets as a function of
        param = '-n' if platform.system().lower() == 'windows' else '-c'

        # Building the command. Ex: "ping -c 1 google.com"
        command = ['ping', param, '1', host]

        return subprocess.call(command) == 0


    def ping_device_pyping(self, host):
        logging.debug("'Sending ping to " + str(host))
        for t in range(1,5):
            try:
                r = ping(host)
                if r:
                    logging.debug("'Sending ping to " + str(host) + ' succussded')
                    return True
                else:
                    logging.debug(f"Sending ping to {str(host)} failed for the {str(t)} time.. sleeping for 1 second.")
                    time.sleep(1)
            except Exception as e:
                logging.error('Exeception in ping : ' + str(e))

        logging.debug("Sending ping to " + str(host) + ' failed for all # ' + str(t) + " times")
        return False








    def SSHConnect(self, ip, username, passowrd):
        #Checking which type of connection needed ( Switch / UFMAPL / Linux Host
        if self.device_type in ['linux_host','virtual machine']:
            client = paramiko.SSHClient()
            logging.debug(msg="Open SSH Client to to linux host :" + str(ip) +"(" + self.device_name + ')' )
            try:
                logging.getLogger("paramiko").setLevel(logging.WARNING)
                client.set_missing_host_key_policy(policy=paramiko.AutoAddPolicy())
                client.connect(ip, port=22, username=username, password=passowrd, allow_agent=False, look_for_keys=True, banner_timeout=80)
            except Exception as e:
                logging.critical(msg="SSH Client wasn't established! Device name : " + str(self.device_name) + "Execption is :" + str(e))
                return None

            logging.info(msg="Open SSH Client to :" + str(ip) +"(" + self.device_name + ')' + " established!")
            return client
        else:
            #UFMAPL / Switch
            logging.debug(msg="Open SSH Client to to switch/ufmapl :" + str(ip))
            try:
                client = ConnectHandler(device_type='cisco_ios', host=ip, username=username,password=passowrd)

                logging.getLogger("netmiko").setLevel(logging.WARNING)
            except Exception as ex:
                logging.critical(msg="SSH Client wasn't established! Device name : " + str(self.device_name))
                return None
            logging.debug("SSH Client to to switch/ufmapl :" + str(ip) + ' Established')

            return client

    @staticmethod
    def createshell(client):
        shell =None
        for i in range(3):
            try:
                shell = client.invoke_shell()
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

    def func(self, text):

        printable = set(string.printable)
        return filter(lambda x: x in printable, text)

    def run_command(self, cmd, remove_asci='no', run_on_global=None, white_chars_removal=None,docker=None):
        logging.debug(f"Inside run commannd function for : {self.device_name}" )
        if (self.device_type == 'switch' or self.device_type == 'ufmapl' or self.device_type in ['GEN2','GEN2.5','GEN3','GEN4']  ) and run_on_global == None:

            try:
                try:
                    logging.debug('Running command for switch or ufmapl :' + str(cmd))
                    if docker:
                        logging.debug(f"changing cmd to run on docker : {docker}")
                        cmd = f"docker exec -it {docker} {cmd}"
                    output = self.ssh_client.send_command_timing(cmd)
                    logging.debug('Running command for switch or ufmapl succusseded!')
                except Exception as e:
                    logging.error(f"Exception in self.ssh_client.send_command_timing : {str(e)} for device : {self.device_name}")
                    logging.debug(f"checking if output is empty for : {str(self.device_name)}")
                if output == "":
                    logging.debug(f"Yes, output if empty")
                    #for some reason when i debug i have to use different function.
                    try:
                        logging.debug(f"retry to send command with self.ssh_client.send_command")
                        logging.debug(f'FOR DEBUGGGGGG : Type of self.ssh_client is {type(self.ssh_client)} ')
                        logging.debug(f'annotions of send_command: \n {self.ssh_client.send_command.__annotations__}')
                        output = self.ssh_client.send_command(cmd,read_timeout=30)
                        logging.debug(f"retry was finished succussfully")
                    except Exception as e:
                        logging.error(f"Exception in self.ssh_client.send_command : {str(e)} for device: {self.device_name}")
                if remove_asci == 'no':
                    return output
                else:
                    #removing asci
                    try:
                        logging.debug('Removing ASCI characters from output ')
                        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
                        result = ansi_escape.sub('', output)
                        logging.debug('Removing ASCI characters from output succussded ')
                        return result
                    except Exception as e:
                        logging.error('Exception in removing asci charecters for output of command ' + str(e))
                        return None
            except Exception as e:
                logging.error(f"Exception in running command {str(e)} , \n command was : {cmd}" )
                logging.error(f"output =\n\n{output}\n\n ")

        elif self.device_type in ['linux_host', 'virtual machine'] or run_on_global != None:
            try:
                logging.debug(f"run command - device is Linux machine or Virtual host {self.device_name}")
                if run_on_global:
                    stdin, stdout, stderr = Device.global_deivce_obj.ssh_client.exec_command(cmd)
                else:
                    stdin, stdout, stderr = self.ssh_client.exec_command(cmd)
                if stderr.read():
                    logging.critical('stderr is not empty for last command ' + str(cmd))
                    return stdout.read().decode('utf-8')
                else:
                    return stdout.read().decode('utf-8')
                logging.debug(f"run command - device is Linux machine or Virtual host {self.device_name} is done")
            except Exception as e:
                logging.error(f"Excpetion in run command for Linux host : {str(e)} , command was : {cmd}")

    @staticmethod
    def search_in_regex(output, regex):
        prog = re.compile(regex)
        result = prog.findall(output)
        return result

