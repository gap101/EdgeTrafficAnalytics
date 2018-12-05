#!/usr/bin/env python3

import zmq
import configparser
from IPFrameRetriever import IPFrameRetriever
from yolo_consumer import Yolo
from influxdb import InfluxDBClient
from yolo_py_consumer import yolo_py_consumer

from InfluxHeartbeat import InfluxHeartbeat

from yolo_py_consumer_2_types import yolo_py_consumer_dual
import sys


# TODO | need to change this to influx
class InfluxDBServiceConnect:
    def __init__(self, config):

        self.db_name = config['INFLUXDB_SERVICE']['db_name']

        pi = config['INFLUXDB_SERVICE']['pi']

        ip = config['PI_ADDRESSES'][str(config['DEFAULT']['cluster_id'])
                                         + str(pi)]

        # TODO add in ssl?
        self.influx_client = InfluxDBClient(
            ip,
            config['INFLUXDB_SERVICE']['port'],
            config['INFLUXDB_SERVICE']['user'],
            config['INFLUXDB_SERVICE']['pass'],
            self.db_name
        )

        self.influx_client.create_database(self.db_name)


    def push(self, measurement, camera, cluster, analysis_method, device, time, value): # TODO push in different thread

        json_body = [
            {
                "measurement": measurement,
                "tags": {
                    "camera": camera,
                    "cluster": cluster,
                    "analysis": analysis_method,
                    "analysis_device": device
                },
                "time": time,
                "fields": {
                    "value": value
                }
            }

        ]

        print('size of sent message: ')
        print(sys.getsizeof(json_body))

        self.influx_client.write_points(json_body)


def get_consumer(consumer_arg, m_config):
    consumer = None

    if consumer_arg == "yolo":
        consumer = Yolo(0.25)  # TODO - configurable

    elif consumer_arg == "yolo_py":
        consumer = yolo_py_consumer()

    elif consumer_arg == "yolo_py_2":
        consumer = yolo_py_consumer_dual()

    return consumer


CONFIG_FILE = "cam_manage_config_deploy.ini"
config = configparser.ConfigParser()
config.read(CONFIG_FILE)

# Load in config params
cluster = config['DEFAULT']['cluster_id']
id = config['DEFAULT']['pi_id']
cam_dev_id = config['ANALYTICS']['pi']
cam_dev_ip = config['PI_ADDRESSES']['' + str(cluster) + str(cam_dev_id)]
cam_dev_req_port = config['CAMERA_DEVICE']['req_port']
cam_dev_push_port = config['CAMERA_DEVICE']['push_port']

consumer = get_consumer(config['ANALYTICS']['consumer'], config)

# masks = []
# for i in range(0,3):
#    mask_file = config['MASKS']['' + str(cluster) + str(i + 1)]
#    if mask_file is 'none':
#        mask_file = None

#    masks[i] = mask_file

print(consumer.str_id)

dbConn = InfluxDBServiceConnect(config)

# TODO Connect to multiple cam devices? but for now just one

# print('tcp://' + cam_dev_ip + ':' + cam_dev_req_port)
# req_socket = zmq.Context().socket(zmq.REQ)
# req_socket.connect('tcp://' + cam_dev_ip + ':' + cam_dev_req_port)
#
# req_socket.send_pyobj({'type': "register", 'client_id': id})
#
# push_port = req_socket.recv_pyobj()
# push_addr = 'tcp://' + cam_dev_ip + ':' + push_port

# TODO change this!!
pull_addr = 'tcp://*:' + config['ANALYTICS']['bind_port']



print('starting consumer')

frame_retriever = IPFrameRetriever(consumer, dbConn, InfluxHeartbeat(config, config['ANALYTICS']['consumer']), pull_addr)

frame_retriever.start()  # TODO unregister in event of failure?
