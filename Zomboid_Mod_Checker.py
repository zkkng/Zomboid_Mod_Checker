#!/usr/bin/env python3
import requests
import json
import time
import datetime
import valve.rcon
import platform
import os
import subprocess
from os import path

global run_count
global startup_update_times_dict
global compare_update_times_dict


######## USER SUPPLIED VALUES ######## 

# File Locations
ini_file = r""
startup_script = r""

# RCON details
#Since this is Valve server RCON this might need to be your public IP even if the server is local
server_address = "XXX.XXX.XXX.XXX"
rcon_port = 27015
rcon_password = ""

###################################### 

rcon_details = (server_address, int(rcon_port))
run_count = 0
startup_update_times_dict = {}
compare_update_times_dict = {}
ws_line = "WorkshopItems="
post_dict = {}
id_list = []
#startup_update_times_dict = []
#compare_update_times_dict = []

#Testing zone


def restart_script():
    if platform.system() == "Windows":
        print("Windows")
        os.startfile(sys.argv[0])
        time.sleep(0.2)
        quit()
    else:
        print("Linux")
        self_path = str(os.path.abspath(__file__))
        os.system("python3 "+self_path)
        time.sleep(0.2)
        quit()

def close_server(rcon_details, rcon_password):
    try: 
        with valve.rcon.RCON(rcon_details, rcon_password, timeout=10) as rcon:
                    rcon.execute("quit",block=True, timeout=10)
    except valve.rcon.RCONCommunicationError:
        print("Server shutdown!")
    except (ConnectionRefusedError, TimeoutError) as e:
        print("Connection to RCON refused or timed out. You may have configured port forwarding, firewall, or server details incorrectly!")
        print("Error: "+str(e))
        print("If you continue from here the script will just try to relaunch the server. If its not working right just exit this script entirely and fix your configuration.")
        input("Press Enter to continue...")
        
    restart_script()
    

def check_again(rcon_details, rcon_password):
    print("Rechecking mods for updates - "+str(datetime.datetime.now().replace(microsecond=0)))
    #For any additional executions of generate_batches() you need to ensure compare_update_times_dict is set back to {} first
    global compare_update_times_dict
    compare_update_times_dict = {}
    generate_batches()
    if startup_update_times_dict == compare_update_times_dict:
        print("No mod updates detected.")
    else:
        print("Mod update detected. Restarting server now.")
        close_server(rcon_details, rcon_password)
    print("Time until next check: ")
    # Rechecks every 5 minutes.
    t = 300
    while t:
        mins, secs = divmod(t, 60)
        timer = '{:02d}:{:02d}'.format(mins, secs)
        print(timer, end="\r")
        time.sleep(1)
        t -= 1
    
    print("00:00 - Rechecking now!")
        
def update_dict_maker(data):
    index = 0
    global run_count
    if run_count == 1:
        dict_name = "startup_update_times_dict"
    else:
        dict_name = "compare_update_times_dict"
    while index < len(data):
        try:
            mod_id = data[index]['publishedfileid']
            update_time = data[index]['time_updated']
            globals()[dict_name][mod_id] = update_time
            # Increasing index has to be at the bottom or it breaks
            index += 1
        except (KeyError):
            print("Unexpected workshop info returned for mod "+str(data[index]['publishedfileid'])+"! Unable to check last updated time.")
            #Increment even on failure or it will be stuck in a death loop
            index += 1

def post_request(post_dict):
    r = requests.post("https://api.steampowered.com/ISteamRemoteStorage/GetPublishedFileDetails/v1/", data=post_dict)
    pp = json.loads(r.text)
    #print(json.dumps(pp['response']['publishedfiledetails'], indent=2))
    data = pp['response']['publishedfiledetails']
    update_dict_maker(data)
    
#https://stackoverflow.com/questions/8290397/how-to-split-an-iterable-in-constant-size-chunks
def batch(iterable, n=1):
    l = len(iterable)
    for ndx in range(0, l, n):
        yield iterable[ndx:min(ndx + n, l)]

def generate_batches():
    global run_count
    run_count += 1
    for x in batch(id_list, 10):
        post_dict = {}
        id_index = 0
        post_dict["itemcount"] = len(x)
        for mod_id in x:
            post_dict["publishedfileids["+str(id_index)+"]"] = mod_id
            id_index += 1
        post_request(post_dict)

def startup_server(startup_script):
    if platform.system() == "Windows":
        os.startfile(startup_script)
    else:
        #Currently still pipes stderr to console. Might change later.
        os.system("(/bin/bash "+startup_script+" &) > /dev/null")

def main(ini_file,ws_line,startup_script):
    startup_server(startup_script)
    file_path = path.relpath(ini_file)
    with open(file_path) as file_read:
        lines = file_read.readlines()
        new_list = []
        idx = 0
        for line in lines:
            if ws_line in line:
                new_list.insert(idx, line)
                idx += 1
        if len(new_list)==0:
            print("\n\"" +ws_line+ "\" is not found in \"" +file_path+ "\"!")
        else:
            # 2 lines contain "WorkshopItems=", we want the second one.
            id_string = end=new_list[1][14:].rstrip()
    #Made this global so there is no need to rerun this portion for subsequent tests.
    #Still rerunning batching because I don't want to bother making variable amounts of global vars and it really isn't a huge load to batch.
    #Subsequent runs will just recall generate_batches()
    global id_list
    id_list = id_string.split(";")
    generate_batches()



main(ini_file,ws_line,startup_script)
time.sleep(10)
while True:
    check_again(rcon_details, rcon_password)