import zmq
import time
from threading import Thread, Event, ThreadError
import pickle
import zlib
import datetime
import os
import sys


class IPFrameRetriever:
    def __init__(self, frame_consumer, dbConn, heartbeat_client, sub_socket):
        self.context = zmq.Context()
        self.pull_socket = self.context.socket(zmq.SUB)
        self.pull_socket.set_hwm(4)
        print(sub_socket)
        self.pull_socket.bind(sub_socket)
        # self.pull_socket.connect(pull_addr)
        self.pull_socket.setsockopt_string(zmq.SUBSCRIBE, "")

        # self.pull_socket.setsockopt_string(zmq.CONFLATE, 1)
        self.dbConn = dbConn

        self.frame_cons = frame_consumer

        self.thread_cancelled = False
        self.hearbeat_client = heartbeat_client
        self.thread = Thread(target=self.run)
        self.hb_thread = Thread(target=self.heartbeat)

    def start(self):
        self.thread.start()
        self.hb_thread.start()

    def heartbeat(self):
        while True:
            self.hearbeat_client.heartbeat_pulse()
            time.sleep(5)

    def shut_down(self):
        self.thread_cancelled = True
        while self.thread.is_alive():
            time.sleep(1)
        return True

    def is_running(self):
        return self.thread.is_alive()

    def run(self):
        self.frame_cons.start()

        print("starting to recieve messages")

        try:

            while not self.thread_cancelled:
                p = self.pull_socket.recv()

                # p = zlib.decompress(z)
                msg = pickle.loads(p)

                print("msg received")

                if msg['continuing']:
                    result_veh_parked, result_veh_flow, resultped = self.frame_cons.frame_consume(msg['frame'], msg['cam_id'], msg['time'])

                    # print(msg['time'])
                    # print(time.time())
                    # print(msg['time'][:-7] + '.' + msg['time'][-7:])

                    # float_time = float(msg['time'][:-7] + '.' + msg['time'][-7:])

                    push_time = datetime.datetime.fromtimestamp(float(msg['time'])).strftime('%Y-%m-%d %H:%M:%S')

                    # TODO only ready for vehicles from the yolo consumer

                    # data_v = {"result" :result,
                    #         "camera_source": msg['cam_id'],
                    #         "time": msg['time'],
                    #         "consumer": self.frame_cons.str_id()}

                    self.dbConn.push('vehicles_parked', msg['cam_id'], 1, self.frame_cons.str_id(),
                                     1, push_time, result_veh_parked)

                    self.dbConn.push('vehicles_flow', msg['cam_id'], 1, self.frame_cons.str_id(),
                                     1, push_time, result_veh_flow)

                    self.dbConn.push('peds', msg['cam_id'], 1, self.frame_cons.str_id(),
                                     1, push_time, resultped)


                    # self.dbConn.push(data)
                    print(result_veh_parked, result_veh_flow, resultped)

                else:
                    break

            self.frame_cons.complete()

        except Exception as e:
            print("exception thrown: ")
            print(e)
            # self.frame_cons.complete()
            os._exit(1)

        # while not self.thread_cancelled:
        #     z = self.pull_socket.recv()
        #     p = zlib.decompress(z)
        #     msg = pickle.loads(p)
        #
        #     print("msg received")
        #
        #     if msg['continuing']:
        #         result_veh_parked, result_veh_flow, resultped = self.frame_cons.frame_consume(msg['frame'],
        #                                                                                       msg['cam_id'],
        #                                                                                       msg['time'])
        #
        #         # print(msg['time'])
        #         # print(time.time())
        #         # print(msg['time'][:-7] + '.' + msg['time'][-7:])
        #
        #         # float_time = float(msg['time'][:-7] + '.' + msg['time'][-7:])
        #
        #         push_time = datetime.datetime.fromtimestamp(float(msg['time'])).strftime('%Y-%m-%d %H:%M:%S')
        #
        #         # TODO only ready for vehicles from the yolo consumer
        #
        #         # data_v = {"result" :result,
        #         #         "camera_source": msg['cam_id'],
        #         #         "time": msg['time'],
        #         #         "consumer": self.frame_cons.str_id()}
        #
        #         self.dbConn.push('vehicles_parked', msg['cam_id'], 1, self.frame_cons.str_id(),
        #                          1, push_time, result_veh_parked)
        #
        #         self.dbConn.push('vehicles_flow', msg['cam_id'], 1, self.frame_cons.str_id(),
        #                          1, push_time, result_veh_flow)
        #
        #         self.dbConn.push('peds', msg['cam_id'], 1, self.frame_cons.str_id(),
        #                          1, push_time, resultped)
        #
        #         # self.dbConn.push(data)
        #         print(result_veh_parked, result_veh_flow, resultped)
        #
        #     else:
        #         break
        #
        # self.frame_cons.complete()
                

