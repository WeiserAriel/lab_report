
from src.classes.constant_ import Constants

import logging
import os 
import shutil

import smtplib
import xlsxwriter
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders

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
        fieldnames = ['Owner','Group','Device Name', 'Device Type', 'MGMT IP', 'MGMT PING', 'ILO IP', 'IPO PING', 'HW ADDRESS', 'CA Type#1',
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
        logging.info('Saving the workbook under : ' + str(self.filename))
        self.save_workbook(self.filename)
        #Skipping the send email part.
        #self.send_email_to_recipient(self.recepients)


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
            self.save_workbook(full_path)
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
            #TODO - skip email sending
            pass
            #server.sendmail(email_user, recepients, text)
        server.quit()
        logging.info("Email sending is done")

    def save_workbook(self,name):
        logging.info('Saving workbook in : '  + str(Constants.root_report_lab))
        try:
            path_to_target = Constants.root_report_lab + os.sep + name
            if os.path.exists(path_to_target):
                logging.debug('File has found, removing it')
                if os.path.isdir(path_to_target):
                    shutil.rmtree(path_to_target)
                else:
                    os.remove(path_to_target)

            if not os.path.exists(Constants.root_report_lab):
                os.makedirs(path_to_target, exist_ok=True)
                os.chmod(path_to_target, 0o777)

            shutil.copy(name,path_to_target)
        except Exception as e:
            logging.error('Exception in save workbook ' + str(e))

