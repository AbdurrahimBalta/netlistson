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


# h_v_lines fonksiyonu, girdi olarak verilen çizgileri yatay ve dikey olarak ayırır.
# rho ve theta houglines parametreleridir piksel ve dereceye eşittir


def h_v_lines(lines):
    h_lines, v_lines = [], []
    for rho, theta in lines:
        if theta < np.pi / 4 or theta > np.pi - np.pi / 4:
            v_lines.append([rho, theta])
        else:
            h_lines.append([rho, theta])
    return h_lines, v_lines

# line_intersections fonksiyonu, yatay ve dikey çizgilerin kesişim noktalarını hesaplar.


def line_intersections(h_lines, v_lines):
    points = []
    for r_h, t_h in h_lines:
        for r_v, t_v in v_lines:
            a = np.array([[np.cos(t_h), np.sin(t_h)],
                         [np.cos(t_v), np.sin(t_v)]])
            b = np.array([r_h, r_v])
            inter_point = np.linalg.solve(a, b)
            points.append(inter_point)
    return np.array(points)

# cluster_points fonksiyonu, girdi olarak verilen noktaları kümelere ayırır ve her küme için ortalama koordinatlarını hesaplar.


def cluster_points(points):
    dists = spatial.distance.pdist(points)
    single_linkage = cluster.hierarchy.single(dists)
    flat_clusters = cluster.hierarchy.fcluster(single_linkage, 15, 'distance')
    cluster_dict = defaultdict(list)
    for i in range(len(flat_clusters)):
        cluster_dict[flat_clusters[i]].append(points[i])
    cluster_values = cluster_dict.values()
    clusters = map(lambda arr: (np.mean(np.array(arr)[:, 0]), np.mean(
        np.array(arr)[:, 1])), cluster_values)
    return sorted(list(clusters), key=lambda k: [k[1], k[0]])

# isInsideBox fonksiyonu, bir koordinatın bir kutu içinde olup olmadığını denetler.


def isInsideBox(bounding_box, node_coordinate):

    left_top, right_bottom, cls = bounding_box
#     if cls == 12:
#         return False
    x1, y1 = left_top
    x2, y2 = right_bottom

    x_node, y_node = node_coordinate

    return x2 >= x_node >= x1 and y2 >= y_node >= y1


def next_alpha(s):
    return chr((ord(s.upper())+1 - 65) % 26 + 65)
