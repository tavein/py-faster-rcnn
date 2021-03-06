#!/usr/bin/env python

# --------------------------------------------------------
# Faster R-CNN
# Copyright (c) 2015 Microsoft
# Licensed under The MIT License [see LICENSE for details]
# Written by Ross Girshick
# --------------------------------------------------------

"""
Demo script showing detections in sample images.

See README.md for installation instructions before running.
"""

import _init_paths
from fast_rcnn.config import cfg
import numpy as np
import sys

cfg.ROOTFILES   = ["/stage2/drinkingkazu/brett/nu_val.root"]

CLASSES = ('__background__',
           'neutrino')

cfg.PIXEL_MEANS =  [[[ 0.0 ]]]
cfg.IMAGE2DPROD = "tpc"
cfg.ROIPROD = "tpc"
#cfg.HEIGHT= 756
#cfg.WIDTH = 864
cfg.WIDTH = 756
cfg.HEIGH = 864
cfg.DEVKIT = "NuDevKitv04_brett"
cfg.IMAGE_LOADER = "BNBNuv04Loader"
cfg.RNG_SEED= 9
cfg.DEBUG = False
cfg.NCHANNELS = 1
cfg.IMIN = 0.5
cfg.IMAX = 10.0
cfg.HAS_RPN = True
cfg.SCALES = [756]
cfg.MAX_SIZE = 864
cfg.IOCFG = sys.argv[1]

from fast_rcnn.test import im_detect, rh
from fast_rcnn.nms_wrapper import nms
from utils.timer import Timer

import caffe, os, sys, cv2
import argparse
from ROOT import larcv

larcv.load_pyutil

import numpy as np

NETS = { 'rpn_uboone': ('resnet50_nu',
                        sys.argv[2]) }


def vis_detections(im, class_name, dets, image_name, thresh=0.5):
    """Draw detected bounding boxes."""
    
    inds = np.where(dets[:, -1] >= thresh)[0]

    if len(inds) == 0:
        print "No detections on {}".format(image_name)
        return
    
    for i in inds:
        bbox  = dets[i, :4]
        score = dets[i, -1]
        out = open("resnet_inference/resnet_dets_nu_{}.txt".format(sys.argv[2].split("/")[-1]),"a")
        out.write("{} {} {} {} {} {}\n".format(image_name,
                                               score,
                                               bbox[0],
                                               bbox[1],
                                               bbox[2],
                                               bbox[3]))

    out.close()

    
def demo(net, image_name):
    """Detect object classes in an image using pre-computed object proposals."""

    im = rh.get_image(int(image_name))

    scores, boxes = im_detect(net, int(image_name), im=im)

    # Visualize detections for each class
    CONF_THRESH = 0.0 # 0.5
    NMS_THRESH = 0.3
    for cls_ind, cls in enumerate(CLASSES[1:]):
        cls_ind += 1 # because we skipped background
        cls_boxes = boxes[:, 4*cls_ind:4*(cls_ind + 1)]
        cls_scores = scores[:, cls_ind]
        dets = np.hstack((cls_boxes,
                          cls_scores[:, np.newaxis])).astype(np.float32)

        keep = nms(dets, NMS_THRESH)
        dets = dets[keep, :]
        vis_detections(im, cls, dets, image_name,thresh=CONF_THRESH)

if __name__ == '__main__':
    cfg.TEST.HAS_RPN = True  # Use RPN for proposals

    cfg.MODELS_DIR = '/home/vgenty/segment/py-faster-rcnn/models/rpn_uboone'

    prototxt = os.path.join(cfg.MODELS_DIR, NETS['rpn_uboone'][0],
                            'faster_rcnn_end2end', 'test.prototxt')

    caffemodel = os.path.join(NETS['rpn_uboone'][1])
    
    #/home/vgenty/py-faster-rcnn/output/faster_rcnn_alt_opt/rpn_uboone_train_5
    if not os.path.isfile(caffemodel):
        raise IOError(('{:s} not found.\nDid you run ./data/script/'
                       'fetch_faster_rcnn_models.sh?').format(caffemodel))

    caffe.set_mode_gpu()
    caffe.set_device(0)
    cfg.GPU_ID = 0

    net = caffe.Net(prototxt, caffemodel, caffe.TEST)

    print '\n\nLoaded network {:s}'.format(caffemodel)

    im_names = range(1000)
    #im_names = range(1)
    
    for im_name in im_names:
        print '~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~'
        print 'Demo for data/demo/{}'.format(im_name)
        demo(net, im_name)
