from CameraDevice import *
import shutil
from yolo_sort import *
from sort import *
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import datetime

from influxdb import InfluxDBClient

class InfluxDBServiceConnect:
    def __init__(self, config):

        self.db_name = config['INFLUXDB_SERVICE']['db_name']

        #pi = config['INFLUXDB_SERVICE']['pi']

        #ip = config['PI_ADDRESSES'][str(config['DEFAULT']['cluster_id'])
        #                                 + str(pi)]

        ip = config['INFLUXDB_SERVICE']['ip']

        # TODO add in ssl?
        self.influx_client = InfluxDBClient(
            ip,
            config['INFLUXDB_SERVICE']['port'],
            config['INFLUXDB_SERVICE']['user'],
            config['INFLUXDB_SERVICE']['pass'],
            self.db_name,
            ssl=True
        )

        #self.influx_client.create_database(self.db_name)


    def push(self, measurement, camera, cluster, analysis_method, device, time, value): # TODO push in different thread
        print('analyis service: ' + str(time))
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

dbConn = InfluxDBServiceConnect(config)




# heartbeat_client = InfluxHeartbeat(config, ''+str(config['DEFAULT']['cluster_id'])+
#                                                '_'+str(config['DEFAULT']['pi_id'])+
#                                                '_cam_'+str(cam_id) + '_camClient')
# cancelled = False
#
# def heartbeat():
#        while not cancelled:
#            heartbeat_client.heartbeat_pulse()
#            time.sleep(5)

# start Heartbeat:
#        self.hb_thread = Thread(target=self.heartbeat)
#        self.hb_thread.start()

# pull in config info
CONFIG_FILE = "cam_manage_config_deploy.ini"
# CONFIG_FILE = "cam_manage_config_test.ini"





config = configparser.ConfigParser()
config.read(CONFIG_FILE)

TOTAL_RECORD_TIME_SEC = int(config['TRACKING']['record_time'])

min_num_frames_for_id = int(config['TRACKING']['min_num_frames_for_id'])

save_loc = config['TRACKING']['save_loc']

##########################################################
# Save frames
cluster = config['DEFAULT']['cluster_id']
cam_id = config['TRACKING']['cams']
device = config['DEFAULT']['pi_id']

cam_addr = config['CAMERAS'][str(cluster) + str(cam_id) + '_ip']
cam_name = config['CAMERAS'][str(cluster) + str(cam_id) + '_id']

# Note | assumes that all cameras have same password and username
cam_user = str(config['CAMERA_DEVICE']['uname'])
cam_pass = str(config['CAMERA_DEVICE']['pass'])
secs_bw_frames = float(config['CAMERA_DEVICE']['secs_bw_frames'])


ipcam = IPCam(cam_addr, cam_user, cam_pass, cam_id)
# ipcam.start()

yolo = yolo_py_consumer()
yolo.start()

print('started thread')

while True:

    ipcam.start()
    print('flushing frames')

    for i in range(3):
        frame = ipcam.get_next_frame()
        print('\tflush')
        time.sleep(1)

    try:
        os.mkdir(save_loc)
    except OSError:
        print ("Creation of the directory %s failed" % save_loc)
    else:
        print ("Successfully created the directory %s " % save_loc)

    frame_num = 0
    start_time = time.time()
    print('saving frames')
    while time.time() - start_time < TOTAL_RECORD_TIME_SEC:

        # s=time.time()

        # print('getting frame number {}'.format(frame_num))

        # time.sleep(secs_bw_frames)

        frame = ipcam.get_next_frame()
        # print(frame)
        cv2.imwrite(str(save_loc) + str(frame_num) + ".jpg", frame)


        frame_num = frame_num + 1
        # print(time.time() - s)

    # print('stopping')
    ipcam.stop()

    #############################
    # get detections

    # yolo = yolo_py_consumer()
    # yolo.start()

    print('starting yolo detections')

    outs = []
    for frame_num, file in enumerate(os.listdir(save_loc)):
        # image = cv2.imread(str(save_loc) + str(file) + ".jpg")

        start = time.time()

        res = yolo.file_consume(str(save_loc) + str(frame_num) + '.jpg', frame_num)

        for item in res:
            outs.append(item)

        # print('total yolo time: {}'.format(time.time() - start))


    ##############################
    # tracking


    # print(outs)
    # print('---------------------')
    # for item in outs:
    #     print(item)
    # print('------------')
    outs = np.array(outs)
    # print(outs)

    # colours = np.random.rand(32,3) #used only for display
    # plt.ion()
    # fig = plt.figure()

    print('starting tracking')

    mot_tracker = Sort(max_age=50, min_hits=15)

    res = {}
    i = 0

    # a = range(int(outs[:, 0].max()) + 1)
    #
    # print(range(int(outs[:, 0].max()) + 1))
    # print(a)
    # os._exit(1)

    for frame_num in range(int(outs[:, 0].max()) + 1):
        # i = i + 1
        # if i > 500:
        #    break

        # print(frame_num)

        start_time = time.time()
        dets = outs[outs[:, 0] == frame_num, 1:6]
        # print(dets)
        # os._exit(1)

        # ax1 = fig.add_subplot(111, aspect='equal')
        # fn = save_loc + '{}.jpg'.format(frame_num)
        # print(fn)
        # im =io.imread(fn)
        # ax1.imshow(im)
        # plt.title('Tracked Targets')
        trackers = mot_tracker.update(dets)

        for d in trackers:
            # print('%d,%d,%.2f,%.2f,%.2f,%.2f,1,-1,-1,-1' % (frame_num, d[4], d[0], d[1], d[2] - d[0], d[3] - d[1]))
            # d = d.astype(np.int32)
            # ax1.add_patch(patches.Rectangle((d[0],d[1]),d[2]-d[0],d[3]-d[1],fill=False,lw=2,ec=colours[d[4]%32,:]))
            # ax1.set_adjustable('box-forced')

            _id = d[4]
            if _id in res:
                res[_id] = res[_id] + 1
            else:
                res[_id] = 1

        # print(len(res.keys()))

        # fig.canvas.flush_events()
        # plt.draw()
        # ax1.cla()

        # print('total time to process frame is: ' + str(time.time() - start_time))

    total_count = 0
    for key, value in res.items():
        print(value)
        if value >= min_num_frames_for_id:
            total_count = total_count + 1

    print()
    print('total number of vehicles seen:')
    print(total_count)
    print('------------------')

    #push(self, measurement, camera, cluster, analysis_method, device, time, value)

    dbcon.push('tracker_vehicle_count', cam_id, cluster, 'sort_tracker_vehicle_count', device, datetime.datetime.now(), total_count)

    # TODO - store in mongo
    # TODO - heartbeat

    # time.sleep(5)

    ##############################
    # Delete Frames

    try:
        shutil.rmtree(save_loc)
    except OSError as e:
        print ("Error: %s - %s." % (e.filename, e.strerror))

    time.sleep(2)




