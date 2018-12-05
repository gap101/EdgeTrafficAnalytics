from CameraDevice import *
import shutil
import datetime

# pull in config info
CONFIG_FILE = "cam_manage_config_deploy.ini"
# CONFIG_FILE = "cam_manage_config_test.ini"


config = configparser.ConfigParser()
config.read(CONFIG_FILE)

TOTAL_RECORD_TIME_SEC = 60

save_loc = './cam_record'

##########################################################
# Save frames

cam_addr = '172.21.20.109'

# Note | assumes that all cameras have same password and username
cam_user = str(config['CAMERA_DEVICE']['uname'])
cam_pass = str(config['CAMERA_DEVICE']['pass'])
secs_bw_frames = float(config['CAMERA_DEVICE']['secs_bw_frames'])


ipcam = IPCam(cam_addr, cam_user, cam_pass, 1)
# ipcam.start()


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

        frame = ipcam.get_next_frame()
        # print(frame)
        cv2.imwrite(str(save_loc) + '/' + str(frame_num) + ".jpg", frame)

        frame_num = frame_num + 1
        # print(time.time() - s)

    # print('stopping')
    ipcam.stop()



