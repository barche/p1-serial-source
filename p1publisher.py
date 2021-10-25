# -*- coding: utf-8 -*-
"""
Created on Wed Dec 23 22:37:55 2020

MQTT client for listening on a serial device (typically a USB port) for P1 electricity meter messages and forwarding them over MQTT.
Meant to work together with https://gitlab.com/Epyon01P/p1-cookie-parser and parts of this file are based on that code and (c) Joannes Laveyne 

@author: Bart Janssens
"""
import json
import time
import yaml
import paho.mqtt.client as mqtt
import signal
import os
import serial
import _thread

"""
MQTT configuration vars
Overridden in the mqtt block in the config file, if present
"""
clientname="utility_meter_serial"
broker="localhost"
port=1883
username=""
password=""

dir_path = os.path.dirname(os.path.realpath(__file__))
my_id = ''
topic = ''
source = {}
with open(dir_path + "/" + "p1config.yaml", 'r') as stream:
    try:
        config = yaml.safe_load(stream)['configuration']
        my_id = config['cookie']['id']
        source = config['source']
        topic = 'stat/' + my_id + '/p1/telegram'
        if 'mqtt' in config:
            mqttconf = config['mqtt']
            if 'broker' in mqttconf:
                broker = mqttconf['broker']
            if 'port' in mqttconf:
                port = mqttconf['port']
            if 'username' in mqttconf:
                username = mqttconf['username']
            if 'password' in mqttconf:
                password = mqttconf['password']
            if 'client_id' in mqttconf:
                clientname = mqttconf['client_id']
    except yaml.YAMLError as exc:
        print(exc)

client = mqtt.Client(clientname)

def on_connect(client, userdata, flags, rc):
    if rc != 0:
        print("MQTT connection failed: " + mqtt.connack_string(rc))
        _thread.interrupt_main()
    else:
        print("Connected to MQTT broker")

client.on_connect = on_connect

if username:
    client.username_pw_set(username, password)

client.connect(broker)

"""
When the Grim Sysadmin comes to reap with his scythe, 
let this venerable daemon process die a Graceful Death
"""
class GracefulDeath:
  kill_now = False
  def __init__(self):
    signal.signal(signal.SIGINT, self.exit_gracefully)
    signal.signal(signal.SIGTERM, self.exit_gracefully)
  def exit_gracefully(self,signum, frame):
    self.kill_now = True

"""
Process the input stream from the meter and return a single complete telegram
"""
def processMeterStream(istream):
    iscomplete = False
    telegram = ''
    while not iscomplete:
        line = istream.readline()
        if not line:
            return ''
        if isinstance(line, bytes):
            line = line.decode('utf-8')
        if line.startswith('/'):
            telegram = line
            continue
        if telegram:
            telegram += line
        if line.startswith('!'):
            iscomplete = True
    return telegram

def opensource(src):
    if 'file' in src:
        return open(src['file'], 'r')
    
    return serial.Serial(src['device'], 115200, xonxoff=1, timeout=1)

"""
Main loop
Check for MQTT messages, on arrival dispatch them to the parser
Meant to keep running as a service, until killed by UNIX kill command
"""
#Nooooo you can't just import me as a module in your program nooooo
if __name__ == '__main__':
    killer = GracefulDeath()
    counter = 0
    with opensource(source) as istream:
        while not killer.kill_now:
            try:
                telegram = processMeterStream(istream)
                if telegram:
                    message = {}
                    message['device_id'] = my_id
                    message['name'] = 'p1telegram'
                    message['value'] = telegram
                    message['unit'] = None
                    message['timestamp'] = round(time.time())
                    counter += 1
                    if counter == 10:
                        client.loop_start()
                        client.publish(topic,json.dumps(message))
                        client.loop_stop()
                        counter = 0
            except KeyboardInterrupt:
                print("Disconnecting from broker... ", end='')
                client.disconnect()
                print("Press Ctrl-C to terminate while statement")
                pass
        #Make a graceful exit when this daemon gets terminated
        print("Termination signal received")
        print("Disconnecting from broker... ", end='')
        client.disconnect()
        print("done")
