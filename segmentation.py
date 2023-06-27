import torch
from PIL import Image
import io

def get_yolov5():
    # local best.pt
    model = torch.hub.load('ultralytics/yolov5', 'custom',
                      path='model/best_V2.pt', force_reload=True,skip_validation=True) 
  # local repo
    model.conf = 0.6
    return model


import cv2
import numpy as np



def get_image_from_bytes(binary_image):
    nparr = np.frombuffer(binary_image, np.uint8)
    input_image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    return input_image

