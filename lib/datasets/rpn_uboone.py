# faster rcnn for uboone

import os
from datasets.imdb import imdb
import datasets.ds_utils as ds_utils
import xml.etree.ElementTree as ET
import numpy as np
import scipy.sparse
import scipy.io as sio
import utils.cython_bbox
import cPickle
import subprocess
import uuid

from fast_rcnn.config import cfg

class rpn_uboone(imdb):
    def __init__(self, image_set, devkit_path=None):
        imdb.__init__(self, 'rpn_uboone_' + image_set)
    
        self._image_set = image_set
        self._devkit_path = self._get_default_path() if devkit_path is None \
                            else devkit_path
        
        self._data_path = self._devkit_path
        print cfg
        self._classes = ('__background__',
                         'eminus','proton','pizero','muminus') # should read this from config
        self._class_to_ind = dict(zip(self.classes, xrange(self.num_classes)))
        self._image_ext   = '.JPEG'
        self._image_index = self._load_image_set_index()
        
        # Default to roidb handler
        self._roidb_handler = self.selective_search_roidb
        self._salt = str(uuid.uuid4())
        self._comp_id = 'comp4'

        # UBOONE specific config options
        self.config = {'use_salt'    : True,
                       'rpn_file'    : None,
                       'min_size'    : 2} # minimum box size
        
        assert os.path.exists(self._devkit_path), \
                'rpn_uboone path does not exist: {}'.format(self._devkit_path)
        assert os.path.exists(self._data_path), \
                'Path does not exist: {}'.format(self._data_path)

    def image_path_at(self, i):
        """
        Return the absolute path to image i in the image sequence.
        """
        return self.image_path_from_index(self._image_index[i])

    def image_path_from_index(self, index):
        """
        Construct an image path from the image's "index" identifier.
        """
        image_path = os.path.join(self._data_path, 'JPEGImages',
                                  index + self._image_ext)
        assert os.path.exists(image_path), \
                'Path does not exist: {}'.format(image_path)
        return image_path

    def _load_image_set_index(self):
        """
        Load the indexes listed in this dataset's image set file.
        """
        image_set_file = os.path.join(self._data_path, 'ImageSets', 'Main',
                                      self._image_set + '.txt')
        assert os.path.exists(image_set_file), \
            'Path does not exist: {}'.format(image_set_file)
        with open(image_set_file) as f:
            image_index = [x.strip() for x in f.readlines()]
            return image_index

    def _get_default_path(self):
        """
        Return the default path where Singlesdevikit is expected to be installed.
        """
        return os.path.join(cfg.DATA_DIR, 'Singlesdevkit')

    def gt_roidb(self): # can this become ROOT ?
        """
        Return the database of ground-truth regions of interest.

        This function loads/saves from/to a cache file to speed up future calls.
        """
        cache_file = os.path.join(self.cache_path, self.name + '_gt_roidb.pkl')
        if os.path.exists(cache_file):
            with open(cache_file, 'rb') as fid:
                roidb = cPickle.load(fid)
            print '{} gt roidb loaded from {}'.format(self.name, cache_file)
            return roidb

        gt_roidb = [self._load_uboone_annotation(index)
                    for index in self.image_index]
        with open(cache_file, 'wb') as fid:
            cPickle.dump(gt_roidb, fid, cPickle.HIGHEST_PROTOCOL)
        print 'wrote gt roidb to {}'.format(cache_file)

        return gt_roidb

    def selective_search_roidb(self):
        print "\t Hey vic I was called, don't delete me! __selective_search__"
        """
        Return the database of selective search regions of interest.
        Ground-truth ROIs are also included.

        This function loads/saves from/to a cache file to speed up future calls.
        """
        cache_file = os.path.join(self.cache_path,
                                  self.name + '_selective_search_roidb.pkl')

        if os.path.exists(cache_file):
            with open(cache_file, 'rb') as fid:
                roidb = cPickle.load(fid)
            print '{} ss roidb loaded from {}'.format(self.name, cache_file)
            return roidb

        if self._image_set != 'test':
            gt_roidb = self.gt_roidb()
            ss_roidb = self._load_selective_search_roidb(gt_roidb)
            roidb    = imdb.merge_roidbs(gt_roidb, ss_roidb)
        else:
            roidb = self._load_selective_search_roidb(None)
        with open(cache_file, 'wb') as fid:
            cPickle.dump(roidb, fid, cPickle.HIGHEST_PROTOCOL)
        print 'wrote ss roidb to {}'.format(cache_file)

        return roidb

        
    def rpn_roidb(self):
    
        print "\t Hey vic I was called, don't delete me! __rpn_roidb__"

        if self._image_set != 'test':
            gt_roidb  = self.gt_roidb()
            rpn_roidb = self._load_rpn_roidb(gt_roidb)
            roidb     = imdb.merge_roidbs(gt_roidb, rpn_roidb)
        else:
            roidb = self._load_rpn_roidb(None)

        return roidb
        
    #### NOT SURE IF THIS IS CALLED
    def _load_rpn_roidb(self, gt_roidb):
        filename = self.config['rpn_file']
        print 'loading {}'.format(filename)
        assert os.path.exists(filename), \
               'rpn data not found at: {}'.format(filename)
        with open(filename, 'rb') as f:
            box_list = cPickle.load(f)
        return self.create_roidb_from_box_list(box_list, gt_roidb)

    ### NOT SURE IF THIS IS CALLED
    def _load_selective_search_roidb(self, gt_roidb):
        filename = os.path.abspath(os.path.join(cfg.DATA_DIR,
                                                'selective_search_data',
                                                self.name + '.mat'))
        assert os.path.exists(filename), \
               'Selective search data not found at: {}'.format(filename)

        raw_data = sio.loadmat(filename)['boxes'].ravel()

        box_list = []

        for i in xrange(raw_data.shape[0]):
            boxes = raw_data[i][:, (1, 0, 3, 2)]
            keep  = ds_utils.unique_boxes(boxes)
            
            boxes = boxes[keep, :]
            keep  = ds_utils.filter_small_boxes(boxes, self.config['min_size'])
            
            boxes = boxes[keep, :]
            
            box_list.append(boxes)

        return self.create_roidb_from_box_list(box_list, gt_roidb)


    def _load_uboone_annotation(self, index):
        """
        Load image and bounding boxes info from TXT file in the UBOONE
        format.
        """
        filename = os.path.join(self._data_path, 'Annotations', index + '.txt') # will be text file instead of xml
        
        # just load text file instead
        tree = ET.parse(filename)
        objs = tree.findall('object')
        
        num_objs = len(objs)

        boxes      = np.zeros((num_objs, 4), dtype=np.uint16)
        gt_classes = np.zeros((num_objs), dtype=np.int32)
        overlaps   = np.zeros((num_objs, self.num_classes), dtype=np.float32)
        
        # "Seg" area for uboone is just the box area -- what is this?
        seg_areas = np.zeros((num_objs), dtype=np.float32)

        # Load object bounding boxes into a data frame -- what dataframe?
        for ix, obj in enumerate(objs):
            bbox = obj.find('bndbox')
            # Make pixel indexes 0-based, like ub and imagenet
            x1 = float(bbox.find('xmin').text)
            y1 = float(bbox.find('ymin').text)
            x2 = float(bbox.find('xmax').text)
            y2 = float(bbox.find('ymax').text)
            

            cls = self._class_to_ind[obj.find('name').text.lower().strip()]
            boxes[ix, :]    = [x1, y1, x2, y2]

            gt_classes[ix]  = cls
            
            overlaps[ix, cls] = 1.0

            seg_areas[ix] = (x2 - x1 + 1) * (y2 - y1 + 1)

        overlaps = scipy.sparse.csr_matrix(overlaps)

        return {'boxes'       : boxes,
                'gt_classes'  : gt_classes,
                'gt_overlaps' : overlaps,
                'flipped'     : False,
                'seg_areas'   : seg_areas}

    def _get_comp_id(self):
        comp_id = (self._comp_id + '_' + self._salt if self.config['use_salt']
            else self._comp_id)

        return comp_id


if __name__ == '__main__':
    from datasets.rpn_uboone import rpn_uboone

    d = rpn_uboone('trainval') #no choice yet, must trainval
    res = d.roidb
    
    from IPython import embed; embed()
