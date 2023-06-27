import ssl
import torch
from IPython.core.debugger import set_trace
import glob
# import re
import math
import cv2
import numpy as np
import scipy.spatial as spatial
import scipy.cluster as cluster
from collections import defaultdict
from statistics import mean
import easyocr
import rectangleFunction as rf
import json


classes = ["AC_Source", "BJT", "Battery", "Capacitor", "Current_Source", "DC_Source", "Dep_Current_Source", "Dep_DC_Source",
           "Diode", "Ground", "Inductor", "MOSFET", "Node", "Opamp", "Resistor", "Resistor_Box", "Voltage_Source", "Zener_Diode", "object"]


class Node:
    def __init__(self, x, y, img, nodeID, name=""):
        self.name = name
        self.img = img
        self.nodeID = nodeID
        self.x = x
        self.y = y

        self.right = self.setRight()
        self.left = self.setLeft()
        self.up = self.setUp()
        self.down = self.setDown()

    def numberOfOut(self):
        return self.left + self.right + self.up + self.down

    def setRight(self):
        values = self.img[self.y-5:self.y+5, self.x:self.x+15]
        numberOfWhitePixels = list(values.flatten()).count(255)
        return numberOfWhitePixels >= 15

    def setLeft(self):
        values = self.img[self.y-5:self.y+5, self.x-15:self.x]
        numberOfWhitePixels = list(values.flatten()).count(255)
        return numberOfWhitePixels >= 15

    def setUp(self):
        values = self.img[self.y-15:self.y, self.x-5:self.x+5]
        numberOfWhitePixels = list(values.flatten()).count(255)
        return numberOfWhitePixels >= 15

    def setDown(self):
        values = self.img[self.y:self.y+15, self.x-5:self.x+5]
        numberOfWhitePixels = list(values.flatten()).count(255)
        return numberOfWhitePixels >= 15

    def isEdge(self):

        # is an edge if more than 2 outs
        if self.numberOfOut() > 2:
            return True
        elif self.numberOfOut() < 2:
            return False

        # either only when horizontal or vertical outs exist

        h = (self.left + self.right) == 1
        v = (self.up + self.down) == 1

        return h and v

    def toString(self):
        return f"name: {self.name}, x,y: {(self.x,self.y)}, lrud: {self.left}, {self.right}, {self.up}, {self.down}"

    def isInABox(self, bounding_boxes):

        for bb in bounding_boxes:
            left_top = bb.top_left_xy
            right_bottom = bb.bottom_right_xy
            cls = bb.classNo

            bb_id = bb.cmp_id

            x1, y1 = left_top
            x2, y2 = right_bottom

            x_node, y_node = self.x, self.y

            if x2 >= x_node >= x1 and y2 >= y_node >= y1:
                return True
        return False


class Component:
    def __init__(self, top_left_xy, bottom_right_xy, classNo, cmp_id, img, value='?'):
        self.cmp_id = cmp_id
        self.top_left_xy = top_left_xy
        self.bottom_right_xy = bottom_right_xy
        self.classNo = classNo
        self.img = img

        self.value = value
        # top and left connections are 1
        self.connection1 = None
        self.connection2 = None

        # if there are any connections vertically or horizontally

        self.horizontal = False
        self.vertical = False

        self.setComponentAxis()

    def setValue(self, value):
        self.value = value

    def setComponentAxis(self):

        x1, y1 = self.top_left_xy
        x2, y2 = self.bottom_right_xy

        leftValues = self.img[y1:y2, x1-15:x1]
        numberOfLeftWhitePixels = list(leftValues.flatten()).count(255)

        rightValues = self.img[y1:y2, x2:x2+15]
        numberOfRightWhitePixels = list(rightValues.flatten()).count(255)

        upValues = self.img[y1-15:y1, x1:x2]
        numberOfUpWhitePixels = list(upValues.flatten()).count(255)

        downValues = self.img[y2:y2+15, x1:x2]
        numberOfDownWhitePixels = list(downValues.flatten()).count(255)


#         horizontalPixels = abs(numberOfLeftWhitePixels - numberOfRightWhitePixels)
#         verticalPixels = abs(numberOfUpWhitePixels - numberOfDownWhitePixels)

        if numberOfLeftWhitePixels > numberOfUpWhitePixels:
            self.horizontal = True
        else:
            self.vertical = True

    #def toString(self):

        #print(
           # f"component id: {self.cmp_id}; x1,y1: {self.top_left_xy}; x2,y2: {self.bottom_right_xy}; class = {classes[self.classNo]} h:{self.horizontal} v:{self.vertical} ")


class Circuit:

    def __init__(self, componentList, nodeList, texts):
        self.componentList = componentList
        self.nodeList = nodeList
        self.texts = texts

        self.clearNoneNodes()
        self.nodeRevisedList = {}

        self.setSameNodes()
        # print(self.nodeRevisedList)

        self.setComponentConnections()
        self.connectValuesToComponents()
        self.generateNetlist()

    def connectValuesToComponents(self):

        for text in self.texts:
            top, bottom = text["coordinate"]

            x1, y1 = top
            x2, y2 = bottom

            midPointX = (x1+x2)//2
            midPointY = (y1+y2)//2

            minDist = 1000000
            index = 0

            for i, component in enumerate(self.componentList):
                cx1, cy1 = component.top_left_xy
                cx2, cy2 = component.bottom_right_xy

                cMidPointX = (cx1+cx2)//2
                cMidPointY = (cy1+cy2)//2

                dist = ((cMidPointX-midPointX)**2 +
                        (cMidPointY-midPointY)**2)**0.5

                if dist < minDist:
                    minDist = dist
                    index = i

#            self.componentList[index].toString()
            self.componentList[index].value = text['text']
    
    def generateNetlist(self):
        text = ""
        for component in self.componentList:
            row = f"{classes[component.classNo]}{component.cmp_id} {component.connection1} {component.connection2} {component.value}"
            print(row)
            text += row+ "\n"
        return text
       

    def setComponentConnections(self):

        for component in self.componentList:
            # set_trace()

            x1, y1 = component.top_left_xy
            x2, y2 = component.bottom_right_xy

            # print(f":::::::::::::::::::::::::::::-{component.cmp_id} , {component.horizontal} {component.vertical}")
            if component.horizontal:
                leftNodes = []
                rightNodes = []

                for node in self.nodeList:
                    # print(f":::::::::::::::::::::::::::::-{component.cmp_id} , {node.toString()} {component.vertical}")
                    if y2 >= node.y >= y1 and node.x < x1:
                        leftNodes.append(node)
                    if y2 >= node.y >= y1 and node.x > x2:
                        rightNodes.append(node)

                leftNodes.sort(key=lambda n: n.x, reverse=True)

                if len(leftNodes) != 0:
                    component.connection1 = self.nodeRevisedList[leftNodes[0].nodeID]

                rightNodes.sort(key=lambda n: n.x)
                if len(rightNodes) != 0:
                    component.connection2 = self.nodeRevisedList[rightNodes[0].nodeID]

            elif component.vertical:
                upNodes = []
                downNodes = []

                for node in self.nodeList:
                    if x2 >= node.x >= x1 and node.y < y1:
                        upNodes.append(node)
                    if x2 >= node.x >= x1 and node.y > y2:
                        downNodes.append(node)

                upNodes.sort(key=lambda n: n.y, reverse=True)

                if len(upNodes) != 0:
                    component.connection1 = self.nodeRevisedList[upNodes[0].nodeID]

                downNodes.sort(key=lambda n: n.y)
                if len(downNodes) != 0:

                    component.connection2 = self.nodeRevisedList[downNodes[0].nodeID]

    def clearNoneNodes(self):
        newNodes = []

        for node in self.nodeList:

            x, y = node.x, node.y

            if not node.isInABox(self.componentList) and node.isEdge():
                newNodes.append(node)
        self.nodeList = newNodes

    def setSameNodes(self):
        letterName = 'Z'

        for node in self.nodeList:
            #print(f"for node : {node.toString()}")
            #{3: 9, 21: 2, 1: 3, 9: 3, 19: 26, 24: 10, 4: 19, 26: 27, 2: 21, 30: 32, 10: 24, 25: 26, 27: 26, 29: 30, 32: 34, 23: 30, 34: 35, 35: 34}

            if node.nodeID not in self.nodeRevisedList.keys():
                letterName = rf.next_alpha(letterName)
                self.nodeRevisedList[node.nodeID] = letterName

            leftN = self.getLeftNeighborNode(node)
            rightN = self.getRightNeighborNode(node)
            upN = self.getUpNeighborNode(node)
            downN = self.getDownNeighborNode(node)

            if node.left and leftN != None:

                if not self.componentExistsBetweenNodes(node, leftN):
                    # print(f"{leftN.toString()} ----> {node.toString()}")

                    self.nodeRevisedList[leftN.nodeID] = self.nodeRevisedList[node.nodeID]

            if node.right and rightN != None:
                if not self.componentExistsBetweenNodes(node, rightN):
                    # print(f"{rightN.toString()} ----> {node.toString()}")
                    self.nodeRevisedList[rightN.nodeID] = self.nodeRevisedList[node.nodeID]

            if node.up and upN != None:
                if not self.componentExistsBetweenNodes(node, upN):
                    # print(f"{upN.toString()} ----> {node.toString()}")
                    self.nodeRevisedList[upN.nodeID] = self.nodeRevisedList[node.nodeID]

                    #upN.name = node.name

            if node.down and downN != None:
                if not self.componentExistsBetweenNodes(node, downN):
                    # print(f"{downN.toString()} ----> {node.toString()}")
                    self.nodeRevisedList[downN.nodeID] = self.nodeRevisedList[node.nodeID]

                    #downN.name = node.name

    def getLeftNeighborNode(self, node):

        leftNodes = []

        x = node.x
        y = node.y

        # get all the nodes that are on the left and the same row

        for n in self.nodeList:
            if n.name == node.name:
                continue
            # if the node we are looking for is in the same y and has a smaller x
            if y-5 < n.y < y+5 and n.x < x:
                leftNodes.append(n)

        # sort by the closeness to the node
        leftNodes.sort(key=lambda n: n.x, reverse=True)

        if len(leftNodes) == 0:
            return None
        return leftNodes[0]

    def getRightNeighborNode(self, node):

        rightNodes = []

        x = node.x
        y = node.y

        # get all the nodes that are on the right and the same row

        for n in self.nodeList:
            if n.name == node.name:
                continue
            # if the node we are looking for is in the same y and has a greater x
            if y-5 < n.y < y+5 and n.x > x:
                rightNodes.append(n)

        # sort by the closeness to the node
        rightNodes.sort(key=lambda n: n.x)
        if len(rightNodes) == 0:
            return None
        return rightNodes[0]

    def getUpNeighborNode(self, node):
        upNodes = []

        x = node.x
        y = node.y

        # get all the nodes that are on the up and the same cloumn
        for n in self.nodeList:
            if n.name == node.name:
                continue
            # if the node we are looking for is in the same x and has a smaller y
            if x-5 < n.x < x+5 and n.y < y:
                upNodes.append(n)

        # sort by the closeness to the node
        upNodes.sort(key=lambda n: n.y, reverse=True)

        if len(upNodes) == 0:
            return None
        return upNodes[0]

    def getDownNeighborNode(self, node):

        downNodes = []

        x = node.x
        y = node.y

        # get all the nodes that are on the down and the same cloumn

        for n in self.nodeList:
            if n.name == node.name:
                continue
            # if the node we are looking for is in the same x and has a smaller y
            if x-5 < n.x < x+5 and n.y > y:
                downNodes.append(n)

        # sort by the closeness to the node
        downNodes.sort(key=lambda n: n.y)
        if len(downNodes) == 0:
            return None
        return downNodes[0]

    def componentExistsBetweenNodes(self, node1, node2):
        if abs(node1.x - node2.x) < 5:
            for component in self.componentList:
                x1, y1 = component.top_left_xy
                x2, y2 = component.bottom_right_xy

                if x1 < node1.x < x2 and (node2.y > y1 > node1.y or node1.y > y1 > node2.y):
                    return True
            return False
        else:
            for component in self.componentList:

                x1, y1 = component.top_left_xy
                x2, y2 = component.bottom_right_xy

                if y2 > node1.y > y1 and (node2.x > x1 > node1.x or node1.x > x1 > node2.x):
                    return True
            return False

    def drawCircuit(self, img):

        for component in self.componentList:

            x1, y1 = component.top_left_xy
            x2, y2 = component.bottom_right_xy
            # uncomment
            cv2.rectangle(img, (x1, y1), (x2, y2), (0, 0, 255), 2)
#             cv2.putText(img,f"{component.cmp_id}", (x1+10,y1-15), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,0,0))

        for node in self.nodeList:
            x, y = node.x, node.y
            nodeID = node.nodeID

            img = cv2.circle(img, (x, y), 5, (255, 100, 0), -1)
            # uncomment
            img = cv2.putText(img, f"{self.nodeRevisedList[node.nodeID]}", (
                x-15, y-3), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0))

        # cv2.imwrite('last.jpg',img)
        
