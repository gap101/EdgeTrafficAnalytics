import configparser
import pickle
import time

from threading import Thread, ThreadError

from PIL import Image
import urllib3
import io
import numpy

import cv2
import zmq
import os

#from InfluxHeartbeat import InfluxHeartbeat

# CONFIG_FILE = "cam_manage_config_deploy.ini"
CONFIG_FILE = "cam_manage_config_test.ini"

CAMERA_URI_ARG = '/cgi-bin/api.cgi?cmd=Snap&channel=0&rs=wuuPhkmUCeI9WG7C&user='

class IPCam:
    def __init__(self, ip, user, password, cam_id):
        self.ip = ip
        self.user = user
        self.password = password

        self.vcap = cv2.VideoCapture('rtmp://' + str(ip) +
                                     '/bcs/channel0_main.bcs?channel=0&stream=0&user='
                                     + str(user) + '&password=' + str(password))
        self.cam_id = cam_id
        self.grabbed, self.frame = self.vcap.read()
        self.new_frame = True
        self.stopped = True

    def connect(self):
        self.vcap = cv2.VideoCapture('rtmp://' + str(self.ip) +
                                     '/bcs/channel0_main.bcs?channel=0&stream=0&user='
                                     + str(self.user) + '&password=' + str(self.password))

    def start(self):
        self.stopped = False
        Thread(target=self.update, args=()).start()
        return self

    def update(self):
        while True:
            try:
                if self.stopped:
                    return

                self.connect()

                while True:
                    if self.stopped:
                        return
                    self.grabbed, self.frame = self.vcap.read()
                    self.new_frame = True

            except cv2.error:
                time.sleep(1)
                print("network lost; attempt reconnection")

    def get_next_frame(self):
        while not self.stopped:
            if self.new_frame:
                self.new_frame = False
                return self.frame

    def stop(self):
        self.stopped = True


class CameraClient:
    def __init__(self,
                 config,
                 push_port_param,
                 cam_ip,
                 cam_uname,
                 cam_pass,
                 seconds_between_frames,
                 cam_id,
                 resize_factor=0.25):

        self.ip_cam_cv2 = IPCam(cam_ip, cam_uname, cam_pass, cam_id)

        self.zmq_context = zmq.Context()
        self.push_socket = self.zmq_context.socket(zmq.PUB)
        self.push_socket.set_hwm(4)
        # print("tcp://*:%s" % push_port_param)
        # self.push_socket.bind("tcp://*:%s" % push_port_param)
        # TODO put this in the config

        connect_addr = config['PI_ADDRESSES'][str(config['DEFAULT']['cluster_id'])
                                         + str(config['ANALYTICS']['pi'])]

        print('tcp://' + connect_addr + ':' + config['ANALYTICS']['bind_port'])

        self.push_socket.connect('tcp://' + connect_addr + ':' + config['ANALYTICS']['bind_port'])

        self.thread_cancelled = False
        self.thread = None

        self.resize_factor = resize_factor

        self.cam_ip = cam_ip
        self.cam_uname = cam_uname
        self.cam_pass = cam_pass
        self.cam_id = cam_id

        # self.subscribers = set()

        self.seconds_between_frames = seconds_between_frames

#        self.heartbeat_client = InfluxHeartbeat(config, ''+str(config['DEFAULT']['cluster_id'])+
#                                                '_'+str(config['DEFAULT']['pi_id'])+
#                                                '_cam_'+str(cam_id) + '_camClient')

#    def heartbeat(self):
#        while not self.thread_cancelled:
#            self.heartbeat_client.heartbeat_pulse()
#            time.sleep(5)

    def start(self):
        self.thread_cancelled = False
        self.ip_cam_cv2.start()
        print('started rtmp ip cam')
        self.thread = Thread(target=self.run)

        self.thread.start()

        # start Heartbeat:
#        self.hb_thread = Thread(target=self.heartbeat)
#        self.hb_thread.start()

    def shut_down(self):
        self.thread_cancelled = True
        while self.thread.is_alive():
            time.sleep(1)

        self.thread = None
        self.hb_thread = None

    def push_message(self, continuing, frame=None):
        msg = {'continuing': continuing,
               'cam_id': self.cam_id,
               'frame': frame,
               # 'time': str(time.time()).replace('.', '')}
               'time': str(time.time())}
        print("pushing message")


        p = pickle.dumps(msg)
        # z = zlib.compress(p)

        self.push_socket.send(p)

    # def register(self, client_id):
    #     if len(self.subscribers) <= 0:
    #         self.start()
    #
    #     self.subscribers.add(client_id)

    # def unregister(self, client_id):
    #     if client_id in self.subscribers:
    #         self.push_message([client_id], False)
    #         self.subscribers.remove(client_id)
    #
    #         if len(self.subscribers) is 0:
    #             self.shut_down()

    def is_running(self):
        return self.thread.is_alive()

    def run(self):
        while not self.thread_cancelled:
            time.sleep(self.seconds_between_frames)
            try:
                frame=self.ip_cam_cv2.get_next_frame()
                self.push_message(True, frame=frame)

            except ThreadError as e:
                print('thread error')
                print(e.args)
                self.thread_cancelled = True

            except Exception as e:
                print('exception thrown:')
                print(e)
                os._exit(1)

class CameraDeviceService:

    def __init__(self,
                 config):

        self.config = config

        self.cam_id = config['DEFAULT']['cam']
        self.cluster = config['DEFAULT']['cluster_id']
        self.req_port = config['CAMERA_DEVICE']['req_port']
        self.push_port = config['CAMERA_DEVICE']['push_port']

        self.client = None
        self.client_setup()

        # self.reply_socket = zmq.Context().socket(zmq.REP)
        # self.reply_socket.bind("tcp://*:%s" % self.req_port)

        print("started CameraDeviceService")

        self.client.start()

        # enter message loop
        # while True:
        #
        #     msg = self.reply_socket.recv_pyobj()
        #     print("Recieved request")
        #
        #     # {type: register, client_id: id}
        #     if msg['type'] == "register":
        #         self.client.register(msg['client_id'])
        #         self.reply_socket.send_pyobj(self.push_port)
        #
        #     if msg['type'] == 'unregister':
        #         self.client.unregister(msg['client_id'])
        #         self.reply_socket.send_pyobj(True)

    def client_setup(self):
        # Note | assumes that you only connect to cameras in the same cluster
        cam_addr = self.config['CAMERAS'][str(self.cluster) + str(self.cam_id) + '_ip']
        cam_name = self.config['CAMERAS'][str(self.cluster) + str(self.cam_id) + '_id']

        # Note | assumes that all cameras have same password and username
        cam_user = str(self.config['CAMERA_DEVICE']['uname'])
        cam_pass = str(self.config['CAMERA_DEVICE']['pass'])
        secs_bw_frames = float(self.config['CAMERA_DEVICE']['secs_bw_frames'])

        self.client = CameraClient(self.config,
                                   self.push_port,
                                   cam_addr,
                                   cam_user,
                                   cam_pass,
                                   secs_bw_frames,
                                   cam_name)


if __name__ == "__main__":
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE)

    # parser = argparse.ArgumentParser(description='Connect and pull frames from networked Camera')
    # parser.add_argument('camid', type=int,
    #                     help="the id of the camera to connect to (assumes the camera is in the same cluster")
    #
    # parser.add_argument('--imgdir', dest='imgdir', type=str, default=None,
    #                     help="if passed, the directory of images to test on")
    #
    # args = parser.parse_args()
    # camera_to_connect_to = args.camid
    # img_dir = args.imgdir

    service = CameraDeviceService(config)
