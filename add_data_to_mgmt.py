#!/bin/python

"""
This code is for Check Point R80.10 API. it loads data from csv and adding those to mgmt server
@author: ivohrbacek@gmail.com / ivo.hrbacek@ixperta.com
"""

import urllib3
import csv
import pprint
import json
import os, time, datetime, sys, shutil
import requests
import configparser
import sys
import argparse

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

#############################

class CSV_Importer_to_List(object):

    """
    Import data from csv to lists
    """

    def __init__(self, file_name):
        #self.filename = file_name
        self.dic_list = []
        try:
            self.reader = csv.DictReader(open(file_name, 'r'))
            for line in self.reader:
                self.dic_list.append(line)
        except IOError:
            print("one csv file you specified does not exists")
            #sys.exit(1)

    def get_csv_list(self):
        return self.dic_list

##############################################



###############################################

class Connector(object):

    """
    Connector class handling connectivity via API to mgmt server
    """

    @classmethod
    def task(cls,sid,url,task):

        """
    Help method for check if task finsihed and changes can be pushed by publish
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

         self.sid=""
         self.task = ""
         # default header without SID
         self.headers_default = {
             'content-type': "application/json",
              'Accept': "*/*",
             }
         # headers for usegae in instance methods - with self.SID     - will be filled up in constructor
         self.headers = {}

         config = configparser.ConfigParser() # config parser instance
         default_cpi_os_path = 'cp.ini' # config file

         # check
         try:
             print ("here OK, connector __init__")
             config.read(default_cpi_os_path) #read from cp.ini file
             self.url=config.get('config','url')
             self.user=config.get('config','user')
             self.passowrd=config.get('config','password')

             payload_list={}
             payload_list['user']=self.user
             payload_list['password']=self.passowrd

         except Exception as e:
             print("there is no cp.ini file or config section is missing: {}".format(e))
             sys.exit(1)

         try:
             self.response = requests.post(self.url+"login", json=payload_list, headers=self.headers_default, verify=False) # verify=False - will work without ssl certificate

             if self.response.status_code == 200:
                 sid_out=json.loads(self.response.text)
                 print(sid_out)
                 self.sid = sid_out['sid']
                 self.headers = {
                        'content-type': "application/json",
                        'Accept': "*/*",
                        'x-chkp-sid': self.sid,
                 }
                 print("Connection to mgmt is okay..")

             else:
              print("There is no SID, connection problem to mgmt server")
              print(self.response.status_code)

         except requests.exceptions.ConnectionError:
             print("can not connect to mgmt server, check connectivity or ssl certificates!!!")
             print(self.response.status_code)
             #sys.exit(1)


    def logout(self):
        # avoid connectovity interruption - thats why try except here
        done=False
        while not done:
            try:
                payload_list={}
                self.response = requests.post(self.url+"logout", json=payload_list, headers=self.headers, verify=False)
                #print self.response.json()
                print("Logout OK")
                return self.response
            except:
                print("connection to mgmt server broken, trying again from logout method")
            else:
                done=True



    def publish(self):
        # avoid connectovity interruption - thats why try except here
        done=False
        while not done:
            try:
                payload_list={}

                self.response = requests.post(self.url+"publish", json=payload_list, headers=self.headers, verify=False)

                publish_text=json.loads(self.response.text)
                #print publish_text

                show_task=Connector.task(self.sid,self.url,publish_text['task-id'])
                #print show_task

                show_task_text = json.loads(show_task.text)
                #print show_task_text

                #print json.loads(show_task.text)

                while show_task_text['tasks'][0]['status'] == "in progress":
                    print(" publish status = ", show_task_text['tasks'][0]['progress-percentage'])
                    time.sleep(3)
                    show_task=Connector.task(self.sid,self.url,publish_text['task-id'])
                    show_task_text=json.loads(show_task.text)
                    print(" publish status = ", show_task_text['tasks'][0]['progress-percentage'] , show_task_text['tasks'][0]['status'])

                print("Publish OK")
                return self.response

            except:
                print("connection to mgmt server broken, trying again from publish method")
            else:
                done=True




    def send_cmd(self, cmd, payload):
        # avoid connectovity interruption - thats why try except here
        done=False
        while not done:
            try:
                payload_list=payload
                self.response = requests.post(self.url + cmd, json=payload_list, headers=self.headers, verify=False)

                #"""" UNCOMMENT THIS FOR DEBUG
                print (self.response.json())
                print (self.response.status_code)
                #"""

                return self.response.status_code
            except:
                print("connection to mgmt server broken, trying again from send_cmd method")
            else:
                done=True




    def check_object(self, cmd, payload ):
        # avoid connectovity interruption - thats why try except here
        done=False
        while not done:
            try:
                payload_list=payload

                self.response = requests.post(self.url + cmd, json=payload_list, headers=self.headers, verify=False)
                #"""" UNCOMMENT THIS FOR DEBUG
                print (self.response.json())
                print (self.response.status_code)
                #"""

                #responce 200 pokud objekt existuje a 400 pokud exustuje duplicitni objekt stejneho jmena a 404 pokud neexistuje vubec
                if self.response.status_code == 200:

                    return True

                elif self.response.status_code == 400:

                    return True

                else:
                    return False
            except:
                print("connection to mgmt server broken, trying again from check_object method")
            else:
                done=True


################################################################


################################################################

class Push_Data(object):


    def __init__(self, group_list, net_list, nat_list, net_to_group_list, host_list, connect):
        self.group_list = group_list
        self.net_list = net_list
        self.connect = connect
        self.nat_list = nat_list
        self.net_to_group_list = net_to_group_list
        self.host_list = host_list


    def add_tag(self):
        tags = []
        # check csv files for tags
        for item in self.group_list:
            tags.append(item['tag'])
        for item in self.net_list:
            tags.append(item['tag'])

        # sort list and remove duplicate entry
        sorted_list = list(set(tags))
        for item in sorted_list:
            if item != '':
                payload ={}
                payload['name']= item
                if self.connect.check_object('show-tag', payload) == True:
                    print(" Tag already exists:" + " " + item)
                    continue
                else:
                    # pokud objek neexistuje pridej ho
                    self.connect.send_cmd('add-tag', payload)
                    print("Added tag:" + item)


    def add_group(self):
        for item in self.group_list:

            payload = {}
            payload ['name'] = item['name']

            if self.connect.check_object('show-group', payload) == True:
                print("Group already exists:" + item['name'])
                continue
            else:
                    # pokud objek neexistuje pridej ho
                    self.connect.send_cmd('add-group', payload)
                    # nastav tagy
                    if item['tag']!='':
                        payload ['tags'] = item['tag']
                        # update na TAgy
                        self.connect.send_cmd('set-group', payload)
                        print("Added group:" + item['name'])

    def add_network(self):

        """
        Method which adding networks
        """

        for item in self.net_list: # go throug data from csv
            payload = {} # common payload
            payload ['name'] = item['name'] # add name to common payload to check if object exists
            if self.connect.check_object('show-network', payload) == True:

                print("Network already exists:" + item['name'])
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

        """
        Method which adding net to group
        """

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




    def set_auto_nat_for_net(self):

        """
        Method which setting up NAT settings for particualr networks
        """

        for item in self.nat_list: # go throug data from csv
            payload ={} # common payload
            nat_payload = {} # help payload for nat-settings
            payload ['name'] = item ['name'] # assing name to be able check if object exists

            if item ['nat-settings'] == 'true': # if nat-settings is true and should be configured, remove name and create nat-settings payload
                r = dict(item) # create tem object
                del r['name'] # remove name item
                del r['nat-settings'] # remove nat-settings parameter which inform NAT should be handled - this is not NAT payload- just boolen
                if item['hide-behind'] == '': # if there is hide method
                    del r ['hide-behind'] # remove hide behind item
                nat_payload = r # create nat_payload
            else:
                break
            if self.connect.check_object('show-network', payload) == True: # check if network object exists
                payload['nat-settings'] = nat_payload # add nat_payload to common payload for request
                print("Configuring NAT for: " + item['name'])
                self.connect.send_cmd('set-network', payload) # modify network settings with NAT config


    def add_host(self):

        """
        Method which setting up NAT settings for particualr networks
        """
        for item in self.host_list:
            payload = {} # common payload
            payload ['name'] = item['name'] # add name to common payload to check if object exists
            if self.connect.check_object('show-host', payload) == True:

                print("Host already exists:" + item['name'])
                continue
            else:
                payload ['ip-address'] = item['ip-address']
                payload ['comments'] = item['comments']
                payload ['tags'] = item['tag']
                # pokud objek neexistuje pridej ho
                self.connect.send_cmd('add-host', payload)
                print("Added host:" + item['name'])




##################################################


# main method
def main():

    """
    Main method where all data and instances are loaded and data are pushed to mgmt via API
    """

    # hangle log file
    try:
        os.remove('log.elg') # remove old log file
        logpath = 'log.elg' # create log file
    except:
        print("log file doe not exists, creating one..")
        logpath = 'log.elg' # create log file


    # load parameters from user
    argParser = argparse.ArgumentParser(description='CP Mgmt data load script, in parameter -m specify which metod you want to load --> for example -m add_tags, if you want to load all data, specify parameter -m ALL')
    argParser.add_argument("-m", dest="method", help=('add_tags, add_group, add_network, set_auto_nat_for_net, set_group_for_net,add_hosts, ALL'), required=True)
    args = argParser.parse_args()
    print("running method:" + " " + args.method)

    # log and run
    old_stdout = sys.stdout # out to log file
    with open(logpath,"a") as log_file: # open log file for write
                sys.stdout = log_file
                print('%s - starting script......' % str(datetime.datetime.now()).split('.')[0])

                 ## load data
                group = CSV_Importer_to_List('group_template.csv') # load group csv and convert it to list of dictionaries
                net= CSV_Importer_to_List('net_template.csv') # load nets csv and convert it to list of dictionaries
                nat = CSV_Importer_to_List('nat_template.csv') # load nat csv and convert it to list of dictionaries
                net_to_group = CSV_Importer_to_List('net_to_group.csv') # load nat csv and convert it to list of dictionaries
                host = CSV_Importer_to_List('host.csv')# load hosts csv and convert it to list of dictionaries

                print ("here OK, csv data")
                # connect to mgmt
                try:
                    connect = Connector() # create instance of Connector to mgmt to be able to work via API
                    print ("here OK, connector")
                    push_data = Push_Data(group.get_csv_list(), net.get_csv_list(),nat.get_csv_list(), net_to_group.get_csv_list(),host.get_csv_list(), connect) # create instance for data pushing - forward lists with data and instance of connector

                # decide what to push according to user parameter
                    if args.method == "ALL":
                        push_data.add_tag() # push tags
                        push_data.add_group() #push groups
                        push_data.add_network() #push networks
                        push_data.set_auto_nat_for_net() # set NAT
                        push_data.set_group_for_net() # set nets to group
                        push_data.add_host()# add hosts


                    elif args.method == "add_tags":
                        print("Running tags")
                        push_data.add_tag() # push tags
                    elif args.method == "add_group":
                        push_data.add_group() #push groups
                    elif args.method == "add_network":
                        push_data.add_network() # push tags
                    elif args.method == "set_auto_nat_for_net":
                        push_data.set_auto_nat_for_net() #push groups
                    elif args.method == "set_group_for_net":
                        push_data.set_group_for_net() # set nets to group
                    elif args.method == "add_hosts":
                        push_data.add_host() # set nets to group


                    else:
                        print("Nothing was added, have you specified right method???")
                        connect.publish() # publish changes
                        connect.logout() # logout
                        sys.exit(1)

                    connect.publish() # publish changes
                    connect.logout() # logout
                    print('%s - script finished!' % str(datetime.datetime.now()).split('.')[0])
                    # print file to terminal
                    sys.stdout = old_stdout

                except Exception as e:
                    print('%s - script crashed!!!!!!!' % str(datetime.datetime.now()).split('.')[0])
                    print ("error:{}".format(e))
                    sys.stdout = old_stdout


    # print file to terminal
    with open("log.elg", "r") as f:
        shutil.copyfileobj(f, sys.stdout)



# if script is loaded, start with main method
if __name__ == "__main__":
    main()
