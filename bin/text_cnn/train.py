#! /usr/bin/python
# -*- coding: utf-8 -*-
# @Time    : 2017/6/30 16:41
# @Author  : HouJP
# @Email   : houjp1992@gmail.com


import ConfigParser
import os
import sys
import time

from ..evaluation import F
from ..utils import DataUtil, LogUtil
import data_helpers


def init_out_dir(config):
    # generate output tag
    out_tag = time.strftime("%Y-%m-%d_%H-%M-%S", time.localtime(time.time()))
    config.set('DIRECTORY', 'out_tag', str(out_tag))
    # generate output directory
    out_pt = config.get('DIRECTORY', 'out_pt')
    out_pt_exists = os.path.exists(out_pt)
    if out_pt_exists:
        LogUtil.log("ERROR", 'out path (%s) already exists ' % out_pt)
        raise Exception
    else:
        os.mkdir(out_pt)
        os.mkdir(config.get('DIRECTORY', 'pred_pt'))
        os.mkdir(config.get('DIRECTORY', 'model_pt'))
        os.mkdir(config.get('DIRECTORY', 'conf_pt'))
        os.mkdir(config.get('DIRECTORY', 'score_pt'))
        LogUtil.log('INFO', 'out path (%s) created ' % out_pt)
    # save config
    config.write(open(config.get('DIRECTORY', 'conf_pt') + 'featwheel.conf', 'w'))


def train(config):
    version = config.get('TITLE_CONTENT_CNN', 'version')
    LogUtil.log('INFO', 'version=%s' % version)
    text_cnn = __import__('bin.text_cnn.%s.text_cnn' % version, fromlist=["*"])
    data_loader = __import__('bin.text_cnn.%s.data_loader' % version, fromlist=["*"])
    # init text cnn model
    model, word_embedding_index, char_embedding_index = text_cnn.init_text_cnn(config)
    # init directory
    init_out_dir(config)

    # load offline train dataset index
    train_index_off_fp = '%s/%s.offline.index' % (config.get('DIRECTORY', 'index_pt'),
                                                  config.get('TITLE_CONTENT_CNN', 'train_index_offline_fn'))
    train_index_off = DataUtil.load_vector(train_index_off_fp, 'int')
    train_index_off = [num - 1 for num in train_index_off]

    # load offline valid dataset index
    valid_index_off_fp = '%s/%s.offline.index' % (config.get('DIRECTORY', 'index_pt'),
                                                  config.get('TITLE_CONTENT_CNN', 'valid_index_offline_fn'))
    valid_index_off = DataUtil.load_vector(valid_index_off_fp, 'int')
    valid_index_off = [num - 1 for num in valid_index_off]

    # load valid dataset
    valid_dataset = data_loader.load_dataset_from_file(config,
                                                       'offline',
                                                       word_embedding_index,
                                                       char_embedding_index,
                                                       valid_index_off)

    # load train dataset
    part_id = 0
    part_size = config.getint('TITLE_CONTENT_CNN', 'part_size')
    valid_size = config.getint('TITLE_CONTENT_CNN', 'valid_size')
    batch_size = config.getint('TITLE_CONTENT_CNN', 'batch_size')
    for train_dataset in data_helpers.load_dataset_from_file_loop(config,
                                                                  'offline',
                                                                  word_embedding_index,
                                                                  char_embedding_index,
                                                                  train_index_off):
        LogUtil.log('INFO', 'part_id=%d, model training begin' % part_id)
        model.fit(train_dataset[:-1],
                  train_dataset[-1],
                  epochs=1,
                  batch_size=batch_size)
        if 0 == (((part_id + 1) * part_size) % valid_size):
            # predict for validation
            valid_preds = model.predict(valid_dataset[:-1], batch_size=32, verbose=True)
            LogUtil.log('INFO', 'prediction of validation data, shape=%s' % str(valid_preds.shape))
            F(valid_preds, valid_dataset[-1])
            # save model
            model_fp = config.get('DIRECTORY', 'model_pt') + 'text_cnn_%03d' % part_id
            model.save(model_fp)
        part_id += 1


if __name__ == '__main__':
    config_fp = sys.argv[1]
    config = ConfigParser.ConfigParser()
    config.read(config_fp)

    train(config)
