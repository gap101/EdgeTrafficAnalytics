import cv2
import os
import pexpect
from ConsumerBase import ConsumerBase
# class YoloSingleton():
#     class __Yolo(ConsumerBase):


class Yolo(ConsumerBase):
    def __init__(self, threshold):

        darknet = "./darknet detect cfg/yolov3.cfg yolov3.weights -thresh {} ".format(threshold)

        self.child = pexpect.spawn(darknet)

        # Initial expect required
        self.child.expect("Enter Image Path:")        


    def performTraining(self):
        print("No training required")


    def performDetection(self, image):
        saved_image = cv2.imwrite("holder.jpg", image)

        self.child.sendline("holder.jpg")

        # vehicles, pedestrians = self.get_count(self.child.before.decode())

        # print("Count: ", (vehicles, pedestrians))

        self.child.expect("Enter Image Path:")
        count = self.get_count(self.child.before.decode())

        os.system("rm holder.jpg")
        
        # Tuple containing number of vehicles in 0th index and number of pedestrians
        # in 1st index
        return count

    def frame_consume(self, image, frame_id, time):
        return self.performDetection(image)


    def get_count(self, yolo_output):
        '''
        Returns the count for cars and pedestrians detected by yolo
        yolo_output: String output obtained from yolo
        '''
        vehicles = 0
        pedestrians = 0

        print(yolo_output)

        parts = yolo_output.split("\n")
        for part in parts:
            print(part)

            # Check if it detected a vehicle
            if "car" in part or "truck" in part:
                vehicles += 1
            elif "person" in part:
                pedestrians += 1

        return vehicles, 0, pedestrians

    def complete(self):
        print("yolo consumer - complete")

    def start(self):
        print("yolo consumer - start")

    def str_id(self):
        return "yolo consumer"
