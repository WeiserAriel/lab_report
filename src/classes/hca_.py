

import logging
import json



class HCAs():
    def __init__(self):
        logging.info('Start getting all HCAs')
        self.get_all_properties()
        logging.info('Finished getting all HCAs info')

    def get_all_properties(self):
        string = """
                    [
                {
                    "Desc": "Mellanox Technologies MT28800 Family [ConnectX-5 Ex]",
                    "Dev": "#1",
                    "FW": "16.30.1004",
                    "PN": "MCX556A-EDAT  rev. A3",
                    "PSID": "MT_0000000009",
                    "SN": "MT1721X04408",
                    "Tempr": "60",
                    "bdf_devices": [
                        {
                            "Bond": "=N/A=",
                            "BondMiiStat": "",
                            "BondState": "",
                            "CblLng": "",
                            "CblPN": "",
                            "CblSN": "",
                            "HCA_Type": "MT4121",
                            "IbNetPref": "fe80000000000000",
                            "IpStat": "down",
                            "Link": "IB",
                            "LnkCapWidth": "x16 G4",
                            "LnkStaWidth": "x16",
                            "LnkStat": "down",
                            "MST_device": "",
                            "Net": "ib0",
                            "Numa": "-1",
                            "PCI_addr": "0000:10:00.0",
                            "PGuid": "ec0d9a03002fb4d2",
                            "PLid": "65535",
                            "Parent_addr": "-",
                            "PhyAnalisys": "",
                            "PhyLinkStat": "",
                            "PhyLnkSpd": "",
                            "Port": "1",
                            "RDMA": "mlx5_0",
                            "RX_bps": "N/A",
                            "Rate": "10",
                            "RoCEstat": "N/A",
                            "SMGuid": "",
                            "SRIOV": "PF  ",
                            "SwDescription": "",
                            "TX_bps": "N/A",
                            "VrtHCA": "Phys"
                        },
                        {
                            "Bond": "=N/A=",
                            "BondMiiStat": "",
                            "BondState": "",
                            "CblLng": "",
                            "CblPN": "",
                            "CblSN": "",
                            "HCA_Type": "MT4121",
                            "IbNetPref": "fe80000000000000",
                            "IpStat": "up_ip46",
                            "Link": "IB",
                            "LnkCapWidth": "x16 G4",
                            "LnkStaWidth": "x16",
                            "LnkStat": "actv",
                            "MST_device": "",
                            "Net": "ib1",
                            "Numa": "-1",
                            "PCI_addr": "0000:10:00.1",
                            "PGuid": "ec0d9a03002fb4d3",
                            "PLid": "3",
                            "Parent_addr": "-",
                            "PhyAnalisys": "",
                            "PhyLinkStat": "",
                            "PhyLnkSpd": "",
                            "Port": "1",
                            "RDMA": "mlx5_1",
                            "RX_bps": "N/A",
                            "Rate": "100",
                            "RoCEstat": "N/A",
                            "SMGuid": "",
                            "SRIOV": "PF  ",
                            "SwDescription": "",
                            "TX_bps": "N/A",
                            "VrtHCA": "Phys"
                        }
                    ]
                }
            ]
            """
        try:
            logging.debug('Tries to load output into json file')
            j = json.loads(string)
            j[0]['Server_name'] = 'r-smg-ib01'
            with open('r-smg-ib01.json', 'w') as f:
                json.dump(j, f)

            #print(string)
        except Exception as e:
            logging.error('Exception : got exception in loading the json file ' + str(e))
            print(e)
