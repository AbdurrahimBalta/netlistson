from fastapi import FastAPI, File
from segmentation import get_yolov5, get_image_from_bytes
from starlette.responses import Response
import io
from PIL import Image
import json
from fastapi.middleware.cors import CORSMiddleware
import ssl
import torch
from IPython.core.debugger import set_trace
import glob
# import re5
import math
import cv2
import numpy as np
import scipy.spatial as spatial
import scipy.cluster as cluster
from collections import defaultdict
from statistics import mean
import easyocr
import rectangleFunction as rf
import netlistFunction as nf


model = get_yolov5()

app = FastAPI(
    title="Netlist Generator API",
    description="""Obtain object value out of image
                    and return image and json result""",
    version="0.0.1",
)

origins = [
    "http://localhost",
    "http://localhost:8000",
    "*"
]
@app.get('/')
def docsa_bak():
    
    return dict(HasanGurbuz='Url karistirma docstan kontrol et karşim')


app.add_middleware(
    #hangi domainlerden istek gideceğini soran ve hepsine izin veren mekanizma
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get('/notify/v1/health')
def get_health():
    
    return dict(msg='OK')


@app.post("/object-to-json")
async def detect_component_return_json_result(file: bytes = File(...)):
    input_image = get_image_from_bytes(file)
    results = model(input_image.copy())
    detect_res = results.pandas().xyxy[0].to_json(orient="records")  # JSON img1 predictions
    detect_res = json.loads(detect_res)
    return {"result": detect_res}


@app.post("/object-to-img")
async def detect_component_return_base64_img(file: bytes = File(...)):
    input_image = get_image_from_bytes(file)
    results = model(input_image.copy())
    results.render()  # updates results.imgs with boxes and labels
    for img in results.ims:
        bytes_io = io.BytesIO()
        img_base64 = Image.fromarray(img)
        img_base64.save(bytes_io, format="jpeg")
    return Response(content=bytes_io.getvalue(), media_type="image/jpeg")


@app.post("/object-to-netlist")
async def detect_component_netlist(file: bytes = File(...)):
    input_image = get_image_from_bytes(file)
    results = model(input_image.copy())
    threshold = 80
    min_line_length = 0
    max_line_gap = 0

    img = get_image_from_bytes(file)
    org_img = img.copy()

    texts = []

    
    reader = easyocr.Reader(['en'])
    result = reader.readtext(img)

    # replace it with white
    for detection in result:
        top_left = tuple([int(val) for val in detection[0][0]])
        bottom_right = tuple([int(val) for val in detection[0][2]])
        text = detection[1]
        if "S" in text:
            text = text.replace("S", "5")

        font = cv2.FONT_HERSHEY_SCRIPT_SIMPLEX
        img = cv2.rectangle(img, top_left, bottom_right, (255, 255, 255), -1)
        text_dict = {"text": text, "coordinate": (top_left, bottom_right)}
        texts.append(text_dict)
    #img = cv2.putText(img,text,top_left,4,.6,(55,55,55),1,cv2.LINE_AA)


    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 300, 200)
    #Detect points that form a line

    lines = cv2.HoughLines(edges, 1, np.pi / 180, threshold,
                       min_line_length, max_line_gap)
    lines = np.reshape(lines, (-1, 2))


# get intersection points of the lines
    h_lines, v_lines = rf.h_v_lines(lines)
    intersection_points = rf.line_intersections(h_lines, v_lines)
    points = rf.cluster_points(intersection_points)


    bounding_boxes = []
    nodes = []
    components = []


    cmp_id = 0
    
    for bb in results.xyxy[0]:
        x1, y1 = int(bb[0]), int(bb[1])
        x2, y2 = int(bb[2]), int(bb[3])
        acc = round(float(bb[4]), 2)
        cls = int(bb[5])

        if cls == 12 or cls == 9:
            continue
        component = nf.Component((x1, y1), (x2, y2), cls, cmp_id, edges)
        components.append(component)
        #component.toString()
        bounding_boxes.append(((x1, y1), (x2, y2), cls))

        cmp_id += 1


    c = 1
# loop through the points
    for point in points:
        x, y = point
        x = int(x)
        y = int(y)
        node = nf.Node(x, y, edges, c, name=c)
        nodes.append(node)

        c += 1
    circuit = nf.Circuit(components, nodes, texts)


    #plot_curcuit = circuit.drawCircuit(org_img)
    
    x = circuit.generateNetlist()
  
    

    return x