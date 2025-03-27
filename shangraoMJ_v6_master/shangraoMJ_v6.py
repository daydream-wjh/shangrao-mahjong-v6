#!/usr/bin/python2.7
# -*- coding: utf-8 -*-
# @Time    : 2020/12/24 17:02
# @Author  : Ren
# @Email   : 1543042088@qq.com
# @File    : shangraoMJ_v5.py
# @Software: PyCharm

# -*- coding:utf-8 -*-
# cython: language_level=2
# python 2.0　两整数相处会自动取整，需要人为给被除数添加float型

"""
# 2021.9.14
# 刘鑫鑫
# 将所有信息返回
# 设计json
{
play_type:ph,jy,qd,ssl
discard_need:[
discard:[
[need1,need2,need3],[pos1,pos2,pos3],
[need1,need2,need3],[pos1,pos2,pos3],
]
}
"""

import copy
import time
from shangraoMJ_v6_master import lib_MJ as MJ
import logging
import random
import datetime
import itertools

# 日志输出
logger = logging.getLogger("shangraoMJ_log_v6")
logger.setLevel(level=logging.DEBUG)
time_now = datetime.datetime.now()
# handler = logging.FileHandler(
#     "/data/log/recommondsrv_masterRecommend/log_v6_%i%i%i.txt" % (time_now.year, time_now.month, time_now.day))
# handler.setLevel(logging.INFO)
# formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
# handler.setFormatter(formatter)
# logger.addHandler(handler)
logger.info("shangrao_v6 compile finished...")

# global variable
TIME_START = time.time()
W_TYPE = 0  # lib_MJ的权重选择
ROUND = 0  # 轮数
t3Set = MJ.get_t3info()
t2Set, t2Efc, efc_t2index = MJ.get_t2info()
REMAIN_NUM = 136  # 剩余牌数
KING = None  # 宝牌
FEIKING = 0  # 飞宝数

T_SELFMO = [0] * 34  # 自摸概率表，牌存在于牌墙中的概率表
LEFT_NUM = [0] * 34  # 未出现的牌的数量表
LEFT_NUM_V5 = [4] * 34  # 按照V5版本的剩余牌数量表
RT1 = [[0] * 34, [0] * 34]  # 危险度表
RT2 = [[0] * 34, [0] * 34]
RT3 = [[0] * 34, [0] * 34]

t1tot3_dict = MJ.t1tot3_info()
t2tot3_dict = MJ.t2tot3_info()


class Node_PH:
    def __init__(self, take=None, AAA=[], ABC=[], jiang=[], T2=[], T1=[], raw=[], taking_set=[], taking_set_w=[],
                 king_num=0,
                 fei_king=0, baohuanyuan=False):
        self.take = take
        self.AAA = AAA
        self.ABC = ABC
        self.jiang = jiang
        self.T2 = T2
        self.T1 = T1
        self.raw = raw
        self.king_num = king_num
        self.fei_king = fei_king
        self.children = []
        self.taking_set = taking_set
        self.baohuanyuan = baohuanyuan
        self.taking_set_w = taking_set_w

    def add_child(self, child):
        self.children.append(child)

    def node_info(self):
        print(self.AAA, self.ABC, self.jiang, "T1=", self.T1, "T2=", self.T2, self.raw, self.taking_set, self.king_num,
              self.fei_king, self.baohuanyuan)


class Node_SSL:
    def __init__(self, take=None, taking_set=[], wan=[], tiao=[], tong=[], zi=[], T1=[], raw=[]):
        self.wan = wan
        self.tiao = tiao
        self.tong = tong
        self.zi = zi
        self.T1 = T1
        self.take = take
        self.raw = raw
        self.taking_set = taking_set
        self.children = []

    def add_child(self, node):
        self.children.append(node)

    def node_info(self):
        print(self.wan, self.tiao, self.tong, self.zi, "take ", self.take, "taking_set ", self.taking_set)


class SearchTree_PH():
    def __init__(self, hand, suits, combination_sets, king_card=None, fei_king=0):
        self.hand = hand
        self.suits = suits
        self.combination_sets = combination_sets
        self.xts = combination_sets[0][-2]
        self.tree_dict = []
        self.king_card = king_card
        self.fei_king = fei_king
        if king_card != None:
            self.king_num = hand.count(king_card)
        else:
            self.king_num = 0
        self.discard_score = {}
        self.discard_state = {}
        self.node_num = 0
        self.chang_num = 0
        self.ph_dis_effect_cards = {}
        self.tingpai = []

    def expand_node(self, node):
        if node.jiang == []:
            has_jiang = False
            if node.king_num >= 2:  # 宝还原
                has_jiang = True  # 补上，有宝时不再搜索无将情况
                child = Node_PH(take=-1, AAA=node.AAA, ABC=node.ABC, jiang=[0, 0],
                                T2=node.T2,
                                T1=node.T1,
                                taking_set=node.taking_set, taking_set_w=node.taking_set_w,
                                king_num=node.king_num - 2,
                                fei_king=node.fei_king, baohuanyuan=node.baohuanyuan)
                node.add_child(child=child)
                self.expand_node(child)

            if node.king_num > 0:  # 宝吊,
                has_jiang = True
                taking_set = copy.copy(node.taking_set)
                taking_set.append(0)
                taking_set_w = copy.copy(node.taking_set_w)
                taking_set_w.append(1)
                child = Node_PH(take=0, AAA=node.AAA, ABC=node.ABC, jiang=[0, 0], T2=node.T2,
                                T1=node.T1,
                                taking_set=taking_set, taking_set_w=taking_set_w, king_num=node.king_num - 1,
                                fei_king=node.fei_king, baohuanyuan=False)
                node.add_child(child=child)
                self.expand_node(child)

            if node.king_num <= 1:
                for t2 in node.T2:  # 有将
                    T2 = MJ.deepcopy(node.T2)
                    # 从t2中找到对子作为将牌
                    if t2[0] == t2[1]:
                        has_jiang = True
                        T2.remove(t2)
                        child = Node_PH(take=-1, AAA=node.AAA, ABC=node.ABC, jiang=t2, T2=T2,
                                        T1=node.T1,
                                        taking_set=node.taking_set, taking_set_w=node.taking_set_w,
                                        king_num=node.king_num,
                                        fei_king=node.fei_king, baohuanyuan=False)  # 非宝吊宝还原
                        node.add_child(child=child)
                        self.expand_node(node=child)
                        # break #移除，好像也不影响，后面评估去重是按摸牌来确定的，这里也不会摸牌了

            if not has_jiang:  # todo 这里可以考虑有将时也扩展
                jiangs = copy.copy(node.T1)
                # for t2 in node.T2:  # 将T2中的牌也加入到将牌中
                #     jiangs.extend(t2)
                if jiangs == []:
                    for t2 in node.T2:
                        jiangs = t2
                        T2 = MJ.deepcopy(node.T2)
                        T2.remove(t2)
                        for t1 in jiangs:
                            taking_set = copy.copy(node.taking_set)
                            taking_set.append(t1)
                            taking_set_w = copy.copy(node.taking_set_w)
                            taking_set_w.append(1)
                            T1 = copy.copy(jiangs)
                            T1.remove(t1)
                            child = Node_PH(take=t1, AAA=node.AAA, ABC=node.ABC, jiang=[t1, t1], T2=T2,
                                            T1=T1,
                                            taking_set=taking_set, taking_set_w=taking_set_w, king_num=node.king_num,
                                            fei_king=node.fei_king, baohuanyuan=False)
                            node.add_child(child=child)
                            self.expand_node(node=child)
                else:
                    for t1 in jiangs:
                        if t1 == -1:  # 对-1不作扩展
                            continue
                        taking_set = copy.copy(node.taking_set)
                        taking_set.append(t1)
                        taking_set_w = copy.copy(node.taking_set_w)
                        taking_set_w.append(1)
                        T1 = copy.copy(jiangs)
                        T1.remove(t1)
                        child = Node_PH(take=t1, AAA=node.AAA, ABC=node.ABC, jiang=[t1, t1], T2=node.T2,
                                        T1=T1,
                                        taking_set=taking_set, taking_set_w=taking_set_w, king_num=node.king_num,
                                        fei_king=node.fei_king, baohuanyuan=False)
                        node.add_child(child=child)
                        self.expand_node(node=child)

        # 胡牌判断
        elif len(node.AAA) + len(node.ABC) == 4:
            if node.king_num > 0:
                node.fei_king += node.king_num  # 多余的宝牌都没飞掉
                node.king_num = 0
                if node.baohuanyuan and node.fei_king == self.king_num + self.fei_king:  # 宝牌全部飞完了，所以就不是宝还原了
                    node.baohuanyuan = False
            return

        # T3扩展
        else:
            # 当待扩展集合不为空时，使用该集合进行扩展
            if node.raw != []:
                tn = node.raw[-1]
                raw = copy.copy(node.raw)  # 深度搜索后面的节点会改变raw，回退可能导致前面的节点raw不正确，这里需要copy
                raw.pop()
                if type(tn) == list:  # 使用t2扩展t3
                    t2 = tn
                    for item in t2tot3_dict[str(t2)]:
                        if item[1][0] == item[1][1]:
                            AAA = MJ.deepcopy(node.AAA)
                            AAA.append(item[1])
                            ABC = node.ABC
                        else:
                            AAA = node.AAA
                            ABC = MJ.deepcopy(node.ABC)
                            ABC.append(item[1])
                        if node.king_num > 0 and item[-2] == self.king_card:  # 宝还原
                            child = Node_PH(take=-1, AAA=AAA, ABC=ABC, jiang=node.jiang, T2=node.T2,
                                            T1=node.T1, raw=raw, taking_set=node.taking_set,
                                            taking_set_w=node.taking_set_w,
                                            king_num=node.king_num - 1,
                                            fei_king=node.fei_king, baohuanyuan=node.baohuanyuan)
                            node.add_child(child=child)
                            self.expand_node(node=child)

                        elif node.king_num > 0 and (0 in node.jiang):  # 宝牌补一张
                            child = Node_PH(take=0, AAA=AAA, ABC=ABC, jiang=node.jiang, T2=node.T2,
                                            T1=node.T1, raw=raw, taking_set=node.taking_set,
                                            taking_set_w=node.taking_set_w,
                                            king_num=node.king_num - 1,
                                            fei_king=node.fei_king, baohuanyuan=False)
                            node.add_child(child=child)
                            self.expand_node(node=child)
                            # normal
                        else:
                            taking_set = copy.copy(node.taking_set)
                            taking_set_w = copy.copy(node.taking_set_w)
                            taking_set.append(item[-2])
                            taking_set_w.append(item[-1])
                            child = Node_PH(take=item[-2], AAA=AAA, ABC=ABC, jiang=node.jiang, T2=node.T2,
                                            T1=node.T1, raw=raw, taking_set=taking_set, taking_set_w=taking_set_w,
                                            king_num=node.king_num,
                                            fei_king=node.fei_king, baohuanyuan=node.baohuanyuan)
                            node.add_child(child=child)
                            # child.node_info()
                            self.expand_node(node=child)
                elif type(tn) == int:
                    t1 = tn
                    for item in t1tot3_dict[str(t1)]:
                        # T1 = copy.copy(node.T1)
                        flag2 = False
                        if node.king_num > 0:  # 用于处理宝还原
                            for card in item[1]:
                                if card == self.king_card:
                                    # T2 = MJ.deepcopy(node.T2)
                                    # T2.append(sorted([card, t1]))
                                    flag2 = True
                                    raw_copy = copy.copy(raw)
                                    raw_copy.append(sorted([card, t1]))
                                    child = Node_PH(take=-1, AAA=node.AAA, ABC=node.ABC, jiang=node.jiang, T2=node.T2,
                                                    T1=node.T1, raw=raw_copy,
                                                    taking_set=node.taking_set, taking_set_w=node.taking_set_w,
                                                    king_num=node.king_num - 1, fei_king=node.fei_king,
                                                    baohuanyuan=node.baohuanyuan)
                                    node.add_child(child=child)
                                    self.expand_node(node=child)
                        if flag2:  # 上述宝还原后不再继续扩展
                            continue

                        if item[0][0] == item[0][1]:
                            AAA = MJ.deepcopy(node.AAA)
                            AAA.append(item[0])
                            ABC = node.ABC
                        else:
                            AAA = node.AAA
                            ABC = MJ.deepcopy(node.ABC)
                            ABC.append(item[0])

                        if node.king_num >= 2 and 0 in node.jiang:  # 宝牌有3张以上，直接补2张，即使其中有一张被作为宝还原也不影响
                            child = Node_PH(take=[0, 0], AAA=AAA, ABC=ABC, jiang=node.jiang, T2=node.T2, T1=node.T1,
                                            raw=raw,
                                            taking_set=node.taking_set, taking_set_w=node.taking_set_w,
                                            king_num=node.king_num - 2, fei_king=node.fei_king,
                                            baohuanyuan=False)
                            node.add_child(child=child)
                            self.expand_node(node=child)

                        # elif node.king_num == 0:  # 宝为0 的处理
                        #     take = item[1]
                        #     take_w = item[-1]
                        #
                        #     taking_set = copy.copy(node.taking_set)
                        #     taking_set.extend(take)
                        #     taking_set_w = copy.copy(node.taking_set_w)
                        #     taking_set_w.extend(take_w)
                        #     child = Node_PH(take=take, AAA=AAA, ABC=ABC, jiang=node.jiang, T2=node.T2, T1=node.T1,raw=raw,
                        #                     taking_set=taking_set, taking_set_w=taking_set_w,
                        #                     king_num=node.king_num, fei_king=node.fei_king,
                        #                     baohuanyuan=node.baohuanyuan)
                        #     node.add_child(child=child)
                        #     self.expand_node(node=child)

                        elif node.king_num == 1 and 0 in node.jiang:  # king_num=1 ,补一张牌,或者不补摸2张
                            # 用1张宝牌
                            for i in range(len(item[1])):
                                card = item[1][i]
                                take = [0, card]

                                taking_set = copy.copy(node.taking_set)
                                taking_set.append(card)
                                taking_set_w = copy.copy(node.taking_set_w)
                                taking_set_w.append(1)

                                child = Node_PH(take=take, AAA=AAA, ABC=ABC, jiang=node.jiang, T2=node.T2, T1=node.T1,
                                                raw=raw,
                                                taking_set=taking_set, taking_set_w=taking_set_w,
                                                king_num=node.king_num - 1, fei_king=node.fei_king,
                                                baohuanyuan=False)
                                node.add_child(child=child)
                                self.expand_node(node=child)
                        else:
                            # print ("node.king_num==%s", (node.king_num))
                            take = item[1]
                            take_w = item[-1]

                            taking_set = copy.copy(node.taking_set)
                            taking_set.extend(take)
                            taking_set_w = copy.copy(node.taking_set_w)
                            taking_set_w.extend(take_w)
                            child = Node_PH(take=take, AAA=AAA, ABC=ABC, jiang=node.jiang, T2=node.T2, T1=node.T1,
                                            raw=raw,
                                            taking_set=taking_set, taking_set_w=taking_set_w,
                                            king_num=node.king_num, fei_king=node.fei_king,
                                            baohuanyuan=node.baohuanyuan)
                            node.add_child(child=child)
                            self.expand_node(node=child)
                else:
                    print("tn Error")
            else:
                if node.T2 != []:  # 1、先扩展T2为T3
                    t2_sets = node.T2
                    T2 = copy.copy(node.T2)
                    for t2_set in itertools.combinations(t2_sets, min(4 - len(node.AAA) - len(node.ABC), len(t2_sets))):
                        node.T2 = copy.copy(T2)
                        node.raw = list(t2_set)
                        for t2 in node.raw:
                            node.T2.remove(t2)
                        self.expand_node(node=node)

                elif node.T1 != []:
                    t1_sets = copy.copy(node.T1)
                    # 这里移除了填充的-1，不作扩展
                    if -1 in t1_sets:
                        t1_sets.remove(-1)
                    T1 = copy.copy(node.T1)
                    for t1_set in itertools.combinations(t1_sets, min(4 - len(node.AAA) - len(node.ABC), len(t1_sets))):
                        node.T1 = copy.copy(T1)
                        node.raw = list(t1_set)
                        for t1 in node.raw:
                            node.T1.remove(t1)
                        self.expand_node(node=node)

    def generate_tree(self):
        kz = []
        sz = []
        for t3 in self.suits:
            if t3[0] == t3[1]:
                kz.append(t3)
            else:
                sz.append(t3)
        for cs in self.combination_sets:
            root = Node_PH(take=None, AAA=cs[0] + kz, ABC=cs[1] + sz, jiang=[], T2=cs[2] + cs[3], T1=cs[-1],
                           taking_set=[], taking_set_w=[], king_num=self.king_num,
                           fei_king=self.fei_king, baohuanyuan=self.king_num > 0)
            self.tree_dict.append(root)
            self.expand_node(node=root)

    def cal_score(self, node):
        value = 1
        if node.taking_set_w != []:
            node.taking_set_w[node.taking_set_w.index(min(node.taking_set_w))] = 1
            for i in range(len(node.taking_set)):
                card = node.taking_set[i]
                if card == 0:  # 宝吊的任意牌
                    taking_rate = 1.0
                else:
                    taking_rate = T_SELFMO[MJ.convert_hex2index(card)]
                # value *= taking_rate*node.taking_set_w[i]
                # todo 优化权重计算
                if node.taking_set_w[i] == MJ.w_ab:
                    value *= taking_rate * MJ.w_ab + RT3[0][MJ.convert_hex2index(card)]
                elif node.taking_set_w[i] == MJ.w_aa:
                    value *= taking_rate * MJ.w_aa + RT1[0][MJ.convert_hex2index(card)] + RT2[0][
                        MJ.convert_hex2index(card)] + RT3[0][MJ.convert_hex2index(card)]
                else:
                    value *= taking_rate
        # 摸牌概率修正，当一张牌被重复获取时，T_selfmo修改为当前数量占未出现牌数量的比例
        taking_set = list(set(node.taking_set))
        taking_set_num = [node.taking_set.count(i) for i in taking_set]
        for i in range(len(taking_set_num)):
            n = taking_set_num[i]
            j = 0
            while n > 1:
                j += 1
                index = MJ.convert_hex2index(taking_set[i])
                if LEFT_NUM[index] >= n:
                    value *= float(LEFT_NUM[index] - j) / LEFT_NUM[index]
                else:  # 摸牌数超过了剩余数，直接舍弃
                    value = 0
                    return value
                n -= 1

        fan = Fan_PH(kz=node.AAA, sz=node.ABC, jiang=node.jiang, fei_king=node.fei_king,
                     using_king=self.king_num + self.fei_king - node.fei_king,
                     baohuanyuan=node.baohuanyuan).fanDetect()
        score = fan * value
        return score

    def calculate_path_expectation(self, node):
        # 深度搜索
        if len(node.AAA) + len(node.ABC) == 4 and node.jiang != []:
            self.node_num += 1
            discard_set = []
            for i in range(node.fei_king - self.fei_king):
                discard_set.append(self.king_card)
            for t2 in node.T2:
                discard_set.extend(t2)
            discard_set.extend(node.T1)
            taking_set_sorted = sorted(node.taking_set)
            if len(taking_set_sorted) == 1:
                self.tingpai.append(taking_set_sorted)
            taking_set_lable = str(taking_set_sorted)  # 转化为str可以加快查找
            if discard_set != []:
                score = self.cal_score(node=node)  # 放到外面减耗时
            else:
                return
            # todo 这种按摸牌的评估方式是否唯一准确
            for card in list(set(discard_set)):
                if card not in self.discard_state.keys():
                    self.discard_state[card] = [[], [], []]
                if taking_set_lable not in self.discard_state[card][0]:
                    self.discard_state[card][0].append(taking_set_lable)
                    self.discard_state[card][1].append([node.AAA, node.ABC, node.jiang])
                    self.discard_state[card][-1].append(score)
                else:
                    index = self.discard_state[card][0].index(taking_set_lable)
                    if score > self.discard_state[card][-1][index]:
                        self.chang_num += 1
                        self.discard_state[card][-1][index] = score

        elif node.children != []:
            for child in node.children:
                self.calculate_path_expectation(node=child)

    def get_discard_score(self):
        self.generate_tree()
        for root in self.tree_dict:
            self.calculate_path_expectation(root)
        state_num = 0
        for discard in self.discard_state.keys():
            if discard not in self.discard_score.keys():
                self.discard_score[discard] = 0
                self.ph_dis_effect_cards[discard] = [[], []]
            self.discard_score[discard] = sum(self.discard_state[discard][-1])
            tmp = self.discard_state[discard][0]
            for t in tmp:
                for c in eval(t):
                    if c not in self.ph_dis_effect_cards[discard][0] and c:
                        self.ph_dis_effect_cards[discard][0].append(c)
            if self.discard_score[discard] == 0 and len(self.ph_dis_effect_cards) > 1:
                self.ph_dis_effect_cards.pop(discard)
            else:
                if discard == self.king_card:
                    self.ph_dis_effect_cards[discard].append(
                        (self.discard_score[discard] - float(value_t1(discard)) / (10 ** (MJ.min_xts + 1) / 2)) * 1.2)
                else:
                    self.ph_dis_effect_cards[discard].append(
                        self.discard_score[discard] - float(value_t1(discard)) / (10 ** (MJ.min_xts + 1) / 2))
            state_num += len(self.discard_state[discard][-1])
        return self.discard_score


class ShiSanLan:
    def __init__(self, cards, suits, king_card, fei_king, padding=[]):
        self.cards = cards
        self.suits = suits
        self.king_card = king_card
        self.discard_state = {}
        self.discard_score = {}
        self.ssl_dis_effct_cards = {}
        self.tree_list = []
        self.fei_king = fei_king
        self.padding = padding
        self.tingpai = []
        self.ssl_three_table = [[1, 6, 9],
                                [1, 4, 9],
                                [1, 4, 7],
                                [1, 4, 8],
                                [1, 5, 9],
                                [1, 5, 8],
                                [2, 5, 9],
                                [2, 5, 8],
                                [3, 6, 9],
                                [2, 6, 9]]

        self.ssl_two_table = [[1, 4], [1, 5], [1, 6], [1, 7], [1, 8], [1, 9],
                              [2, 5], [2, 6], [2, 7], [2, 8], [2, 9],
                              [3, 6], [3, 7], [3, 8], [3, 9],
                              [4, 7], [4, 8], [4, 9],
                              [5, 8], [5, 9],
                              [6, 9]]
        self.ssl_two_efc = [[[7], [8], [9]], [[8], [9]], [[9]], [[4]], [[4], [5]], [[4], [5], [6]],
                            [[8], [9]], [[9]], [[]], [[5]], [[5], [6]],
                            [[9]], [[]], [[]], [[6]],
                            [[1]], [[1]], [[1]],
                            [[1]], [[1]],
                            [[1], [2], [3]]
                            ]

        self.ssl_one_table = [[1], [9], [2], [8], [3], [7], [4], [6], [5]]
        self.ssl_one_efc = [[[4, 7], [4, 8], [4, 9], [5, 8], [5, 9], [6, 9]],  # 1
                            [[1, 4], [1, 5], [1, 6], [2, 5], [2, 6], [3, 6]],  # 9
                            [[5, 8], [5, 9], [6, 9], [7], [8]],  # 2
                            [[1, 4], [1, 5], [2, 5], [3]],  # 8
                            [[6, 9], [7], [8]],  # 3
                            [[1, 4], [2], [3]],  # 7
                            [[1, 7], [8], [9]],  # 4
                            [[1], [2], [3, 9]],  # 6
                            [[1, 8], [1, 9], [2, 8], [2, 9]]  # 5
                            ]

        self.ssl_zero_efc = [[1, 6, 9],
                             [1, 4, 9],
                             [1, 4, 7],
                             [1, 4, 8],
                             [1, 5, 9],
                             [1, 5, 8],
                             [2, 5, 9],
                             [2, 5, 8],
                             [3, 6, 9],
                             [2, 6, 9],
                             [2, 7], [3, 7], [3, 8]]
        # self.zi = [0x]

    def add_color(self, list, color):
        return [i + color for i in list]

    def color_info(self, cards, color):
        CSs = []
        tiles = list(set(cards))

        waitnumMax1 = max((tiles.count(1) + tiles.count(4) + tiles.count(7)),
                          (tiles.count(1) + tiles.count(4) + tiles.count(8)),
                          (tiles.count(1) + tiles.count(4) + tiles.count(9)),
                          (tiles.count(1) + tiles.count(5) + tiles.count(8)),
                          (tiles.count(1) + tiles.count(5) + tiles.count(9)),
                          (tiles.count(1) + tiles.count(6) + tiles.count(9)),
                          (tiles.count(2) + tiles.count(5) + tiles.count(8)),
                          (tiles.count(2) + tiles.count(5) + tiles.count(9)),
                          (tiles.count(2) + tiles.count(6) + tiles.count(9)),
                          (tiles.count(3) + tiles.count(6) + tiles.count(9)))
        waitnumMax2 = max((tiles.count(2) + tiles.count(7)),
                          (tiles.count(3) + tiles.count(7)),
                          (tiles.count(3) + tiles.count(8)), )

        if max(waitnumMax1, waitnumMax2) == 3:  # 当向听数为3 的时候 直接返回3，无有效牌
            for tb in self.ssl_three_table:
                if tb[0] in cards and tb[1] in cards and tb[2] in cards:
                    tmp = copy.copy(cards)
                    tmp.remove(tb[0])
                    tmp.remove(tb[1])
                    tmp.remove(tb[2])
                    CSs.append([self.add_color(tb, color), self.add_color(tmp, color)])
        elif max(waitnumMax1, waitnumMax2) == 2:  # 当向听数为2 的时候 返回向听数
            for i in range(len(self.ssl_two_table)):
                tb = self.ssl_two_table[i]
                if tb[0] in cards and tb[1] in cards:
                    tmp = copy.copy(cards)
                    tmp.remove(tb[0])
                    tmp.remove(tb[1])
                    CSs.append([self.add_color(tb, color), self.add_color(tmp, color)])
        elif max(waitnumMax1, waitnumMax2) == 1:  # 当向听数只有1 的时候
            for card in range(1, 10):
                if card in tiles:
                    tmp = copy.copy(cards)
                    tmp.remove(card)

                    CSs.append([[card + color], self.add_color(tmp, color)])

        else:
            CSs.append([[], []])
        # print CSs
        return CSs

    def ssl_CS(self):
        CSs = []
        if self.suits != []:
            return [[[], [], 14]]
        wan, tiao, tong, zi = MJ.split_type_s(self.cards)
        wan_CS = self.color_info(wan, 0)
        tiao_CS = self.color_info([i & 0x0f for i in tiao], 0x10)
        tong_CS = self.color_info([i & 0x0f for i in tong], 0x20)
        # zi
        zi_ssl = list(set(zi))
        zi_T1 = copy.copy(zi)
        for card in zi_ssl:
            zi_T1.remove(card)
            # zi_efc.remove(card)
        zi_CS = [[zi_ssl, zi_T1]]
        for cs_wan in wan_CS:
            for cs_tiao in tiao_CS:
                for cs_tong in tong_CS:
                    for cs_zi in zi_CS:
                        xts = 14 - len(cs_wan[0]) - len(cs_tiao[0]) - len(cs_tong[0]) - len(cs_zi[0])
                        CSs.append([cs_wan[0], cs_tiao[0], cs_tong[0], cs_zi[0],
                                    cs_wan[-1] + cs_tiao[-1] + cs_tong[-1] + cs_zi[-1], xts])

        CSs.sort(key=lambda k: k[-1], reverse=True)
        return CSs

    def efc_ssl(self, cards, type):
        cards_cp = [i & 0x0f for i in cards]
        if type <= 0x20:
            if len(cards_cp) == 0:
                efc = self.ssl_zero_efc
            elif len(cards_cp) == 1:
                efc = self.ssl_one_efc[self.ssl_one_table.index(cards_cp)]
            elif len(cards_cp) == 2:
                efc = self.ssl_two_efc[self.ssl_two_table.index(cards_cp)]
            elif len(cards_cp) == 3:
                efc = [[]]
            efc_c = []
            for s in efc:  # 2020.12.28 bug解决，这里没有花色还原
                efc_c.append([i + type for i in s])
            efc = efc_c
        else:
            efc = [[]]
            for card in range(0x31, 0x38):
                if card not in cards:
                    efc[0].append(card)
        return efc

    def expand_node(self, node):
        if len(node.wan) + len(node.tiao) + len(node.tong) + len(node.zi) == 14:
            # node.node_info()
            return
        else:
            # 分别扩展万条同
            if node.raw != []:
                raw = copy.copy(node.raw)
                card = raw[-1]
                raw.pop()
                type = card & 0xf0
                taking_set = copy.copy(node.taking_set)
                taking_set.append(card)
                if type == 0x00:
                    wan = copy.copy(node.wan)
                    wan.append(card)
                    child = Node_SSL(take=card, taking_set=taking_set, wan=wan, tiao=node.tiao, tong=node.tong,
                                     zi=node.zi, T1=node.T1, raw=raw)
                elif type == 0x10:
                    tiao = copy.copy(node.tiao)
                    tiao.append(card)
                    child = Node_SSL(take=card, taking_set=taking_set, wan=node.wan, tiao=tiao, tong=node.tong,
                                     zi=node.zi, T1=node.T1, raw=raw)
                elif type == 0x20:
                    tong = copy.copy(node.tong)
                    tong.append(card)
                    child = Node_SSL(take=card, taking_set=taking_set, wan=node.wan, tiao=node.tiao, tong=tong,
                                     zi=node.zi, T1=node.T1, raw=raw)
                elif type == 0x30:
                    zi = copy.copy(node.zi)
                    zi.append(card)
                    child = Node_SSL(take=card, taking_set=taking_set, wan=node.wan, tiao=node.tiao, tong=node.tong,
                                     zi=zi, T1=node.T1, raw=raw)
                node.add_child(child)
                self.expand_node(node=child)
            else:  # 生成raw
                # raws = []
                for wan_efc in self.efc_ssl(node.wan, 0):
                    for tiao_efc in self.efc_ssl(node.tiao, 0x10):
                        for tong_efc in self.efc_ssl(node.tong, 0x20):
                            for zi_efc in self.efc_ssl(node.zi, 0x30):
                                efcs = wan_efc + tiao_efc + tong_efc + zi_efc
                                xts = 14 - len(node.wan) - len(node.tiao) - len(node.tong) - len(node.zi)
                                for efc in itertools.combinations(efcs, xts):
                                    node.raw = list(efc)
                                    # raws.append(raw)
                                    self.expand_node(node)

    def generate_tree(self):
        CSs = self.ssl_CS()
        CSs.sort(key=lambda k: k[-1], reverse=True)
        # 取xts最小的一组
        min_xts = CSs[0][-1]
        CSs_min_xts = []
        for cs in CSs:
            if cs[-1] == min_xts:
                CSs_min_xts.append(cs)

        for cs in CSs_min_xts:
            node = Node_SSL(take=None, taking_set=[], wan=cs[0], tiao=cs[1], tong=cs[2], zi=cs[3], T1=cs[4], raw=[])
            self.tree_list.append(node)
            self.expand_node(node=node)

    def cal_score(self, node):
        """
            计算节点的评估值
        :param node: 节点
        :return: 评估值
        """

        value = 1
        # print node.taking_set
        for card in node.taking_set:
            value *= T_SELFMO[MJ.convert_hex2index(card)]
        # fan检测
        fan = 8
        # 飞宝
        fei_king = self.fei_king + node.T1.count(self.king_card)
        fan *= 2 ** fei_king
        # 七星
        if len(node.zi) == 7:
            fan *= 2
        score = value * fan
        return score

    def evaluate(self, node):
        if node.children == []:  # 叶子节点
            if len(node.wan) + len(node.tiao) + len(node.tong) + len(node.zi) == 14:

                score = self.cal_score(node)
                taking_set_sorted = sorted(node.taking_set)
                if len(taking_set_sorted) == 1:
                    self.tingpai.append(taking_set_sorted)
                discards = node.T1 + self.padding
                for discard in discards:
                    if discard not in self.discard_state.keys():
                        self.discard_state[discard] = [[], []]
                        self.discard_state[discard][0].append(taking_set_sorted)
                        self.discard_state[discard][-1].append(score)
                    elif taking_set_sorted not in self.discard_state[discard][0]:
                        self.discard_state[discard][0].append(taking_set_sorted)
                        self.discard_state[discard][-1].append(score)
        else:
            for child in node.children:
                self.evaluate(node=child)

    def get_discard_score(self):
        self.generate_tree()
        for tree in self.tree_list:
            self.evaluate(node=tree)
        for discard in self.discard_state.keys():
            if discard not in self.discard_score.keys():
                self.discard_score[discard] = sum(self.discard_state[discard][-1])
                self.ssl_dis_effct_cards[discard] = [[], []]
            tmp = self.discard_state[discard][0]
            for t in tmp:
                for c in t:
                    if c not in self.ssl_dis_effct_cards[discard][0]:
                        self.ssl_dis_effct_cards[discard][0].append(c)
            if self.discard_score[discard] == 0 and len(self.ssl_dis_effct_cards) > 1:
                self.ssl_dis_effct_cards.pop(discard)
            else:
                self.ssl_dis_effct_cards[discard].append(self.discard_score[discard])
        return self.discard_score


class JiuYao:
    def __init__(self, cards, suits, king_card, fei_king, padding=[]):
        self.cards = cards
        self.suits = suits
        self.king_card = king_card
        self.fei_king = fei_king
        self.padding = padding
        self.jy_dis_effct_cards = {}
        self.discard_score = {}
        self.discard_state = {}
        self.tingpai = [[1], [9], [0x11], [0x19], [0x21], [0x29], [0x31], [0x32], [0x33], [0x34], [0x35], [0x36],
                        [0x37]]
        self.yaojiu = [1, 9, 0x11, 0x19, 0x21, 0x29, 0x31, 0x32, 0x33, 0x34, 0x35, 0x36, 0x37]

    def yaojiu_CS(self):
        # 判断是否是91
        CS = [[], [], 14]
        flag = True
        for suit in self.suits:
            for card in suit:
                if card not in self.yaojiu:
                    flag = False
        if not flag:
            return CS
        CS[-1] -= len(self.suits) * 3
        for card in self.cards:
            if card in self.yaojiu:
                CS[0].append(card)
            else:
                CS[1].append(card)
        CS[-1] -= len(CS[0])
        return CS

    def get_discard_score(self):
        CS = self.yaojiu_CS()
        if CS[-1] != 14:
            value = 1
            yaojiu_take = 0
            n = 0
            for card in self.yaojiu:
                index = MJ.convert_hex2index(card)
                if CS[0].count(card) > 2 and CS[-1] != 1:  # todo 待完善
                    yaojiu_take += T_SELFMO[index] * MJ.w_aa + RT1[0][index] + RT2[0][index] + RT2[0][index] + RT3[0][
                        index] + RT3[0][index]
                else:
                    yaojiu_take += T_SELFMO[index]
                n += LEFT_NUM[MJ.convert_hex2index(card)]
            value *= yaojiu_take ** CS[-1]

            xt = CS[-1]
            j = 0
            while xt > 1:
                j += 1
                if n==0:
                    return 0
                value *= float(n - j) / n
                xt -= 1
                n -= 1
            # fan
            fan = 4
            fei_king = self.fei_king + CS[1].count(self.king_card)
            fan *= 2 ** fei_king
            # 有七星91吗？TODO
            score = value * fan
            discards = CS[1] + self.padding
            for discard in discards:
                if discard not in self.discard_score:
                    self.discard_score[discard] = score
                    self.jy_dis_effct_cards[discard] = [self.yaojiu, []]
                if self.discard_score[discard] == 0 and len(self.jy_dis_effct_cards) > 1:
                    self.jy_dis_effct_cards.pop(discard)
                else:
                    self.jy_dis_effct_cards[discard].append(self.discard_score[discard])
        return self.discard_score


class Node_Qidui:
    def __init__(self, take=None, AA=[], T1=[], raw=[], taking_set=[], king_num=0):
        self.take = take
        self.AA = AA
        self.T1 = T1
        self.raw = raw
        self.taking_set = taking_set
        self.king_num = king_num
        self.children = []

    def add_child(self, child):
        self.children.append(child)

    def node_info(self):
        print(self.AA, self.T1, self.raw, self.taking_set, self.king_num)


class Qidui:
    def __init__(self, cards, suits, king_card, fei_king, padding=[]):
        self.cards = cards
        self.suits = suits
        self.king_card = king_card
        self.fei_king = fei_king
        self.discard_score = {}
        self.king_num = cards.count(king_card)
        self.padding = padding
        self.tree_list = []
        self.discard_state = {}
        self.qd_dis_effct_cards = {}
        self.tingpai = []

    def qidui_CS(self):
        CS = [[], [], 14]
        if self.suits != []:
            return CS
        cards_rm_king = copy.copy(self.cards)
        for i in range(self.king_num):
            cards_rm_king.remove(self.king_card)
        for card in list(set(cards_rm_king)):
            n = cards_rm_king.count(card)
            if n == 1:
                CS[1].append(card)
            elif n == 2:
                CS[0].append([card, card])
            elif n == 3:
                CS[0].append([card, card])
                CS[1].append(card)
            elif n == 4:
                CS[0].append([card, card])
                CS[0].append([card, card])
        king_num = self.king_num
        # 这里把宝用掉
        while king_num > 0:
            if len(CS[0]) + king_num > 7:
                CS[0].append([self.king_card, self.king_card])
                king_num -= 2
            else:
                CS[0].append([0, 0])
                king_num -= 1
        CS[-1] -= len(CS[0]) * 2 + (7 - len(CS[0])) - 1  # 这里给七对的xt+1，减少后面选择打七对的概率
        if CS[-1] < 0:
            CS[-1] = 0
        return CS

    def expand_node(self, node):
        if len(node.AA) == 7:
            return
        else:
            if node.raw != []:
                # for card in node.raw:
                card = node.raw[-1]
                node.raw.pop()
                AA = copy.copy(node.AA)
                AA.append([card, card])

                # if node.king_num==1:
                #
                #     child = Node_Qidui(take=0, AA=AA, T1=node.T1, taking_set=node.taking_set, king_num=node.king_num-1)
                # else:
                # T1 = copy.copy(node.T1)
                # T1.remove(card)

                taking_set = copy.copy(node.taking_set)
                taking_set.append(card)
                child = Node_Qidui(take=card, AA=AA, T1=node.T1, raw=node.raw, taking_set=taking_set,
                                   king_num=node.king_num)
                node.add_child(child=child)
                self.expand_node(node=child)
            else:
                if node.T1 != []:
                    t1_sets = copy.copy(node.T1)
                    # if -1 in t1_sets:
                    #     t1_sets.remove(-1)
                    T1 = copy.copy(node.T1)
                    for t1_set in itertools.combinations(t1_sets, min(7 - len(node.AA), len(t1_sets))):
                        node.T1 = copy.copy(T1)
                        node.raw = list(t1_set)
                        for t1 in node.raw:
                            node.T1.remove(t1)
                        self.expand_node(node=node)

    def generate_tree(self):
        CS = self.qidui_CS()
        # print "qidui CS",CS
        node = Node_Qidui(take=None, AA=CS[0], T1=CS[1], taking_set=[], king_num=self.king_num)
        self.tree_list.append(node)
        self.expand_node(node=node)

    def fan(self, node):
        """
        七对番型
        :param node:
        """
        fei_king = self.fei_king + node.T1.count(self.king_card)
        if self.king_num == 0 or fei_king == self.fei_king + self.king_num:
            fan = 16
        else:
            fan = 12
        fan *= 2 ** fei_king
        # 91
        jiuyao = [1, 9, 0x11, 0x19, 0x21, 0x29, 0x31, 0x32, 0x33, 0x34, 0x35, 0x36, 0x37]
        ziyise = [0x31, 0x32, 0x33, 0x34, 0x35, 0x36, 0x37]
        flag_jiuyao = True
        for t2 in node.AA:
            if t2[0] not in jiuyao:
                flag_jiuyao = False
                break
        flag_ziyise = True
        for t2 in node.AA:
            if t2[0] not in ziyise:
                flag_ziyise = False
                break
        if flag_jiuyao:
            fan *= 2
        if flag_ziyise:
            fan *= 2
        return fan

    def evaluate(self, node):
        if node.children == []:
            if len(node.AA) == 7:
                # node.node_info()
                taking_set_sorted = sorted(node.taking_set)
                if len(taking_set_sorted) == 1:
                    self.tingpai.append(taking_set_sorted)
                value = 1
                for card in taking_set_sorted:
                    # print "card",card
                    if card == -1:
                        value = 1.0 / 34
                    else:
                        value *= T_SELFMO[MJ.convert_hex2index(card)]
                fan = self.fan(node=node)
                score = value * fan
                discards = node.T1 + self.padding
                for discard in discards:
                    if discard not in self.discard_state.keys():
                        self.discard_state[discard] = [[], []]
                        self.discard_state[discard][0].append(taking_set_sorted)
                        self.discard_state[discard][-1].append(score)
                    elif taking_set_sorted not in self.discard_state[discard][0]:
                        self.discard_state[discard][0].append(taking_set_sorted)
                        self.discard_state[discard][-1].append(score)
        else:
            for child in node.children:
                self.evaluate(child)

    def get_discard_score(self):
        self.generate_tree()
        for tree in self.tree_list:
            self.evaluate(tree)
        for discard in self.discard_state.keys():
            if discard not in self.discard_score:
                self.discard_score[discard] = 0
                self.qd_dis_effct_cards[discard] = [[], []]
            tmp = self.discard_state[discard][0]
            for t in tmp:
                for c in t:
                    if c not in self.qd_dis_effct_cards[discard][0]:
                        self.qd_dis_effct_cards[discard][0].append(c)
            self.discard_score[discard] = sum(self.discard_state[discard][-1])
            if self.discard_score[discard] == 0 and len(self.qd_dis_effct_cards) > 1:
                self.qd_dis_effct_cards.pop(discard)
            else:
                self.qd_dis_effct_cards[discard].append(self.discard_score[discard])
        return self.discard_score


'''
番数计算类
'''


class Fan_PH():
    def __init__(self, kz, sz, jiang, fei_king=0, using_king=0, baohuanyuan=False):
        """
        初始化类变量
        :param kz: 刻子
        :param sz: 顺子
        :param jiang: 将
        :param node: 待检测的结点
        :param fei_king: 飞宝数
        """
        self.kz = kz
        self.sz = sz
        self.jiang = jiang
        self.fei_king = fei_king
        self.using_king = using_king
        self.baohuanyuan = baohuanyuan
        self.mul = 2

    # 碰碰胡
    def pengPengHu(self):
        """
        碰碰胡检测
        是否刻子树数达到４个
        :return: bool
        """
        if len(self.kz) == 4:
            # if self.usingKing==0:
            return True
        else:
            return False

    # 宝还原 x2
    # def baoHuanYuan(self):
    #
    #     if self.baohuanyuan:
    #         return True
    #     else:
    #         return False

    # 清一色 x2
    def qingYiSe(self):
        """
        清一色检测
        手牌为同一花色
        :return: bool
        """
        # todo 宝吊无法检测清一色，因为将牌无法确定
        w = 0
        ti = 0
        to = 0
        z = 0
        # print self.kz + self.sz+ self.jiang
        for t in self.kz + self.sz + [self.jiang]:
            card = t[0]
            if card != 0:
                if card & 0xf0 == 0x00:
                    w = 1
                elif card & 0xf0 == 0x10:
                    ti = 1
                elif card & 0xf0 == 0x20:
                    to = 1
                else:
                    return False

        if w + ti + to <= 1:
            return True
        else:
            return False

    def fanDetect(self):
        """
        番数计算
        基础分４分，通过调用上述的番种检测来增加基础分
        :return: int 番数
        """
        # 基础分判定
        score = 4
        if self.pengPengHu():
            # print "0"
            score *= self.mul
            if self.using_king == 0 or self.baohuanyuan:
                score *= self.mul
            score *= 2  # 碰碰胡再给2倍分

        # 翻倍机制
        # 飞宝 当可以宝吊时，将飞宝倍数得到提高
        # if 0 in self.jiang:
        #     for i in range(self.fei_king):
        #         score *= 2.5
        # else:
        for i in range(self.fei_king):
            # print "1"
            score *= self.mul

        # # 宝还原　x2
        if self.baohuanyuan:
            # print score, self.baohuanyuan,self.jiang,
            # print "2"
            score *= self.mul

        # 清一色
        if self.qingYiSe():
            score *= self.mul
            # print "3"
        # 单吊　x2
        # 这里无法处理，宝吊需要吃碰杠吃碰杠处理
        # if score>16: #得分大于16时，分数评估提高
        #     score*=1.5
        # print
        return score


'''
平胡类，相关处理方法
分为手牌拆分模块sys_info，评估cost,出牌决策，吃碰杠决策等部分
'''


class PingHu:
    '''
    '''

    def __init__(self, cards, suits, kingCard=None, fei_king=0, padding=[]):
        """
        类变量初始化
        :param cards: 手牌　
        :param suits:副露
        :param leftNum:剩余牌数量列表
        :param discards:弃牌
        :param discards_real:实际弃牌
        :param discardsOp:场面副露
        :param round:轮数
        :param remainNum:牌墙剩余牌数量
        :param seat_id:座位号
        :param kingCard:宝牌
        :param fei_king:飞宝数
        :param op_card:动作操作牌
        """
        cards.sort()
        self.cards = cards
        self.suits = suits
        self.kingCard = kingCard
        self.fei_king = fei_king
        self.padding = padding
        self.kingNum = cards.count(kingCard)

    @staticmethod
    def split_type_s(cards=[]):
        """
        功能：手牌花色分离，将手牌分离成万条筒字各色后输出
        :param cards: 手牌　[]
        :return: 万,条,筒,字　[],[],[],[]
        """
        cards_wan = []
        cards_tiao = []
        cards_tong = []
        cards_zi = []
        for card in cards:
            if card & 0xF0 == 0x00:
                cards_wan.append(card)
            elif card & 0xF0 == 0x10:
                cards_tiao.append(card)
            elif card & 0xF0 == 0x20:
                cards_tong.append(card)
            elif card & 0xF0 == 0x30:
                cards_zi.append(card)
        return cards_wan, cards_tiao, cards_tong, cards_zi

    @staticmethod
    def get_effective_cards(dz_set=[]):
        """
        获取有效牌
        :param dz_set: 搭子集合 list [[]]
        :return: 有效牌 list []
        """
        effective_cards = []
        for dz in dz_set:
            if len(dz) == 1:
                effective_cards.append(dz[0])
            elif dz[1] == dz[0]:
                effective_cards.append(dz[0])
            elif dz[1] == dz[0] + 1:
                if int(dz[0]) & 0x0F == 1:
                    effective_cards.append(dz[0] + 2)
                elif int(dz[0]) & 0x0F == 8:
                    effective_cards.append((dz[0] - 1))
                else:
                    effective_cards.append(dz[0] - 1)
                    effective_cards.append(dz[0] + 2)
            elif dz[1] == dz[0] + 2:
                effective_cards.append(dz[0] + 1)
        effective_cards = set(effective_cards)  # set 和list的区别？
        return list(effective_cards)

    # 判断３２Ｎ是否存在于ｃａｒｄｓ中
    @staticmethod
    def in_cards(t32=[], cards=[]):
        """
        判断３２Ｎ是否存在于ｃａｒｄｓ中
        :param t32: ３Ｎ或2N组合牌
        :param cards: 本次判断的手牌
        :return: bool
        """
        for card in t32:
            if card not in cards:
                return False
        return True

    @staticmethod
    def get_32N(cards=[]):
        """
        功能：计算所有存在的手牌的３Ｎ与２Ｎ的集合，例如[3,4,5]　，将得到[[3,4],[3,5],[4,5],[3,4,5]]
        思路：为减少计算量，对长度在12张以上的单花色的手牌，当存在顺子时，不再计算搭子
        :param cards: 手牌　[]
        :return: 3N与2N的集合　[[]]
        """
        cards.sort()
        kz = []
        sz = []
        aa = []
        ab = []
        ac = []
        lastCard = 0
        # 对长度在12张以上的单花色的手牌，当存在顺子时，不再计算搭子
        if len(cards) >= 12:
            for card in cards:
                if card == lastCard:
                    continue
                else:
                    lastCard = card
                if cards.count(card) >= 3:
                    kz.append([card, card, card])
                elif cards.count(card) >= 2:
                    aa.append([card, card])
                if card + 1 in cards and card + 2 in cards:
                    sz.append([card, card + 1, card + 2])
                else:
                    if card + 1 in cards:
                        ab.append([card, card + 1])
                    if card + 2 in cards:
                        ac.append([card, card + 2])
        else:
            for card in cards:
                if card == lastCard:
                    continue
                else:
                    lastCard = card
                if cards.count(card) >= 3:
                    kz.append([card, card, card])
                if cards.count(card) >= 2:
                    aa.append([card, card])
                if card + 1 in cards and card + 2 in cards:
                    sz.append([card, card + 1, card + 2])
                if card + 1 in cards:
                    ab.append([card, card + 1])
                if card + 2 in cards:
                    ac.append([card, card + 2])
        return kz + sz + aa + ab + ac

    def extract_32N(self, cards=[], t32_branch=[], t32_set=[]):
        """
        功能：递归计算手牌的所有组合信息，并存储在t32_set，
        思路: 每次递归前检测是否仍然存在３２N的集合,如果没有则返回出本此计算的结果，否则在手牌中抽取该３２N，再次进行递归
        :param cards: 手牌
        :param t32_branch: 本次递归的暂存结果
        :param t32_set: 所有组合信息
        :return: 结果存在t32_set中
        """
        t32N = self.get_32N(cards=cards)

        if len(t32N) == 0:
            t32_set.extend(t32_branch)
            # t32_set.extend([cards])
            t32_set.append(0)
            t32_set.extend([cards])
        else:
            for t32 in t32N:
                if self.in_cards(t32=t32, cards=cards):
                    cards_r = copy.copy(cards)
                    for card in t32:
                        cards_r.remove(card)
                    t32_branch.append(t32)
                    self.extract_32N(cards=cards_r, t32_branch=t32_branch, t32_set=t32_set)
                    if len(t32_branch) >= 1:
                        t32_branch.pop(-1)

    def tree_expand(self, cards):
        """
        功能：对extract_32N计算的结果进行处理同一格式，计算万条筒花色的组合信息
        思路：对t32_set的组合信息进行格式统一，分为[kz,sz,aa,ab,xts,leftCards]保存，并对划分不合理的地方进行过滤，例如将３４５划分为35,4为废牌的情况
        :param cards: cards [] 万条筒其中一种花色手牌
        :return: allDeWeight　[kz,sz,aa,ab,xts,leftCards] 去除不合理划分情况的组合后的组合信息
        """
        all = []
        t32_set = []
        self.extract_32N(cards=cards, t32_branch=[], t32_set=t32_set)
        kz = []
        sz = []
        t2N = []
        aa = []
        length_t32_set = len(t32_set)
        i = 0
        # for i in range(len(t32_set)):
        while i < length_t32_set:
            t = t32_set[i]
            flag = True  # 本次划分是否合理
            if t != 0:
                if len(t) == 3:

                    if t[0] == t[1]:
                        kz.append(t)
                    else:
                        sz.append(t)  # print (sub)
                elif len(t) == 2:
                    if t[1] == t[0]:
                        aa.append(t)
                    else:
                        t2N.append(t)

            else:
                '修改，使计算时间缩短'
                leftCards = t32_set[i + 1]
                efc_cards = self.get_effective_cards(dz_set=t2N)  # t2N中不包含ａａ
                # 去除划分不合理的情况，例如345　划分为34　或35等，对于333 划分为33　和3的情况，考虑有将牌的情况暂时不做处理
                for card in leftCards:
                    if card in efc_cards:
                        flag = False
                        break

                if flag:
                    all.append([kz, sz, aa, t2N, 0, leftCards])
                kz = []
                sz = []
                aa = []
                t2N = []
                i += 1
            i += 1

        allSort = []  # 给每一个元素排序
        allDeWeight = []  # 排序去重后

        for e in all:
            for f in e:
                if f == 0:  # 0是xts位，int不能排序
                    continue
                else:
                    f.sort()
            allSort.append(e)

        for a in allSort:
            if a not in allDeWeight:
                allDeWeight.append(a)

        allDeWeight = sorted(allDeWeight, key=lambda k: (len(k[0]), len(k[1]), len(k[2])), reverse=True)  # 居然可以这样排序！！
        return allDeWeight

    @staticmethod
    def zi_expand(cards=[]):
        """
        功能：计算字牌组合信息
        思路：字牌组合信息需要单独计算，因为没有字顺子，迭代计算出各张字牌的２Ｎ和３Ｎ的情况，由于某些情况下，可能只会需要ａａ作为将牌的情况，同时需要刻子和ａａ的划分结果
        :param cards: 字牌手牌
        :return: ziBranch　字牌的划分情况　[kz,sz,aa,ab,xts,leftCards]
        """
        cardList = []
        for i in range(7):
            cardList.append([])
        ziCards = [0x31, 0x32, 0x33, 0x34, 0x35, 0x36, 0x37]
        for card in ziCards:
            index = (card & 0x0f) - 1
            # print(index)

            if cards.count(card) == 4:
                # 此结构为[3N,2N,leftCards]
                cardList[index].append([[[card, card, card]], [], [], [], 0, [card]])
            elif cards.count(card) == 3:
                cardList[index].append([[[card, card, card]], [], [], [], 0, []])
                cardList[index].append([[], [], [[card, card]], [], 0, [card]])
            elif cards.count(card) == 2:

                cardList[index].append([[], [], [[card, card]], [], 0, []])
            elif cards.count(card) == 1:
                cardList[index].append([[], [], [], [], 0, [card]])
            else:
                cardList[index].append([[], [], [], [], 0, []])

        ziBranch = []
        for c1 in cardList[0]:
            for c2 in cardList[1]:
                for c3 in cardList[2]:
                    for c4 in cardList[3]:
                        for c5 in cardList[4]:
                            for c6 in cardList[5]:
                                for c7 in cardList[6]:
                                    branch = []
                                    for n in range(6):
                                        branch.append(c1[n] + c2[n] + c3[n] + c4[n] + c5[n] + c6[n] + c7[n])
                                    ziBranch.append(branch)
        return ziBranch

    def pinghu_CS(self, cards=[], suits=[], t1=[]):
        if cards == []:
            cards = self.cards
            suits = self.suits
        cards.sort()
        # 加入一些特殊的处理 例如碰碰胡的CS生成
        CS = self.pinghu_CS2(cards, suits, t1)
        kingNum = 0
        RM_King = copy.copy(cards)
        if self.kingCard != None:
            kingNum = cards.count(self.kingCard)
            for i in range(kingNum):
                RM_King.remove(self.kingCard)
        pph = MJ.pengpengHu(outKingCards=RM_King, suits=suits, kingNum=kingNum)
        if pph[0] not in CS and pph[0][-2] <= CS[0][-2] + 1:
            CS += pph
        return CS

    def pinghu_CS2(self, cards=[], suits=[], t1=[], is_ting=False):
        """
        功能：综合计算手牌的组合信息
        思路：对手牌进行花色分离后，单独计算出每种花色的组合信息　，再将其综合起来，计算每个组合向听数，最后输出最小向听数及其加一的组合
        :param cards: 手牌
        :param suits: 副露
        :param left_num: 剩余牌
        :param kingCard: 宝牌
        :return: 组合信息
        """
        # 去除宝牌计算信息，后面出牌和动作决策再单独考虑宝牌信息
        if cards == []:
            cards = self.cards
            suits = self.suits
        RM_King = copy.copy(cards)
        kingNum = 0
        if self.kingCard != None:
            kingNum = cards.count(self.kingCard)
            for i in range(kingNum):
                RM_King.remove(self.kingCard)

        # 花色分离
        wan, tiao, tong, zi = self.split_type_s(RM_King)
        wan_expd = self.tree_expand(cards=wan)
        tiao_expd = self.tree_expand(cards=tiao)
        tong_expd = self.tree_expand(cards=tong)
        zi_expd = self.zi_expand(cards=zi)

        all = []
        for i in wan_expd:
            for j in tiao_expd:
                for k in tong_expd:
                    for m in zi_expd:
                        branch = []
                        # 将每种花色的4个字段合并成一个字段
                        for n in range(6):
                            branch.append(i[n] + j[n] + k[n] + m[n])

                        branch[-1] += self.padding + t1
                        all.append(branch)

        # 将获取概率为０的组合直接丢弃到废牌中 todo 由于有宝，这里也可能会被宝代替
        # 移到了出牌决策部分处理
        if self.kingNum <= 1:  # 这里只考虑出牌、宝做宝吊的情况
            for a in all:
                for i in range(len(a[3]) - 1, -1, -1):
                    ab = a[3][i]
                    efc = self.get_effective_cards([ab])
                    if sum([LEFT_NUM[MJ.convert_hex2index(e)] for e in efc]) == 0:
                        a[3].remove(ab)
                        a[-1].extend(ab)
                        # logger.info("remove rate 0 ab,%s,%s,%s,a=%s",self.cards,self.suits,self.kingCard,a)

        # 计算向听数
        # 计算拆分组合的向听数
        all = MJ.cal_xts(all, suits, kingNum)

        # 获取向听数最小的all分支
        min_index = 0
        for i in range(len(all)):
            if all[i][4] > all[0][4]:  # xts+１以下的组合
                min_index = i
                break

        if min_index == 0:  # 如果全部都匹配，则min_index没有被赋值，将min_index赋予ａｌｌ长度
            min_index = len(all)

        all = all[:min_index]

        # 处理向听数为0时的情况，需要从中依次选择一张牌作为t1
        if all[0][-2] == 0 and all[0][-1] == [] and not is_ting:
            all = []
            for card in list(set(cards)):
                cards_ = copy.copy(cards)
                cards_.remove(card)
                all += self.pinghu_CS2(cards=cards_, suits=suits, t1=[card])
        return all

    def left_card_weight(self, card, left_num, need_jiang=False):
        """
        功能：对废牌组合中的每张废牌进行评估，计算其成为３Ｎ的概率
        思路：每张牌能成为３N的情况可以分为先成为搭子，在成为３Ｎ２步，成为搭子的牌必须自己摸到，而成为kz,sz可以通过吃碰。刻子为获取２张相同的牌，顺子为其邻近的２张牌
        :param card: 孤张牌
        :param left_num: 剩余牌
        :return: 评估值
        """

        # if self.remainNum==0:
        #     remainNum=1
        # else:
        #     remainNum = self.remainNum
        # remainNum = 1
        i = convert_hex2index(card)

        if need_jiang:
            return left_num[i]
        # d_w = 0

        # if left_num[i] == self.remainNum:
        #     sf = float(self.leftNum[i])
        # else:
        #     sf = float(left_num[i]) / remainNum * float((left_num[i] - 1)) / remainNum * 6

        if left_num[i] > 1:
            aa = left_num[i] * (left_num[i] - 1) * 4
        else:
            aa = left_num[i]
        if card >= 0x31:  # kz概率
            # todo if card == fengwei:
            # if card >= 0x35 and left_num[i] >= 2:
            #     d_w = left_num[i] * left_num[i] * 2  # bug 7.22 修正dw-d_w
            # else:
            d_w = aa  # 7.22 １６:３５ 去除字牌
        elif card % 16 == 1:  # 11＋２3
            d_w = aa + left_num[i + 1] * left_num[i + 2] * 2
        elif card % 16 == 2:  # 22+13+3(14)+43   222 123 234
            d_w = aa + left_num[i - 1] * left_num[i + 1] * 2 + left_num[i + 1] * left_num[i + 2] * 2
        elif card % 16 == 8:  # 888 678 789
            d_w = aa + left_num[i - 2] * left_num[i - 1] * 2 + left_num[i - 1] * left_num[i + 1] * 2
        elif card % 16 == 9:  # 999 789
            d_w = aa + left_num[i - 2] * left_num[i - 1] * 2
        # 删除多添加的×２
        else:  # 555 345 456 567
            # print (left_num)
            d_w = aa + left_num[i - 2] * left_num[i - 1] * 2 + left_num[i - 1] * left_num[i + 1] * 2 + left_num[i + 1] * \
                  left_num[
                      i + 2] * 2
        # if card<=0x31:
        #     if (card%0x0f==3 or card %0x0f==7): #给金3银7倍数
        #         d_w*=1.5
        #     elif card%0x0f==5:
        #         d_w*=1.2
        print("i=", i, d_w)
        return d_w


def translate16_33(i):
    """
    将牌值１６进制转化为０－３３的下标索引
    :param i: 牌值
    :return: 数组下标
    """
    i = int(i)
    if i >= 0x01 and i <= 0x09:
        i = i - 1
    elif i >= 0x11 and i <= 0x19:
        i = i - 8
    elif i >= 0x21 and i <= 0x29:
        i = i - 15
    elif i >= 0x31 and i <= 0x37:
        i = i - 22
    else:
        # i=1/0
        print("translate16_33 is error,i=%d" % i)
        i = -1
    return i


def convert_hex2index(a):
    """
    将牌值１６进制转化为０－３３的下标索引
    :param a: 牌
    :return: 数组下标
    """
    if a > 0 and a < 0x10:
        return a - 1
    if a > 0x10 and a < 0x20:
        return a - 8
    if a > 0x20 and a < 0x30:
        return a - 15
    if a > 0x30 and a < 0x40:
        return a - 22


def trandfer_discards(discards, discards_op, handcards):
    """
    获取场面剩余牌数量
    计算手牌和场面牌的数量，再计算未知牌的数量
    :param discards: 弃牌
    :param discards_op: 场面副露
    :param handcards: 手牌
    :return: left_num, discards_list　剩余牌列表，已出现的牌数量列表
    """
    discards_map = {0x01: 0, 0x02: 1, 0x03: 2, 0x04: 3, 0x05: 4, 0x06: 5, 0x07: 6, 0x08: 7, 0x09: 8, 0x11: 9, 0x12: 10,
                    0x13: 11, 0x14: 12, 0x15: 13, 0x16: 14, 0x17: 15, 0x18: 16, 0x19: 17, 0x21: 18, 0x22: 19, 0x23: 20,
                    0x24: 21, 0x25: 22, 0x26: 23, 0x27: 24, 0x28: 25, 0x29: 26, 0x31: 27, 0x32: 28, 0x33: 29, 0x34: 30,
                    0x35: 31, 0x36: 32, 0x37: 33, }
    left_num = [4] * 34
    discards_list = [0] * 34

    for per in discards:
        for item in per:
            discards_list[discards_map[item]] += 1
            left_num[discards_map[item]] -= 1
    for seat_op in discards_op:
        for op in seat_op:
            for item in op:
                discards_list[discards_map[item]] += 1
                left_num[discards_map[item]] -= 1
    for item in handcards:
        left_num[discards_map[item]] -= 1
    return left_num, discards_list


# 获取ｌｉｓｔ中的最小值和下标
def get_min(list=[]):
    """
    获取最小ｘｔｓ的下标
    :param list: 向听数列表
    :return: 返回最小向听数及其下标
    """
    min = 14
    index = 0
    for i in range(len(list)):
        if list[i] < min:
            min = list[i]
            index = i
    return min, index


def pre_king(king_card=None):
    """
    计算宝牌的前一张
    :param king_card: 宝牌
    :return:宝牌的前一张牌
    """
    if king_card == None:
        return None
    if king_card == 0x01:
        return 0x09
    elif king_card == 0x11:
        return 0x19
    elif king_card == 0x21:
        return 0x29
    elif king_card == 0x31:
        return 0x37
    else:
        return king_card - 1


def value_t1(card):
    value = 0
    if card != -1:
        for e in t1tot3_dict[str(card)]:
            v = 1
            for i in range(len(e[1])):
                v *= T_SELFMO[MJ.convert_hex2index(e[1][i])] * e[-1][i]
            value += v
    return value


def get_effect_card(t2):
    """
    功能：计算搭子的有效牌
    """
    effect_card = []
    if t2[0] + 2 == t2[1]:
        effect_card.append(t2[0] + 1)
    if t2[0] + 1 == t2[1]:
        if t2[0] - 1 & 0x0F > 0:
            effect_card.append(t2[0] - 1)
        if t2[1] + 1 & 0x0F <= 9:
            effect_card.append(t2[1] + 1)
    return effect_card


def get_a_effect_card(t1):
    """
    计算t1的有效牌
    """
    if t1 & 0xF0 == 0x30:
        return [t1]
    effect_card = [t1, t1 - 1, t1 - 2, t1 + 1, t1 + 2]
    invalid = []
    for card in effect_card:
        if card & 0x0F < 1 or card & 0x0F > 9:
            invalid.append(card)
    for card in invalid:
        effect_card.remove(card)
    return effect_card


def get_tingcards(cards=[], suits=[], king_card=None):
    PH = PingHu(cards=cards, suits=suits, kingCard=king_card, fei_king=0, padding=[])
    SSL = ShiSanLan(cards=cards, suits=suits, king_card=king_card, fei_king=0, padding=[])
    JY = JiuYao(cards=cards, suits=suits, king_card=king_card, fei_king=0, padding=[])
    QD = Qidui(cards=cards, suits=suits, king_card=king_card, fei_king=0, padding=[])
    # 组合信息
    CS_PH = PH.pinghu_CS2(is_ting=True)
    CS_SSL = SSL.ssl_CS()
    CS_JY = JY.yaojiu_CS()
    CS_QD = QD.qidui_CS()
    xts_list = [CS_PH[0][-2], CS_SSL[0][-1], CS_JY[-1], CS_QD[-1] - 1]
    hu_type = ['PH', 'SSL', 'JY', 'QD']
    if 0 in xts_list:
        value = random.randint(300, 400)
        result_info = [{
            "discard_need": {-1: [[-1], [-1], value]},
            "play_type": hu_type[xts_list.index(0)],
            "xts": 1}]
        return result_info
    result_info = []
    for i in range(len(xts_list)):
        value = random.randint(200, 250)
        tingcards = []
        result = {}
        if i == 0 and xts_list[i] == 1:
            for cs in CS_PH:
                if cs[-2] == 1 and cards.count(king_card) == 0:  # 无宝牌时
                    if len(cs[2]) == 0 and cs[-1][0]:  # 缺将牌
                        tingcards.append(cs[-1][0])
                    elif len(cs[2]) == 2:
                        for aa in cs[2]:
                            tingcards.append(aa[0])
                    elif cs[3]:
                        tingcards += get_effect_card(cs[3][0])
                elif cs[-2] == 1 and cards.count(king_card) == 1:  # 有宝牌时，将对子和搭子、孤张的有效牌都算上
                    for aa in cs[2]:
                        tingcards.append(aa[0])
                    for ab in cs[3]:
                        tingcards += get_effect_card(ab)
                elif cs[-2] == 1 and cards.count(king_card) >= 2:  # 有两张以上宝牌时
                    for aa in cs[2]:
                        tingcards.append(aa[0])
                    for ab in cs[3]:
                        tingcards += get_effect_card(ab)
                    for t1 in cs[-1]:
                        tingcards += get_a_effect_card(t1)
            result = {
                "discard_need": {-1: [list(set(tingcards)), [], value]},
                "play_type": 'PH',
                "xts": 1
            }
        elif i == 1 and xts_list[i] == 1:
            for cs in CS_SSL:
                for efc in [
                    SSL.efc_ssl(cs[0], 0x00) + SSL.efc_ssl(cs[1], 0x10) + SSL.efc_ssl(cs[2], 0x20) + SSL.efc_ssl(cs[3],
                                                                                                                 0x30)]:
                    for card in efc:
                        if card != []:
                            tingcards.append(card[0])
            result = {
                "discard_need": {-1: [list(set(tingcards)), [], value]},
                "play_type": 'SSL',
                "xts": 1
            }
        elif i == 2 and xts_list[i] == 1:
            tingcards = JY.yaojiu
            result = {
                "discard_need": {-1: [tingcards, [], value]},
                "play_type": 'JY',
                "xts": 1
            }
        elif i == 3 and xts_list[i] == 1:
            for t1 in CS_QD[-2]:
                tingcards.append(t1)
            result = {
                "discard_need": {-1: [list(set(tingcards)), [], value]},
                "play_type": 'QD',
                "xts": 1
            }
        if result != {}:
            for card in result['discard_need'][-1][0]:
                result['discard_need'][-1][1].append(LEFT_NUM_V5[translate16_33(card)])
            result_info.append(result)
    return result_info


def get_score_dict(cards, suits, king_card, fei_king, padding=[], max_xts=14, is_recommend=False):
    # 寻找向听数在阈值内的牌型
    PH = PingHu(cards=cards, suits=suits, kingCard=king_card, fei_king=fei_king, padding=padding)
    SSL = ShiSanLan(cards=cards, suits=suits, king_card=king_card, fei_king=fei_king, padding=padding)
    JY = JiuYao(cards=cards, suits=suits, king_card=king_card, fei_king=fei_king, padding=padding)
    QD = Qidui(cards=cards, suits=suits, king_card=king_card, fei_king=fei_king, padding=padding)
    # 组合信息
    CS_PH = PH.pinghu_CS2()
    CS_SSL = SSL.ssl_CS()
    CS_JY = JY.yaojiu_CS()
    CS_QD = QD.qidui_CS()
    # 向听数
    # global ph_dis_effect_cards,ssl_dis_effct_cards,jy_dis_effct_cards,qd_dis_effct_cards
    ph_dis_effect_cards, ssl_dis_effct_cards, jy_dis_effct_cards, qd_dis_effct_cards = {}, {}, {}, {}
    xts_list = [CS_PH[0][-2], CS_SSL[0][-1], CS_JY[-1], CS_QD[-1]]
    # print("xts_list PH,SSL,JY,QD", xts_list)
    logger.info("xts PH,SSL,JY,QD:%s", xts_list)
    xts_list_copy = copy.deepcopy(xts_list)
    xts_list_copy[3] -= 1
    if len(suits) * 3 + len(cards) == 13 and min(
            xts_list_copy) <= 1 and is_recommend:  # 出牌决策中手牌中有13张牌，向听数为1的情况，找出听牌和剩余牌
        result_info = get_tingcards(cards=cards, suits=suits, king_card=king_card)
        return {}, 1, result_info
    min_xts = min(xts_list)
    MJ.min_xts = min_xts
    # if min_xts>max_xts+1: #op中吃碰后向听数增加的情况，特别是打非平胡的牌型
    #     return {cards[-1]:0},min_xts
    type_list = []  # 需搜索的牌型
    for i in range(4):
        if xts_list[i] - 1 <= min_xts:
            type_list.append(i)
    score_list = []
    time_start = time.time()
    time_list = []
    for i in type_list:
        if i == 0:
            search_PH = SearchTree_PH(hand=cards, suits=suits, combination_sets=CS_PH, king_card=king_card,
                                      fei_king=fei_king)
            score_list.append(search_PH.get_discard_score())
            ph_dis_effect_cards = search_PH.ph_dis_effect_cards
        elif i == 1:
            score_list.append(SSL.get_discard_score())
            ssl_dis_effct_cards = SSL.ssl_dis_effct_cards
        elif i == 2:
            raw = JY.get_discard_score()
            # 如果它返回了整数，就把它包装成字典
            if isinstance(raw, int):
                raw = {"score": raw}
            score_list.append(raw)
            jy_dis_effct_cards = JY.jy_dis_effct_cards
        elif i == 3:
            score_list.append(QD.get_discard_score())
            qd_dis_effct_cards = QD.qd_dis_effct_cards
        time_list.append(time.time() - time_start - sum(time_list))
    logger.info("time use%s", time_list)
    score_dict = {}
    for score in score_list:
        for key, val in score.items():
            # 只处理有效牌面（跳过 wrapper key）
            try:
                adjustment = float(value_t1(key)) / (10 ** (min_xts + 1) / 2)
            except KeyError:
                continue

            if key not in score_dict:
                score_dict[key] = val - adjustment
            else:
                score_dict[key] += val
    if king_card in score_dict.keys():  # 飞宝的权重增加
        score_dict[king_card] *= 1.2
    xt_type = ['PH', 'SSL', 'JY', 'QD']
    RENSULT_INFO = []
    need_type = [ph_dis_effect_cards, ssl_dis_effct_cards, jy_dis_effct_cards, qd_dis_effct_cards]
    for i in range(4):
        if xts_list[i] <= min_xts + 1:
            REASON_JSON = {
                'play_type': [],
                'discard_need': {},
                'xts': 14
            }
            REASON_JSON['play_type'] = xt_type[i]
            if i != 3:
                REASON_JSON['xts'] = xts_list[i]
            else:
                REASON_JSON['xts'] = xts_list[i] - 1
            REASON_JSON['discard_need'] = need_type[i]
            for key in REASON_JSON['discard_need']:
                for card in REASON_JSON['discard_need'][key][0]:  # TODO 当card = 0时代表宝吊，考虑是否放入摸牌集合中
                    REASON_JSON['discard_need'][key][1].append(LEFT_NUM_V5[translate16_33(card)])
            RENSULT_INFO.append(REASON_JSON)
    return score_dict, min_xts, RENSULT_INFO


def get_seat_id_list(seat_id):
    if seat_id == 0:
        seats = [0, 1, 2, 3]
    elif seat_id == 1:
        seats = [1, 2, 3, 0]
    elif seat_id == 2:
        seats = [2, 3, 0, 1]
    elif seat_id == 3:
        seats = [3, 0, 1, 2]
    else:
        logger.error("seat_id error=%s", seat_id)
    return seats


def get_RT(hands, discards_op, seat_id, wall, king_card, discards_real, discards):
    # 后面的玩家座位号生成
    seats = get_seat_id_list(seat_id)
    RT1 = [[0] * 34, [0] * 34]
    RT2 = [[0] * 34, [0] * 34]
    RT3 = [[0] * 34, [0] * 34]
    # 生成出牌
    global LEFT_NUM, T_SELFMO, REMAIN_NUM
    REMAIN_NUM = max(1, len(wall))

    w1 = []
    w2 = []
    w3 = []
    if 0 < len(wall):
        w1.append(wall[0])
    if 1 < len(wall):
        w2.append(wall[1])
    if 2 < len(wall):
        w3.append(wall[2])

    # 使用可见信息生成
    LEFT_NUM, _ = trandfer_discards(discards=discards, discards_op=discards_op, handcards=hands[seats[1]])
    LEFT_NUM[translate16_33(pre_king(king_card))] -= 1
    T_SELFMO = [float(i) / REMAIN_NUM for i in LEFT_NUM]
    discards1, _, RENSULT_INFO = get_score_dict(cards=hands[seats[1]] + w1, suits=discards_op[seats[1]],
                                                king_card=king_card, fei_king=discards_real[seats[1]].count(king_card))

    LEFT_NUM, _ = trandfer_discards(discards=discards, discards_op=discards_op, handcards=hands[seats[2]])
    LEFT_NUM[translate16_33(pre_king(king_card))] -= 1
    T_SELFMO = [float(i) / REMAIN_NUM for i in LEFT_NUM]
    discards2, _, RENSULT_INFO = get_score_dict(cards=hands[seats[2]] + w2, suits=discards_op[seats[2]],
                                                king_card=king_card, fei_king=discards_real[seats[2]].count(king_card))

    LEFT_NUM, _ = trandfer_discards(discards=discards, discards_op=discards_op, handcards=hands[seats[3]])
    LEFT_NUM[translate16_33(pre_king(king_card))] -= 1
    T_SELFMO = [float(i) / REMAIN_NUM for i in LEFT_NUM]
    discards3, _, RENSULT_INFO = get_score_dict(cards=hands[seats[3]] + w3, suits=discards_op[seats[3]],
                                                king_card=king_card, fei_king=discards_real[seats[3]].count(king_card))

    sum1 = 1
    for key in discards1.keys():
        sum1 += discards1[key]
    for key in discards1.keys():
        RT1[0][MJ.convert_hex2index(key)] = discards1[key] / sum1

    sum2 = 1
    for key in discards2.keys():
        sum2 += discards2[key]
    for key in discards2.keys():
        RT2[0][MJ.convert_hex2index(key)] = discards2[key] / sum2

    sum3 = 1
    for key in discards3.keys():
        sum3 += discards3[key]
    for key in discards3.keys():
        RT3[0][MJ.convert_hex2index(key)] = discards3[key] / sum3
    return RT1, RT2, RT3


def get_min_xt(cards, suits, king_card, fei_king=0, padding=[]):
    """
    获取最小向听数
    :param cards:
    :param suits:
    :param king_card:
    :return:
    """
    # fei_king=0
    # padding=[]
    # 寻找向听数在阈值内的牌型
    PH = PingHu(cards=cards, suits=suits, kingCard=king_card, fei_king=fei_king, padding=padding)
    SSL = ShiSanLan(cards=cards, suits=suits, king_card=king_card, fei_king=fei_king, padding=padding)
    JY = JiuYao(cards=cards, suits=suits, king_card=king_card, fei_king=fei_king, padding=padding)
    QD = Qidui(cards=cards, suits=suits, king_card=king_card, fei_king=fei_king, padding=padding)
    # 组合信息
    CS_PH = PH.pinghu_CS2()
    CS_SSL = SSL.ssl_CS()
    CS_JY = JY.yaojiu_CS()
    CS_QD = QD.qidui_CS()
    # 向听数

    xts_list = [CS_PH[0][-2], CS_SSL[0][-1], CS_JY[-1], CS_QD[-1]]
    # print "xts_list PH,SSL,JY,QD", xts_list
    # logger.info("xts PH,SSL,JY,QD:%s", xts_list)
    min_xts = min(xts_list)
    return min_xts


def update(cards=[], king_card=None,
           discards=[], discards_real=[], discards_op=[],
           round=0, seat_id=-1, hands=[], wall=[]):
    global T_SELFMO, LEFT_NUM, TIME_START, RT1, RT2, RT3, ROUND, LEFT_NUM_V5
    ROUND = round
    MJ.KING = king_card
    TIME_START = time.time()
    LEFT_NUM_V5, discards_list = trandfer_discards(discards=discards, discards_op=discards_op, handcards=cards)
    # LEFT_NUM_V5[translate16_33(pre_king(king_card))] -= 1  #  宝牌的前一张系统中不会减1

    if True:
        RT1, RT2, RT3 = get_RT(hands=hands, discards_op=discards_op, seat_id=seat_id, wall=wall, king_card=king_card,
                               discards_real=discards_real, discards=discards)
        LEFT_NUM = [0] * 34  # 初始化
        T_SELFMO = [0] * 34
        for card in wall:
            LEFT_NUM[MJ.convert_hex2index(card)] += 1
        REMAIN_NUM = max(1, len(wall))
        T_SELFMO = [float(i) / REMAIN_NUM for i in LEFT_NUM]

        # 对牌墙前2轮牌做分配
        wall_n = []
        for i in [3, 7]:
            if i < len(wall):
                wall_n.append(wall[i])
        for card in wall_n:
            T_SELFMO[MJ.convert_hex2index(card)] = 1


def recommend_card(cards=[], suits=[], king_card=None,
                   discards=[], discards_real=[], discards_op=[], fei_king=0,
                   remain_num=136, round=0, seat_id=-1, hands=[], wall=[]):
    """
    功能：推荐出牌接口
    思路：使用向听数作为牌型选择依据，对最小ｘｔｓ的牌型，再调用相应的牌型类出牌决策
    :param cards: 手牌
    :param suits: 副露
    :param king_card: 宝牌
    :param discards: 弃牌
    :param discards_op: 场面副露
    :param fei_king: 飞宝数
    :param remain_num: 剩余牌
    :return: outCard 推荐出牌
    """
    # logger.info("recommond card start...")
    # 更新全局变量
    global T_SELFMO, LEFT_NUM, TIME_START, RT1, RT2, RT3, ROUND, LEFT_NUM_V5
    ROUND = round
    MJ.KING = king_card
    TIME_START = time.time()
    LEFT_NUM_V5, discards_list = trandfer_discards(discards=discards, discards_op=discards_op, handcards=cards)
    # LEFT_NUM_V5[translate16_33(pre_king(king_card))] -= 1  #  宝牌的前一张系统中不会减1

    if True:
        RT1, RT2, RT3 = get_RT(hands=hands, discards_op=discards_op, seat_id=seat_id, wall=wall, king_card=king_card,
                               discards_real=discards_real, discards=discards)
        LEFT_NUM = [0] * 34  # 初始化
        T_SELFMO = [0] * 34
        for card in wall:
            LEFT_NUM[MJ.convert_hex2index(card)] += 1
        REMAIN_NUM = max(1, len(wall))
        T_SELFMO = [float(i) / REMAIN_NUM for i in LEFT_NUM]

        # 对牌墙前2轮牌做分配
        wall_n = []
        for i in [3, 7]:
            if i < len(wall):
                wall_n.append(wall[i])
        for card in wall_n:
            T_SELFMO[MJ.convert_hex2index(card)] = 1
    score_dict, _, RESULT_INFO = get_score_dict(cards, suits, king_card, fei_king, is_recommend=True)
    discard_need_real = {}
    score_max = 0
    null_set = []
    for result in RESULT_INFO:
        if not result['discard_need']:
            null_set.append(result)
    for result in null_set:
        RESULT_INFO.remove(result)
    for result in RESULT_INFO:
        max_key = -2  # -1 已经作为听牌用了，
        for card in result['discard_need']:
            if result['discard_need'][card][2] > score_max:
                score_max = result['discard_need'][card][2]
                max_key = card
                discard_need_real = {card: result['discard_need'][card]}
        if len(result['discard_need']) == 1 and max_key == -2:
            for key in result['discard_need']:
                result['discard_need'][key][2] = random.randint(15, 20) / 1000.0
                max_key = key
                discard_need_real = {key: result['discard_need'][key]}
        discard_need_real[max_key][1], discard_need_real[max_key][0] = MJ.quick_sort(discard_need_real[max_key][1],
                                                                                     discard_need_real[max_key][0], 0,
                                                                                     len(discard_need_real[max_key][
                                                                                             0]) - 1)
        while len(discard_need_real[max_key][1]) and discard_need_real[max_key][1][-1] == 0:
            discard_need_real[max_key][1].pop()
            discard_need_real[max_key][0].pop()

        discard_need_real[max_key][2] = MJ.get_percentage(discard_need_real[max_key][2])
        result['discard_need'] = discard_need_real
        if result['xts'] == 0:
            result['discard_need'][max_key][0] = [-1]
            result['discard_need'][max_key][1] = [-1]
        score_max = 0
    if score_dict != {}:
        recommend_card = max(score_dict, key=lambda x: score_dict[x])
    else:
        recommend_card = cards[-1]
        logger.error("no card be recommonded,cards=%s,suits=%s,king_card=%s", cards, suits, king_card)
    end = time.time()
    if end - TIME_START > 3:
        logger.error("overtime %s,%s,%s,%s", end - TIME_START, cards, suits, king_card)
    logger.info("recommend_card %s", recommend_card)
    return recommend_card, score_dict, RESULT_INFO


def recommend_op(op_card=None, cards=[], suits=[], king_card=None, discards=[], discards_real=[], discards_op=[],
                 seat_id=-1, out_seat_id=-1, self_turn=False,
                 fei_king=0, isHu=False, round=0, hands=[], wall=[]):
    """
    功能：动作决策接口
    思路：使用向听数作为牌型选择依据，对最小ｘｔｓ的牌型，再调用相应的牌型类动作决策
    :param op_card: 操作牌
    :param cards: 手牌
    :param suits: 副露
    :param king_card: 宝牌
    :param discards: 弃牌
    :param discards_op: 场面副露
    :param canchi: 吃牌权限
    :param self_turn: 是否是自己回合
    :param fei_king: 飞宝数
    :param isHu: 是否胡牌
    :return: [],isHu 动作组合牌，是否胡牌
    """

    # 更新全局变量
    global T_SELFMO, LEFT_NUM, TIME_START, RT1, RT2, RT3
    MJ.KING = king_card
    TIME_START = time.time()
    # 返回的信息
    RESULT_INFO = {
        'op': {
            'operate': [],
            'isHu': False},
        'score_pre': [],
        'score_op': {}
    }

    if isHu:  # 先判断是否弃胡
        # 这里肯定是自己回合，所以除了上面的杠，没有其他操作
        # todo 处理单吊打法。只处理有宝单吊，在其他玩家没有听牌的时候
        # 检测其他玩家是否听牌
        seats = get_seat_id_list(seat_id)
        xts_other = []
        for i in range(1, 4):
            seat = seats[i]
            if len(wall) > i - 1:
                take = [wall[i - 1]]
                padding = []
            else:
                take = []
                padding = [-1]
            xts_other.append(get_min_xt(hands[seat] + take, discards_op[seat], king_card, padding=padding))
        if 0 in xts_other:  # 其他玩家下回合必胡，这里必须先胡牌
            RESULT_INFO['op'] = {'operate': [], 'isHu': True}
            return RESULT_INFO
        else:  # 其他玩家没有胡牌，这里判断是不是需要弃胡胡大番
            if cards.count(king_card) >= 2 and len(wall) >= 4:  # 多张宝牌，能否弃掉一张翻倍
                # 判断弃胡后得分
                cards_ = copy.copy(cards)
                cards_.remove(king_card)
                cards_.append(wall[3])  # 第三张牌
                min_xts_dk = get_min_xt(cards_, suits, king_card)
                if min_xts_dk == 0:  # 如果弃胡后打掉一张宝牌，下次摸牌仍然能够胡牌，这里可以选择弃胡 todo 宝吊不需要再次飞宝
                    RESULT_INFO['op'] = {'operate': [], 'isHu': False}
                    return RESULT_INFO
        RESULT_INFO['op'] = {'operate': [], 'isHu': True}
        return RESULT_INFO

    # 杠操作判断
    if self_turn:
        # 不操作前的向听数
        min_xts_pre = get_min_xt(cards, suits, king_card)
        for card in list(set(cards)):
            if cards.count(card) == 4:  # pinghu qidui jiuyao
                # 暗杠24分
                cards_ = copy.copy(cards)
                while (card in cards_):
                    cards_.remove(card)
                suits_ = MJ.deepcopy(suits)
                suits_.append([card, card, card, card])
                if len(wall) >= 1:  # 牌墙还有牌
                    min_xts = get_min_xt(cards_ + [wall[0]], suits_, king_card)
                    if min_xts <= min_xts_pre + 1:
                        RESULT_INFO['op'] = {'operate': [card, card, card, card], 'isHu': False}
                        return RESULT_INFO
        # 补杠
        for suit in suits:
            if suit[0] == op_card:
                suits_ = MJ.deepcopy(suits)
                suits_.remove(suit)
                suits_.append([suit[0], suit[0], suit[0], suit[0]])
                cards_ = MJ.deepcopy(cards)
                cards_.remove(op_card)
                if len(wall) >= 1:  # 牌墙还有牌
                    min_xts = get_min_xt(cards_ + [wall[0]], suits_, king_card)
                    if min_xts <= min_xts_pre + 1:
                        RESULT_INFO['op'] = {'operate': [suit[0], suit[0], suit[0], suit[0]], 'isHu': False}
                        return RESULT_INFO
    # 明杠
    else:  # 计算不操作的xt
        seats = get_seat_id_list(out_seat_id)
        n_in_wall = seats.index(seat_id) - 1
        cards_ = copy.copy(cards)
        if n_in_wall < len(wall):
            cards_.append(wall)
            padding = []
        else:
            padding = [-1]
        min_xts_pre = get_min_xt(cards, suits, king_card, padding=padding)  # 补一张
        for card in list(set(cards)):
            if cards.count(op_card) == 3 and op_card == card:
                cards_ = copy.copy(cards)
                while (card in cards_):
                    cards_.remove(card)
                suits_ = MJ.deepcopy(suits)
                # suits_.remove([card, card, card])
                suits_.append([card, card, card, card])
                if len(wall) >= 1:
                    min_xts = get_min_xt(cards_ + [wall[0]], suits_, king_card)
                    if min_xts <= min_xts_pre + 1:
                        RESULT_INFO['op'] = {'operate': [card, card, card, card], 'isHu': False}
                        return RESULT_INFO

    # 暗杠补杠牌操作
    canchi = False
    seats = get_seat_id_list(out_seat_id)
    if seats.index(seat_id) == 1:
        canchi = True
    RT1 = [[0] * 34, [0] * 34]  # 危险度表
    RT2 = [[0] * 34, [0] * 34]
    RT3 = [[0] * 34, [0] * 34]

    LEFT_NUM = [0] * 34  # 初始化
    T_SELFMO = [0] * 34
    for card in wall:
        LEFT_NUM[MJ.convert_hex2index(card)] += 1
    REMAIN_NUM = max(1, len(wall))
    T_SELFMO = [float(i) / REMAIN_NUM for i in LEFT_NUM]

    # 计算操作前评估值
    cards_pre = copy.copy(cards)
    index = seats.index(seat_id) - 1
    if len(wall) > index:
        cards_pre.append(wall[index])
        padding = []
    else:
        padding = [-1]
    score_dict_pre, min_xts_pre, result_info_pre = get_score_dict(cards_pre, suits, king_card, fei_king,
                                                                  padding=padding)
    if score_dict_pre != {}:
        score_pre = max(score_dict_pre.values())
        for result in result_info_pre:
            RESULT_JSON = {}
            RESULT_JSON['play_type'] = result['play_type']
            score = 0
            for key in result['discard_need']:
                if result['discard_need'][key][2] > score:
                    score = result['discard_need'][key][2]
            RESULT_JSON['score'] = MJ.get_percentage(score)
            RESULT_JSON['xts'] = result['xts']
            RESULT_INFO['score_pre'].append(RESULT_JSON)
    else:
        score_pre = 0
        RESULT_INFO['score_pre'] = [{
            'play_type': 'PH',
            'score': 0,
            'xts': 14
        }]

    # 计算操作后的评估值
    # 确定可选动作
    # 操作后变量更新，todo 牌墙中我们摸牌的位置会改变，注意修改
    RT1, RT2, RT3 = get_RT(hands=hands, discards_op=discards_op, seat_id=seat_id, wall=wall, king_card=king_card,
                           discards_real=discards_real, discards=discards)
    LEFT_NUM = [0] * 34  # 初始化
    T_SELFMO = [0] * 34
    for card in wall:
        LEFT_NUM[MJ.convert_hex2index(card)] += 1
    REMAIN_NUM = max(1, len(wall))
    T_SELFMO = [float(i) / REMAIN_NUM for i in LEFT_NUM]

    # 对牌墙前2轮牌做分配
    wall_n = []
    for i in [3, 7]:
        if i < len(wall):
            wall_n.append(wall[i])

    for card in wall_n:
        T_SELFMO[MJ.convert_hex2index(card)] = 1

    op_sets = []
    if canchi:
        # 可操作的集合
        if op_card < 0x30:  # 字牌不能吃
            rm_sets = [[op_card - 2, op_card - 1], [op_card - 1, op_card + 1], [op_card + 1, op_card + 2]]
        else:
            rm_sets = []
        for op_set in rm_sets:
            if op_set[0] in cards and op_set[1] in cards:
                op_sets.append(op_set)
        # 碰
        if cards.count(op_card) >= 2:
            op_sets.append([op_card, op_card])
    else:
        if cards.count(op_card) >= 2:
            op_sets.append([op_card, op_card])

    score_set = []
    result_set = []
    for op_set in op_sets:
        cards_ = copy.copy(cards)
        cards_.remove(op_set[0])
        cards_.remove(op_set[1])
        suits_ = MJ.deepcopy(suits)
        suits_.append(sorted(op_set + [op_card]))
        score_dict, _, result_ = get_score_dict(cards=cards_, suits=suits_, king_card=king_card, fei_king=fei_king,
                                                max_xts=min_xts_pre)
        result_set.append(result_)
        if score_dict != {}:
            score = max(score_dict.values())
            score_set.append(score)
    if time.time() - TIME_START > 3:
        logger.warning("op time out %s", time.time() - TIME_START)
    if score_set == []:
        RESULT_INFO['score_op'] = {
            'play_type': ' ',
            'score': 0,
            'xts': 14
        }
    else:
        max_score = max(score_set)
        logger.info("op,max_score=%s,score_pre=%s", max_score, score_pre)
        RESULT_INFO['score_op']['play_type'] = result_set[score_set.index(max_score)][0]['play_type']
        RESULT_INFO['score_op']['score'] = MJ.get_percentage(max_score)
        RESULT_INFO['score_op']['xts'] = result_set[score_set.index(max_score)][0]['xts']
        if max_score > score_pre * 1.05:
            RESULT_INFO['op'] = {'operate': op_sets[score_set.index(max_score)] + [op_card], 'isHu': False}
        else:
            RESULT_INFO['op'] = {'operate': [], 'isHu': False}
            score_op = RESULT_INFO['score_op']['score']
            if max_score < score_pre:
                max_score = score_pre
            RESULT_INFO['score_op']['score'] = MJ.get_percentage(max_score)
            RESULT_INFO['score_pre'][0]['score'] = score_op
    if RESULT_INFO['op']['operate']:
        RESULT_INFO['op']['operate'] = sorted(RESULT_INFO['op']['operate'])
    return RESULT_INFO
