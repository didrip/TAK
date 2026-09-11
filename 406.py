#!/usr/bin/python -u

import logging
import os
import socket
import xml.etree.ElementTree as ET
from time import time, gmtime, strftime, sleep
import serial

# COT destination - default to TAK multicast network
ATAK_HOST = os.getenv('ATAK_HOST', '127.0.0.1')
ATAK_PORT = int(os.getenv('ATAK_PORT', '8087'))
    
ser=serial.Serial(port="/dev/bus/usb/007",baudrate=4800,bytesize=8,parity='N',stopbits=1,timeout=1)
# Parametres
# {'baudrate': 4800, 'bytesize': 8, 'parity': 'N', 'stopbits': 1, 'xonxoff': False, 'dsrdtr': False, 'rtscts': False, 'timeout': 1, 'write_timeout': None, 'inter_byte_timeout': None}
ser.close()
ser.open()
if ser.isOpen():
	print('Port '+ser.name+' ouvert')

# Enable debug output
DEBUG_LEVEL = int(os.getenv('DEBUG', '1'))

# Validity period of CoT events, for setting "stale" attribute
COT_EVT_TTL = 86400  # seconds

# Event type
#TYPE_COT = 'a-u-G' # Point
TYPE_COT = 'b-a-o-tbl' # Alerte

def Balise2CoT(lat,lon):

    # Generate remark field
    remark = 'Balise 406MHz'

    TIME_FORMAT = '%Y-%m-%dT%H:%M:%SZ'

    # Event fields
    event_attr = {
        'version': '2.0',
        'uid': 'Balise406',
        'time': strftime(TIME_FORMAT, gmtime()),
        'start': strftime(TIME_FORMAT, gmtime()),
        'stale': strftime(TIME_FORMAT, gmtime(time()+COT_EVT_TTL)),
        'type': TYPE_COT,
        'how': 'm-g' # Event "how" (how the coordinates were generated), presumably GPS
    }

    # Point fields
    point_attr = {
        'lat': lat,
        'lon': lon,
        'hae': '0',
        'ce': '9999999.0',  # unspec
        'le': '9999999.0',  # unspec
    }

    print(strftime(TIME_FORMAT, gmtime())+" ; "+point_attr['lat']+" ; "+point_attr['lon'])
    
    # Mandatory schema, "event" element at top level, with sub-elements "point" and "detail"
    cot = ET.Element('event', attrib=event_attr)
    ET.SubElement(cot, 'point', attrib=point_attr)
    det = ET.SubElement(cot, 'detail')
    ET.SubElement(det, 'contact', attrib={'callsign': 'Balise406'})
    ET.SubElement(det, 'usericon', attrib={'iconsetpath': 'COT_MAPPING_2525C/a-u/a-u-G'})
    ET.SubElement(det, 'remarks').text = remark

    #cotXML = '<?xml version="1.0" standalone="yes"?>'.encode('utf-8')
    cotXML = ''.encode('utf-8')
    cotXML += ET.tostring(cot)

    # Send CoT message to ATAK
    o_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    o_sock.connect((ATAK_HOST, ATAK_PORT))
    o_sock.send(cotXML)
    o_sock.close()
    logger.debug('Sent to %s:%d\n' % (ATAK_HOST, ATAK_PORT))


if __name__ == '__main__':

    # Enable debug output
    DEBUG_LEVEL = int(os.getenv('DEBUG', '1'))

    logger = logging.getLogger()
    logger.addHandler(logging.StreamHandler())
    logger.setLevel(logging.INFO)

    if DEBUG_LEVEL > 0:
        logger.setLevel(logging.DEBUG)

    try:
        while ser.isOpen():
           line406=ser.readline()  # copie d'une ligne entière jusqu'à \n dans la variable line
           #print(line406)
           line406=b'$GPGGA,120814.000,4320.1960,N,00602.2620,E,1,08,2.0,00.0,M,,,,0000*32\r\n'
           if ((line406[:6] == b'$GPGGA' or line406[:6] == b'$GNGGA') and b'$GPRMC' not in line406):
                latPart = str(line406).split(",")[2:3]   # Latitude, format ddmm.mmmmmmm
                longPart = str(line406).split(",")[4:5]  # Longitude, format dddmm.mmmmmmm
                latDegrees = latPart[0][:2]
                longDegrees = longPart[0][:3]
                latMinutes = latPart[0][2:]
                longMinutes = longPart[0][3:]
                latitude_baliz = round((int(latDegrees) + float(latMinutes) / 60),5)
                longitude_baliz = round((int(longDegrees) + float(longMinutes) / 60),5)
                if (str(line406).split(",")[3:4][0][0]=="S"):
                    latitude_baliz = -latitude_baliz
                if (str(line406).split(",")[5:6][0][0]=="W"):
                    longitude_baliz = -longitude_baliz
                Balise2CoT(str(latitude_baliz),str(longitude_baliz))
           sleep(1)
    # Catch CTRL+C nicely.
    except KeyboardInterrupt:
        ser.close()
        print('Port '+ser.name+' fermé')

