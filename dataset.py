#!/usr/bin/env python 
# -*- coding: utf-8 -*-
# @Time    : 2022/8/17 9:09
# @Author  : Joisen
# @File    : dataset.py

import json
import os

import torch.utils.data as data
from torch.utils.data import Dataset

from feature_extract_me import *


class HuDataset(Dataset):
    def __init__(self, file_dir):
        self.file_dir = file_dir
        self.file_path_list = []

        # 遍历文件夹获取所有文件的路径
        for root, dirs, files in os.walk(self.file_dir):
            for file in files:
                if file.endswith('.json'):
                    self.file_path_list.append(os.path.join(root, file))

    def __getitem__(self, idx):
        file_path = self.file_path_list[idx]  # 文件路径
        with open(file_path, 'r', encoding='utf-8') as file:
            # 读取JSON文件
            info = json.load(file)

        handcards0 = info['handCards0']
        handcards = info['handCards']
        fulu_ = info['fulu_']
        discards = info['discards']
        king_card = info['king_card']
        discards_seq = info['discards_seq']
        remain_card_num = info['remain_card_num']
        self_king_num = info['self_king_num']
        fei_king_nums = info['fei_king_nums']
        round_ = info['round_']
        dealer_flag = info['dealer_flag']
        label = info['isHu']
        operate_card = info['operate_card']
        hand_strength = info['hand_strength']

        features = card_preprocess(handcards0, handcards, king_card, discards_seq, discards, self_king_num,
                                   fei_king_nums, fulu_, remain_card_num, round_, dealer_flag, operate_card,hand_strength, label)

        return features, label

    def __len__(self):
        return len(self.file_path_list)


class ScoreDataset(Dataset):
    def __init__(self, file_dir):
        self.file_dir = file_dir
        self.file_path_list = []

        # 遍历文件夹获取所有文件的路径
        for root, dirs, files in os.walk(self.file_dir):
            for file in files:
                if file.endswith('.json'):
                    self.file_path_list.append(os.path.join(root, file))

    def __getitem__(self, idx):
        file_path = self.file_path_list[idx]  # 文件路径
        with open(file_path, 'r', encoding='utf-8') as file:
            # 读取JSON文件
            info = json.load(file)

        handcards0 = info['handCards0']
        handcards = info['handCards']
        fulu_ = info['fulu_']
        discards = info['discards']
        king_card = info['king_card']
        discards_seq = info['discards_seq']
        remain_card_num = info['remain_card_num']
        self_king_num = info['self_king_num']
        fei_king_nums = info['fei_king_nums']
        round_ = info['round_']
        dealer_flag = info['dealer_flag']
        label = info['high_score']
        is_hu = info['isHu']
        operate_card = info['operate_card']

        features = card_preprocess_score(handcards0, handcards, king_card, discards_seq, discards, self_king_num,
                                         fei_king_nums, fulu_, remain_card_num, round_, dealer_flag, operate_card,
                                         is_hu)

        return features, label

    def __len__(self):
        return len(self.file_path_list)


# 读取数据集
data_dir = '/path/to/your/dataset/hu'
dataset = HuDataset(data_dir)

if __name__ == '__main__':
    file_dir = '/home/tonnn/.nas/wjh/qihu/hu/hu/hu'
    dataset = HuDataset(file_dir)
    # file_name_list = os.listdir(file_dir)
    # file_path = os.path.join(file_dir, file_name_list[1])
    feature, label = dataset[1]
    print(feature)
    print(len(dataset))
    train_size = int(0.8 * len(dataset))
    val_size = int(len(dataset) - train_size)
    train_dataset, val_dataset = data.random_split(dataset, [train_size, val_size])
    train_loader = data.DataLoader(train_dataset, batch_size=100, shuffle=True, drop_last=True,
                                   num_workers=0)  # train需要shuffle
    # for features, labels in train_loader:
    # print(labels)
    #     print()
    # print()
