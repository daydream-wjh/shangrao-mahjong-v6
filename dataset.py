import json
import os
import torch.utils.data as data
from torch.utils.data import Dataset
from feature_extract_me import *


class HuDataset(Dataset):
    def __init__(self, file_dir):
        self.file_dir = file_dir
        self.data = []  # 存储所有加载的数据

        # 遍历文件夹并一次性加载所有数据到内存
        for root, dirs, files in os.walk(self.file_dir):
            for file in files:
                if file.endswith('.json'):
                    file_path = os.path.join(root, file)
                    with open(file_path, 'r', encoding='utf-8') as f:
                        info = json.load(f)

                    # 预处理并存储特征和标签
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

                    features = card_preprocess(handcards0, handcards, king_card, discards_seq, discards,
                                               self_king_num, fei_king_nums, fulu_, remain_card_num,
                                               round_, dealer_flag, operate_card, hand_strength, label)

                    self.data.append((features, label))

    def __getitem__(self, idx):
        # 直接从内存中返回数据
        return self.data[idx]

    def __len__(self):
        return len(self.data)


class ScoreDataset(Dataset):
    def __init__(self, file_dir):
        self.file_dir = file_dir
        self.data = []  # 存储所有加载的数据

        # 遍历文件夹并一次性加载所有数据到内存
        for root, dirs, files in os.walk(self.file_dir):
            for file in files:
                if file.endswith('.json'):
                    file_path = os.path.join(root, file)
                    with open(file_path, 'r', encoding='utf-8') as f:
                        info = json.load(f)

                    # 预处理并存储特征和标签
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

                    features = card_preprocess_score(handcards0, handcards, king_card, discards_seq,
                                                     discards, self_king_num, fei_king_nums, fulu_,
                                                     remain_card_num, round_, dealer_flag, operate_card, is_hu)

                    self.data.append((features, label))

    def __getitem__(self, idx):
        # 直接从内存中返回数据
        return self.data[idx]

    def __len__(self):
        return len(self.data)


if __name__ == '__main__':
    file_dir = '/home/tonnn/.nas/wjh/qihu/hu/hu/hu'
    dataset = HuDataset(file_dir)

    # 测试数据加载
    feature, label = dataset[1]
    print(feature)
    print(len(dataset))

    # 创建数据加载器
    train_size = int(0.8 * len(dataset))
    val_size = int(len(dataset) - train_size)
    train_dataset, val_dataset = data.random_split(dataset, [train_size, val_size])
    train_loader = data.DataLoader(train_dataset, batch_size=100, shuffle=True, drop_last=True, num_workers=0)