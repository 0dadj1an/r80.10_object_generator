"""
This code is for Check Point R80.10 API. it loads data from csv and adding those to mgmt server
@author: ivohrbacek@gmail.com / ivo.hrbacek@ixperta.com
"""

import getpass
import urllib3
import csv
import pprint
import json
import os, time, datetime, sys, shutil
import requests
import configparser
import sys
import argparse
import logging
from datetime import datetime
import os



urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


#############################

class CSV_Importer_to_List(object):


    """
    Import data from csv to lists
    """


    def __init__(self, file_name):
        self.dic_list = []
        try:
            self.reader = csv.DictReader(open(file_name, 'r'))
            for line in self.reader:
                self.dic_list.append(line)

        except Exception as e:
            DoLogging().do_logging('CSV_Importer_to_List()__init__ - csv impoit fail: {}'.format(e))
            sys.exit(1)



    def get_csv_list(self):
        return self.dic_list



##############################################


class GetHostsNetworks():
    
    """
    class for geting all hosts and their IPs
    methods:
    get_all_hosts() - get all hosts from mgmt
    get_all_networks() - get all networks from mgmt


    """

    def __init__(self, connector:object):

        """
        constructor has just instance of connector and default json payload
        """

        self.connector = connector
        self.offset = 0
        self.counter_hosts=0
        self.counter_networks=0
        self.payload_rules ={
        "limit" : 500,
        "offset" : self.offset,
        "details-level":'full'
        
    }


    def get_all_hosts(self) -> list:

        """
        get all hosts

        """
        result_hosts = []
        

        hosts = self.connector.send_cmd('show-hosts', self.payload_rules) 
        for item in hosts['objects']: # add only objects, no other data
            self.counter_hosts+=1
            result_hosts.append({'name':item['name'], 'ip':item['ipv4-address']})

        total = hosts['total'] 
        while hosts['to'] != total:
            offset = self.offset
            offset += 500
            self.payload_rules ={
                "limit" : 500,
                "offset" : offset,
                "details-level":'full'
            }
            hosts = self.connector.send_cmd('show-hosts', self.payload_rules)
            for item in hosts['objects']:
                self.counter_hosts+=1
                result_hosts.append({'name':item['name'], 'ip':item['ipv4-address']})
                

        return result_hosts
    
    
    
    def get_all_networks(self) -> list:
    
        """
        get all networks

        """
        result_networks = []
        

        networks = self.connector.send_cmd('show-networks', self.payload_rules) # whole rulebase for particular layer
        for item in networks['objects']: # add only objects, no other data
            self.counter+=1
            result_networks.append({'name':item['name'], 'ip':item['ipv4-address']})

            

        total = networks['total'] # check total data : 'from': 7501, 'to': 7886, 'total': 7886}
        while networks['to'] != total: # if there are many rules, do cycle with offset +100 and hangle all data 
            offset = self.offset
            offset += 500
            self.payload_rules ={
                "limit" : 500,
                "offset" : offset,
                "details-level":'full'
            }
            networks = self.connector.send_cmd('show-hosts', self.payload_rules) # add result to existing dict
            for item in networks['objects']:
                self.counter+=1
                result_networks.append({'name':item['name'], 'ip':item['ipv4-address']})



        return result_networks


    def get_counter_hosts(self):
        return self.counter_hosts
    
    
    def get_counter_networks(self):
        return self.counter_networks
        




###############################################



class DoLogging():
    
    """
    Logging class, to have some possibility debug code in the future

    """

    def __init__(self):

        """
        Constructor does not do anything
        """
        
        self.file_name="logcp.elg"
        self.start_time=str(datetime.now())
        


    def do_logging(self, msg:str):
        

        """
        Log appropriate message into log file
        
        """
        
        #if needed change to DEBUG for more data
        
        logging.basicConfig(filename=self.file_name, level=logging.INFO)
        msgq = 'TIME:{}:{}'.format(str(datetime.now()),msg)
        logging.info(msgq)




###############################################

class Connector():
    
    """
    
    Connector class is main class handling connectivity to CP API
    Login is done in constructor once instance of Connector is created
    methods:
            task_method() - help method for publish status check
            publish() - method for changes publishing
            send_cmd() - makes API call based on functionality (viz. API reference)
            logout() - logout form API
            discard() - discard changes
           
    """

    # do not care about ssl cert validation for now   
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


    @classmethod
    def task_method(cls, sid:str, url:str, task:str) -> dict:

        """
        this is help method which is checking task status when publish is needed
        """

        payload_list={}
        payload_list['task-id']=task
        headers = {
            'content-type': "application/json",
            'Accept': "*/*",
            'x-chkp-sid': sid,
        }
        response = requests.post(url+"show-task", json=payload_list, headers=headers, verify=False)
        return response



    def __init__(self):

        """
        This is constructor for class, login to API server is handled here - handling also conectivity problems to API
        """


        self.sid=""
        self.standby=False
        # default header without SID
        self.headers_default = {
             'content-type': "application/json",
              'Accept': "*/*",
             }
        # headers for usage in instance methods - with self.SID - will be filled up in constructor
        self.headers = {}
        
        config = configparser.ConfigParser() # config parser instance
        default_cpi_os_path = 'cp.ini' # config file

        try:
            config.read(default_cpi_os_path) #read from cp.ini file
            self.url=config.get('config','url')
            self.user=config.get('config','user')
            self.passowrd=getpass.getpass()

            self.payload_list={}
            self.payload_list['user']=self.user
            self.payload_list['password']=self.passowrd
            
        

        except Exception as e:
            print("there is no cp.ini file or config section is missing: {}".format(e))
            sys.exit(1)
            
        
        done=False
        counter=0
        # loop to handle connection interuption
        while not done:
            counter +=1
            if counter == 5:
                DoLogging().do_logging('Connector()__init__ - connection to mgmt can not be established even in loop...exit')
                raise Exception
                
            try:
                self.response = requests.post(self.url+"login", json=self.payload_list, headers=self.headers_default, verify=False)
                 # verify=False - will work without ssl certificate 
                DoLogging().do_logging('Connector()__init__ - API login data: {}'.format(self.response.text))
                if self.response.status_code == 200:
                    #print(json.loads(self.response.text))
                    try:
                        sid_out=json.loads(self.response.text)
                        try:
                            self.standby=sid_out['standby']
                        except Exception as e:
                            pass
                            
                        self.sid = sid_out['sid']
                        self.headers = {
                                'content-type': "application/json",
                                'Accept': "*/*",
                                'x-chkp-sid': self.sid,
                        }
                        DoLogging().do_logging('Connector()__init__ - Connection to API is okay')
                        DoLogging().do_logging(self.response.status_code)
                        
                    except Exception as e:
                        DoLogging().do_logging('Connector()__init__ - API is not running probably..: {}'.format(e))

                else:
                    try:
                        a = json.loads(self.response.text)
                        print (" ")
                        DoLogging().do_logging('Connector()__init__ - API returned data: {0}'.format(a))
                        print (" ")
                        
                        if a['message']=='Authentication to server failed.':
                            print (" ")
                            DoLogging().do_logging('Connector()__init__ - API returned data: You entered wrong password probably..try it again from the beggining..\n')
                            sys.exit(1)

                        if a['message']=='Administrator is locked.':
                            print (" ")
                            print ("Use this command to unlock admin:\n")
                            DoLogging().do_logging('Connector()__init__ - API returned data: Admin is locked, use mgmt_cli -r true unlock-administrator name ''admin'' --format json -d ''System Data'' ..\n')
                            print (" ")
                            sys.exit(1)
                        DoLogging().do_logging('Connector()__init__ - There is no SID, connection problem to API gateway')
                        time.sleep (5)
                    except Exception as e:
                        DoLogging().do_logging('Connector()__init__ - API is not running probably..:{}'.format(e))
                    continue

            except Exception as e:   
                DoLogging().do_logging('Connector()__init__ - exception occured..can not connect to mgmt server, check IP connectivity or ssl certificates!!!: {}'.format(e))     
            
            else:
                done=True


    def publish(self):

        """
        Publish method is responsible for publishing changes to mgmt server, its here for future usage, its not used now by rulerevision
        """

        payload_list={}
        headers = {
            'content-type': "application/json",
            'Accept': "*/*",
            'x-chkp-sid': self.sid,
        }

        done=False
        counter=0
        
        while not done:
            counter +=1
            if counter == 5:
                DoLogging().do_logging('connection to mgmt for publish does not work even in loop.. exit')
                raise Exception
                sys.exit(1)
            try:
                self.response = requests.post(self.url+"publish", json=payload_list, headers=headers, verify=False)
                DoLogging().do_logging('publish() is going to run..')

                publish_text=json.loads(self.response.text)
                DoLogging().do_logging(publish_text)
                show_task=Connector.task_method(self.sid,self.url,publish_text['task-id'])
                show_task_text = json.loads(show_task.text)
                DoLogging().do_logging(show_task_text)
                
                while show_task_text['tasks'][0]['status'] == "in progress":
                    DoLogging().do_logging(" publish status = ".format(show_task_text['tasks'][0]['progress-percentage']))
                    time.sleep(10)
                    show_task=Connector.task_method(self.sid,self.url,publish_text['task-id'])
                    show_task_text=json.loads(show_task.text)
                    msg = " publish status = {} {}".format(show_task_text['tasks'][0]['progress-percentage'],show_task_text['tasks'][0]['status'])
                    DoLogging().do_logging(msg)
                    
                    
                    
                if show_task_text['tasks'][0]['status'] == "failed":
                    DoLogging().do_logging('publish() publish failed..:{}'.format(show_task_text))
                    raise Exception 
                    

                DoLogging().do_logging('publish() is done')
                DoLogging().do_logging('publish() responce: {}'.format(self.response))
                return self.response
            
            except Exception as e:
                DoLogging().do_logging('Connector()__publish() - exception occured..can not connect to mgmt server, check IP connectivity or ssl certificates!!!: {}'.format(e))
                
            else:
                done=True



    def logout(self):

        """
        Logout method for correct disconenction from API

        """

        done=False
        counter=0
        while not done:
            counter +=1
            if counter == 5:
                DoLogging().do_logging('Connector()__logout() - logout can not be done because connection to mgmt is lost and reconnect does not work...')
                raise Exception
                sys.exit(1)
                
            else:
                try:
                    payload_list={}
                    self.response = requests.post(self.url+"logout", json=payload_list, headers=self.headers, verify=False)
                    if self.response.status_code == 200:
                        DoLogging().do_logging('Connector()__logout() - logout from gw is okay')
                        return self.response.json()
                    else:
                        out = json.loads(self.response.text)
                        DoLogging().do_logging('Connector()__logout() - printing API data for logout issue: {0}'.format(out))
                        return self.response.json()
                    
                except Exception as e:
                    DoLogging().do_logging('Connector()__logout() - connection to gateway is broken, trying again : {}'.format(e))

                else:
                    done=True
           
                     

    def send_cmd(self, cmd, payload):

        """
        Core method, all data are exchanged via this method via cmd variable, you can show, add data etc.
        """

        done=False
        counter=0
        while not done:
            counter +=1
            if counter == 5:
                DoLogging().do_logging('Connector()__send_cmd() - send_cmd() can not be done because connection to mgmt is lost and reconnect does not work, check unpublished changes manually..')
                self.discard()
                self.logout()
                raise Exception
                sys.exit(1)
            else:
                 try:
                     payload_list=payload
                     self.response = requests.post(self.url + cmd, json=payload_list, headers=self.headers, verify=False)
                     if self.response.status_code == 200:
                         DoLogging().do_logging('Connector()__send_cmd() - send cmd is OKAY')
                         return self.response.json()
                     else:
                         out = json.loads(self.response.text)
                         
                         DoLogging().do_logging('Connector()__send_cmd() - printing API data for send_cmd() issue: {0}'.format(out))
                         
                         return self.response.json()
                     
                     
                 except Exception as e:
                    DoLogging().do_logging('Connector()__send_cmd() - POST operation to API is broken due connectivity flap or issue.. trying again....: {}'.format(e))

                    
                 else:
                    done=True


    def discard(self):

        """
        discard method for correct discard of all data modified via API

        """

        done=False
        counter=0
        while not done:
            counter +=1
            if counter == 5:
                DoLogging().do_logging('Connector()__discard() can not be done because connection to mgmt is lost and reconnect does not work, check unpublished changes manually..')
                raise Exception
            else:
                try:
                    payload_list={}
                    self.response = requests.post(self.url+"discard", json=payload_list, headers=self.headers, verify=False)
                    if self.response.status_code == 200:
                        DoLogging().do_logging('Connector()__discard() discard is okay')
                        out = json.loads(self.response.text)
                        DoLogging().do_logging('Connector()__discard() APi data:{}'.format(out))
                        return self.response.json()

                    else:
                        out = json.loads(self.response.text)
                        DoLogging().do_logging('Connector()__discard() APi data:{}'.format(out))
                        return self.response.json()
                except Exception as e:
                    DoLogging().do_logging('Connector()__discard() dicard:connection to gateway is broken, trying again: {}'.format(e))
                   
                else:
                    done=True
                    
                    
    def keep_keepalive(self):
        """
        keep alive to avoid problems when ArcSight search takes so long so CP PI session expires
        """
        
        done=False
        counter=0
        while not done:
            counter +=1
            if counter == 5:
                DoLogging().do_logging('Connector()__keep_keepalive() can not be done because connection to mgmt is lost and reconnect does not work, check unpublished changes manually..')
                raise Exception
                sys.exit(1)
            else:
                try:
                    payload_list={}
                    self.response = requests.post(self.url+"keepalive", json=payload_list, headers=self.headers, verify=False)
                    if self.response.status_code == 200:
                        DoLogging().do_logging('Connector()__keep_keepalive() keepalive is okay')
                        out = json.loads(self.response.text)
                        DoLogging().do_logging('Connector()__keep_keepalive() APi data:{}'.format(out))
                        return self.response.json()

                    else:
                        out = json.loads(self.response.text)
                        DoLogging().do_logging('Connector()__keep_keepalive() APi data:{}'.format(out))
                        return self.response.json()
                except Exception as e:
                    DoLogging().do_logging('Connector()__keep_keepalive() keepalive:connection to gateway is broken, trying again: {}'.format(e))
                   
                else:
                    done=True
                    
    
    def check_object(self, cmd, payload):
        done=False
        counter=0
        while not done:
            counter +=1
            if counter == 5:
                DoLogging().do_logging('Connector()__check_object() can not be done because connection to mgmt is lost and reconnect does not work, check unpublished changes manually..')
                raise Exception
            else: 
                try:
                    payload_list=payload
                    self.response = requests.post(self.url + cmd, json=payload_list, headers=self.headers, verify=False)
                    #"""" UNCOMMENT THIS FOR DEBUG
                    #print (self.response.json())
                    #print (self.response.status_code)
                    #"""

                    #responce 200 pokud objekt existuje a 400 pokud exustuje duplicitni objekt stejneho jmena a 404 pokud neexistuje vubec
                    if self.response.status_code == 200:
                        return True

                    elif self.response.status_code == 400:
                        return True
                    else:
                        return False
                except Exception as e:
                    DoLogging().do_logging('Connector()__check_object() - connection to gateway is broken, trying again: {}'.format(e))
                else:
                    done=True
                    
                    
    def get_sid(self):
        """
        return SID of connector instance
        """
        return self.sid
    
    
    def get_standby(self):
        """
        """
        return self.standby



    

################################################################
################################################################





################################################################



class Push_Data(object):

    def __init__(self, host_to_group_list, group_list, net_list, nat_list, net_to_group_list, host_list, connect):
        
        self.group_list = group_list
        self.net_list = net_list
        self.connect = connect
        self.nat_list = nat_list
        self.net_to_group_list = net_to_group_list
        self.host_to_group_list = host_to_group_list
        self.host_list = host_list




    def add_group(self):
              
        for item in self.group_list:
            payload = {}
            if item['name'] != '':
                payload['name'] = item['name']
                if self.connect.check_object('show-group', payload) == True:
                    print("Group already exists:" + item['name'])
                    continue
                else:
                        # pokud objek neexistuje pridej ho
                        self.connect.send_cmd('add-group', payload)
                        # nastav tagy
                        if item['tag']!='':
                            payload_tag ={}
                            payload_tag['name']= item['tag']
                            if self.connect.check_object('show-tag', payload_tag) == True:   
                                print(" Tag already exists:" + " " + item['tag'])
                            else:
                                self.connect.send_cmd('add-tag', payload_tag)
                                print("Added tag for group:" + item['tag'])
                                
                            payload ['tags'] = item['tag']
                            self.connect.send_cmd('set-group', payload)
                            print("Added group:" + item['name'])          
            else:
                DoLogging().do_logging('Push_Data_add_group() - name for item:{} is missing'.format(item))
        
                
                



    def add_network(self):
        
        for item in self.net_list: # go throug data from csv
            payload = {} # common payload
            payload ['name'] = item['name'] # add name to common payload to check if object exists
            if self.connect.check_object('show-network', payload) == True:
                print("Network with same name already exists, checking IP address:" + item['name'])
                continue

            else:
                payload ['subnet'] = item['subnet4']
                payload ['mask-length'] = item['mask-length4']
                payload ['comments'] = item['comments']
                payload ['ignore-warnings'] ='false'
                #payload ['tags'] = item['tag']
                print (payload)
                # pokud objek neexistuje pridej ho
                self.connect.send_cmd('add-network', payload)
                print("Added network:" + item['name'])





    def set_group_for_net(self):



        for item in self.net_to_group_list: # go throug data from csv

            print (item)

            payload ={} # common payload

            group_payload = {} # help payload for nat-settings

            payload ['name'] = item ['name'] # assing name to be able check if object exists



            if item ['group'] == None: # if nat-settings is true and should be configured, remove name and create nat-settings payload

                continue

            else:

                group_payload['add'] = item ['group']



            if self.connect.check_object('show-network', payload) == True: # check if network object exists

                payload['groups'] = group_payload # add nat_payload to common payload for request

                print("Adding network: " + item['name'] + " " + "into group:" + item ['group'])

                self.connect.send_cmd('set-network', payload) # modify network settings with NAT config





    def set_group_for_host(self):



        """

        Method which adding net to group

        """

        init_counter=0

        end_counter=500

        for item in self.host_to_group_list: # go throug data from csv

            print (item)

            payload ={} # common payload

            group_payload = {} # help payload for nat-settings

            payload ['name'] = item ['name'] # assing name to be able check if object exists



            if item ['group'] == None: # if nat-settings is true and should be configured, remove name and create nat-settings payload

                continue

            else:

                group_payload['add'] = item ['group']



            if self.connect.check_object('show-host', payload) == True: # check if network object exists

                payload['groups'] = group_payload # add nat_payload to common payload for request

                print("Adding host: " + item['name'] + " " + "into group:" + item ['group'])

                self.connect.send_cmd('set-host', payload) # modify network settings with NAT config

                init_counter +=1

                print (init_counter)

                if init_counter==end_counter:

                   self.connect.publish()
                   print("keepalive:".format(self.connect.keep_alive()))

                   end_counter+=500

                   print ("End counter changed: {}".format(end_counter))



        self.connect.publish()



    def set_auto_nat_for_net(self):





        for item in self.nat_list:

            payload ={}

            nat_payload = {}

            payload ['name'] = item ['name']



            if item ['nat-settings'] == 'true':

                del r['name']

                del r['nat-settings']

                if item['hide-behind'] == '':

                    del r ['hide-behind']

                nat_payload = r

            else:

                break

            if self.connect.check_object('show-network', payload) == True:

                payload['nat-settings'] = nat_payload

                print("Configuring NAT for: " + item['name'])

                self.connect.send_cmd('set-network', payload)





    def add_host(self):


        init_counter=0

        end_counter=1000

        for item in self.host_list:

            payload = {}

            payload ['name'] = item['name']

            if self.connect.check_object('show-host', payload) == True:



                print("Host already exists:" + item['name'])

                continue

            else:

                payload ['ip-address'] = item['ip-address']

                payload ['comments'] = item['comments']

                payload ['ignore-warnings'] ='true'

                self.connect.send_cmd('add-host', payload)

                print("Added host:" + item['name'])

                init_counter +=1

                print (init_counter)

                if init_counter==end_counter:

                   self.connect.publish()

                   end_counter+=1000

                   print ("End counter changed")



        self.connect.publish()









##################################################





# main method

def main():
    
    try:
        os.remove('logcp.elg')
    except:
        pass

    argParser = argparse.ArgumentParser(description='CP Mgmt data load script, in parameter -m specify which metod you want to load --> for example -m add_tags, if you want to load all data, specify parameter -m ALL')
    argParser.add_argument("-m", dest="method", help=('add_tags, add_group, add_network, set_auto_nat_for_net, set_group_for_net, set_group_for_host, add_hosts, ALL'), required=True)
    args = argParser.parse_args()
    print("running method:" + " " + args.method)
    group = CSV_Importer_to_List('group_template.csv')
    net= CSV_Importer_to_List('net_template.csv')
    nat = CSV_Importer_to_List('nat_template.csv')
    net_to_group = CSV_Importer_to_List('net_to_group.csv')
    host_to_group = CSV_Importer_to_List('host_to_group.csv')
    host = CSV_Importer_to_List('host.csv')

    try:
        connect = Connector()
        try:
            push_data = Push_Data(host_to_group.get_csv_list(), group.get_csv_list(), net.get_csv_list(),nat.get_csv_list(), net_to_group.get_csv_list(),host.get_csv_list(), connect) # create instance for data pushing - forward lists with data and instance of connector

            if args.method == "ALL":
                push_data.add_tag()
                push_data.add_group()
                push_data.add_network()
                push_data.set_auto_nat_for_net()
                push_data.set_group_for_net()
                push_data.add_host()
                push_data.set_group_for_host()

            elif args.method == "add_tags":
                push_data.add_tag()
            elif args.method == "add_group":
                push_data.add_group() 
            elif args.method == "add_network":
                push_data.add_network() 
            elif args.method == "set_auto_nat_for_net":
                push_data.set_auto_nat_for_net() 
            elif args.method == "set_group_for_net":
                push_data.set_group_for_net()
            elif args.method == "set_group_for_host":
                push_data.set_group_for_host() 
            elif args.method == "add_hosts":
                push_data.add_host() 

            else:
                connect.logout() 
                sys.exit(1)

            connect.logout() # logout
            
        except KeyboardInterrupt:
            DoLogging().do_logging("\n main() - ctrl+c pressed, logout and exit..")
            connect.logout()
            sys.exit(1)

        except Exception as e:
            print (e)
            connect.discard()
            connect.logout()
                
    except KeyboardInterrupt:
        DoLogging().do_logging("\n main() - ctrl+c pressed, logout and exit..")
        print ("can not connect, leaving")
        sys.exit(1)
    except Exception as e:
        print ("can not connect, leaving")
        
    
    
   
        



if __name__ == "__main__":
   
   main()
    



