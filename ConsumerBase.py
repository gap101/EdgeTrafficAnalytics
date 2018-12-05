from abc import ABC, abstractmethod


class ConsumerBase(ABC):

    @abstractmethod
    def frame_consume(self, frame, cam_id):
        pass

    @abstractmethod
    def complete(self):
        pass

    @abstractmethod
    def start(self):
        pass

    @abstractmethod
    def str_id(self):
        pass