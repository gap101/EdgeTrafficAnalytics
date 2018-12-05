from ctypes import *
import cv2
import os
import math
import random
from ConsumerBase import ConsumerBase
import numpy as np



class BOX(Structure):
    _fields_ = [("x", c_float),
                ("y", c_float),
                ("w", c_float),
                ("h", c_float)]


class DETECTION(Structure):
    _fields_ = [("bbox", BOX),
                ("classes", c_int),
                ("prob", POINTER(c_float)),
                ("mask", POINTER(c_float)),
                ("objectness", c_float),
                ("sort_class", c_int)]


class IMAGE(Structure):
    _fields_ = [("w", c_int),
                ("h", c_int),
                ("c", c_int),
                ("data", POINTER(c_float))]


class METADATA(Structure):
    _fields_ = [("classes", c_int),
                ("names", POINTER(c_char_p))]


lib = CDLL("libdarknet.so", RTLD_GLOBAL)
lib.network_width.argtypes = [c_void_p]
lib.network_width.restype = c_int
lib.network_height.argtypes = [c_void_p]
lib.network_height.restype = c_int

predict = lib.network_predict
predict.argtypes = [c_void_p, POINTER(c_float)]
predict.restype = POINTER(c_float)

set_gpu = lib.cuda_set_device
set_gpu.argtypes = [c_int]

make_image = lib.make_image
make_image.argtypes = [c_int, c_int, c_int]
make_image.restype = IMAGE

get_network_boxes = lib.get_network_boxes
get_network_boxes.argtypes = [c_void_p, c_int, c_int, c_float, c_float, POINTER(c_int), c_int, POINTER(c_int)]
get_network_boxes.restype = POINTER(DETECTION)

make_network_boxes = lib.make_network_boxes
make_network_boxes.argtypes = [c_void_p]
make_network_boxes.restype = POINTER(DETECTION)

free_detections = lib.free_detections
free_detections.argtypes = [POINTER(DETECTION), c_int]

free_ptrs = lib.free_ptrs
free_ptrs.argtypes = [POINTER(c_void_p), c_int]

network_predict = lib.network_predict
network_predict.argtypes = [c_void_p, POINTER(c_float)]

reset_rnn = lib.reset_rnn
reset_rnn.argtypes = [c_void_p]

load_net = lib.load_network
load_net.argtypes = [c_char_p, c_char_p, c_int]
load_net.restype = c_void_p

do_nms_obj = lib.do_nms_obj
do_nms_obj.argtypes = [POINTER(DETECTION), c_int, c_int, c_float]

do_nms_sort = lib.do_nms_sort
do_nms_sort.argtypes = [POINTER(DETECTION), c_int, c_int, c_float]

free_image = lib.free_image
free_image.argtypes = [IMAGE]

letterbox_image = lib.letterbox_image
letterbox_image.argtypes = [IMAGE, c_int, c_int]
letterbox_image.restype = IMAGE

load_meta = lib.get_metadata
lib.get_metadata.argtypes = [c_char_p]
lib.get_metadata.restype = METADATA

load_image = lib.load_image_color
load_image.argtypes = [c_char_p, c_int, c_int]
load_image.restype = IMAGE

rgbgr_image = lib.rgbgr_image
rgbgr_image.argtypes = [IMAGE]

predict_image = lib.network_predict_image
predict_image.argtypes = [c_void_p, IMAGE]
predict_image.restype = POINTER(c_float)


class yolo_py_consumer_dual(ConsumerBase):

    def __init__(self):
        print("initied")
        start_img = cv2.imread("predictions.png")
        self.flow_mask = np.zeros(start_img.shape[:2], dtype=np.uint8)
        self.parked_mask = np.ones(start_img.shape[:2], dtype=np.uint8) * 255

        self.roi_corners_parked = np.array([[(103, 265), (105, 156), (120, 156),
                                    (176, 120), (187, 139), (244, 187),
                                    (478, 200), (479, 269)]], dtype=np.int32)

        cv2.drawContours(self.parked_mask, self.roi_corners_parked, -1, 0, -1)

        self.roi_corners_flow = np.array([[(0, 266), (0, 230), (68, 235), (90, 155), (115, 140),
                             (193, 131),(233, 168), (300, 200),
                             (479, 144), (477,267)]], dtype=np.int32)

        channel_count = start_img.shape[2]  # i.e. 3 or 4 depending on your image
        ignore_mask_color = (255,) * channel_count
        cv2.fillPoly(self.flow_mask, self.roi_corners_flow, ignore_mask_color)

    def frame_consume(self, frame, cam_id, time):

        parking_img = cv2.bitwise_and(frame, frame, mask=self.parked_mask)

        # print(len(frame))

        cv2.imwrite("holder.jpg", parking_img)

        # exit()

        detected_parking = self.detect(self.net, self.meta, b"holder.jpg")
        os.system("rm holder.jpg")

        # print(len(frame))


        flow_img = cv2.bitwise_and(frame, self.flow_mask)
        cv2.imwrite("holder.jpg", flow_img)
        # exit()
        detected_flow = self.detect(self.net, self.meta, b"holder.jpg")

        os.system("rm holder.jpg")

        # print(r)

        count = self.get_count(detected_parking, detected_flow)



        # Tuple containing number of vehicles in 0th index and number of pedestrians
        # in 1st index
        return count

    def get_count(self, yolo_output_park, yolo_output_flow):
        '''
        Returns the count for cars and pedestrians detected by yolo
        yolo_output: String output obtained from yolo
        '''
        vehicles_parked = 0
        vehicles_flow = 0
        pedestrians = 0

        print(yolo_output_park)

        for part in yolo_output_park:
            print(part)

            # Check if it detected a vehicle
            if b"car" in part or b"truck" in part:
                vehicles_parked += 1
            elif b"person" in part:
                pedestrians += 1

        print(yolo_output_flow)

        for part in yolo_output_flow:
            print(part)

            # Check if it detected a vehicle
            if b"car" in part or b"truck" in part:
                vehicles_flow += 1
            elif b"person" in part:
                pedestrians += 1


        return vehicles_parked, vehicles_flow, pedestrians

    def complete(self):
        print("done")

    def start(self):
        self.net = load_net(b"cfg/yolov3.cfg", b"yolov3.weights", 0)
        self.meta = load_meta(b"cfg/coco.data")




    def str_id(self):
        return ("yolo_py_dual_consumer")

    def sample(self, probs):
        s = sum(probs)
        probs = [a / s for a in probs]
        r = random.uniform(0, 1)
        for i in range(len(probs)):
            r = r - probs[i]
            if r <= 0:
                return i
        return len(probs) - 1

    def c_array(self, ctype, values):
        arr = (ctype * len(values))()
        arr[:] = values
        return arr

    def classify(self, net, meta, im):
        out = predict_image(net, im)
        res = []
        for i in range(meta.classes):
            res.append((meta.names[i], out[i]))
        res = sorted(res, key=lambda x: -x[1])
        return res

    def detect(self, net, meta, image, thresh=.5, hier_thresh=.5, nms=.45):
        im = load_image(image, 0, 0)
        num = c_int(0)
        pnum = pointer(num)
        predict_image(net, im)
        dets = get_network_boxes(net, im.w, im.h, thresh, hier_thresh, None, 0, pnum)
        num = pnum[0]
        if (nms): do_nms_obj(dets, num, meta.classes, nms);

        res = []
        for j in range(num):
            for i in range(meta.classes):
                if dets[j].prob[i] > 0:
                    b = dets[j].bbox
                    # print(b)
                    res.append((meta.names[i], dets[j].prob[i], (b.x, b.y, b.w, b.h)))
        res = sorted(res, key=lambda x: -x[1])
        free_image(im)
        free_detections(dets, num)
        return res

# if __name__ == "__main__":
# net = load_net("cfg/densenet201.cfg", "/home/pjreddie/trained/densenet201.weights", 0)
# im = load_image("data/wolf.jpg", 0, 0)
# meta = load_meta("cfg/imagenet1k.data")
# r = classify(net, meta, im)
# print r[:10]
# net = load_net(b"cfg/yolov3.cfg", b"yolov3.weights", 0)
# meta = load_meta(b"cfg/coco.data")
# r = detect(net, meta, b"data/dog.jpg")
# print (r)


