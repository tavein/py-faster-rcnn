# --------------------------------------------------------
# Fast R-CNN
# Copyright (c) 2015 Microsoft
# Licensed under The MIT License [see LICENSE for details]
# Written by Ross Girshick
# --------------------------------------------------------

"""Blob helper functions."""

from fast_rcnn.config import cfg
import numpy as np
import cv2
import time

def im_list_to_blob(ims):
    """Convert a list of images into a network input.

    Assumes images are already prepared (means subtracted, BGR order, ...).
    """
    max_shape = np.array([im.shape for im in ims]).max(axis=0)
    num_images = len(ims)
    blob = np.zeros((num_images, max_shape[0], max_shape[1], cfg.NCHANNELS),
                    dtype=np.float32)
    for i in xrange(num_images):
        im = ims[i]
        blob[i, 0:im.shape[0], 0:im.shape[1], :] = im
    # Move channels (axis 3) to axis 1
    # Axis order will become: (batch elem, channel, height, width)
    channel_swap = (0, 3, 1, 2)
    blob = blob.transpose(channel_swap)
    return blob

def prep_im_for_blob(im, pixel_means, target_size, max_size):
    """Mean subtract and scale an image for use in a blob."""
    im = im.astype(np.float32, copy=False)
    im -= pixel_means
    # print "{}".format(im)
    # time.sleep(10)
    im_shape = im.shape
    im_size_min = np.min(im_shape[0:2])
    im_size_max = np.max(im_shape[0:2])
    
    im_scale = float(target_size) / float(im_size_min)
    
    # Prevent the biggest axis from being more than MAX_SIZE
    if np.round(im_scale * im_size_max) > max_size:
        im_scale = float(max_size) / float(im_size_max)
    
    # no need to resize...
    print "resizing im_shape : {} im_size_min {} im_size_max {} im_scale : {}".format(im_shape,
                                                                                      im_size_min,
                                                                                      im_size_max,
                                                                                      im_scale)
    # #INTER_LINEAR - a bilinear interpolation (used by default)
    # im = cv2.resize(im, None, None, fx=im_scale, fy=im_scale,
    #                 interpolation=cv2.INTER_LINEAR)

    print "after resize im.shape {} and im_scale {}".format(im.shape,im_scale)

    return im, im_scale
