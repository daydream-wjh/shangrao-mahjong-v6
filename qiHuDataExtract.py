#!/usr/bin/env python 
# -*- coding: utf-8 -*-
# @Time    : 2022/7/30 10:49
# @Author  : Joisen
# @File    : test.py.py
import statistics

import ujson as json

# 或者
import os
# import orjson

from feature_extract.cal_xts import *
from shangraoMJ_v6_master.shangraoMJ_v6 import get_score_dict, update, recommend_card


def get_dealer(zhuang_id, high_score_id):
    '''
    :param zhuang_id: 庄家id
    :param high_score_id: 高手玩家id
    :return: 进行位置调整后庄家的位置
    '''
    retList = []
    for i in range(4):
        if zhuang_id == i:
            retList.append(1)
        else:
            retList.append(0)
    return changeSeat(retList, high_score_id)


def self_king_num(king_card, handCards0):
    '''
    :param king_card: 宝牌
    :param handCards0: 当前玩家即高手玩家的手牌
    :return: 返回高手玩家的宝牌数
    '''
    ret_num = 0
    for i in range(len(handCards0)):
        if handCards0[i] == king_card:
            ret_num += 1
    return ret_num


def get_feiKing_num(disCardReal, kingCard):
    '''
    :param disCardReal: 经过位置调整后所有玩家真实丢弃的牌
    :param kingCard: 宝牌
    :return: 返回所有玩家的飞宝数  一维list
    '''
    retList = []
    for discard in disCardReal:
        num = 0
        for i in discard:
            if i == kingCard:
                num += 1
        retList.append(num)
    return retList


# 获取牌墙中剩余的牌
def get_remain_card(discards, fulu, hand_cards):
    '''
    :param hand_cards: 各玩家的手牌
    :param discards: 丢弃的牌(不含副露中的牌)
    :param fulu: 副露
    :return: 牌墙中剩余的牌
    '''
    card_num = 0
    for discard in discards:
        card_num += len(discard)
    for fulu_ in fulu:
        for fl in fulu_:
            card_num += len(fl)
    for hand_card in hand_cards:
        card_num += len(hand_card)

    return 136 - card_num


def generate_all_cards():
    cards_value = [
        1, 2, 3, 4, 5, 6, 7, 8, 9,
        17, 18, 19, 20, 21, 22, 23, 24, 25,
        33, 34, 35, 36, 37, 38, 39, 40, 41,
        49, 50, 51, 52, 53, 54, 55
    ]
    all_cards = []
    for v in cards_value:
        all_cards.extend([v] * 4)
    return all_cards


def get_remain_cards_set(discards, fulu, hand_cards):
    all_cards = generate_all_cards()
    used_cards = []

    for discard in discards:
        used_cards.extend(discard)
    for fulu_ in fulu:
        for fl in fulu_:
            used_cards.extend(fl)
    for hand_card in hand_cards:
        used_cards.extend(hand_card)

    remain_cards = copy.deepcopy(all_cards)
    for card in used_cards:
        if card in remain_cards:
            remain_cards.remove(card)

    return remain_cards


def get_high_score_seatId(player_ids, high_score_id):
    '''
    :param player_ids: 选手id的一维列表
    :param high_score_id: 高分选手的id
    :return: 高分选手的座位号
    '''
    for i in range(len(player_ids)):
        if player_ids[i] == high_score_id:
            return i


def changeSeat(cards, seatId):
    '''
    :param handCards: 所有玩家牌
    :param seatId: 高手玩家的位置
    :return: 返回将高手玩家置为第一位的牌列表
    '''
    ret_list = cards[seatId:] + cards[:seatId]
    return ret_list


def get_json_info_hu(data_dir, store_path):
    global file_num_nh, file_num_h
    # get json file_names
    all_json = os.listdir(data_dir)
    for j_name in all_json:
        j_path = os.path.join(data_dir, j_name)
        with open(j_path, encoding='utf-8') as j:
            try:
                info = json.load(j)
            except (json.JSONDecodeError, ValueError):
                print(f"跳过无效 JSON 文件：{j_path}")
                continue
        # 庄家id
        zhuang_id = info['zhuang_id']
        # 得到宝牌
        king_card = info['king_card']
        # 获取高分选手的位置
        high_score_seatId = get_high_score_seatId(info['players_id'], info['high_score_player_id'])
        if high_score_seatId < len(info["grade"]):
            high_score = info["grade"][high_score_seatId]
        else:
            continue
        # 获得进行位置调整后的庄家位置
        dealer_flag = get_dealer(zhuang_id, high_score_seatId)
        battle_info = info['battle_info']
        # 遍历一个json文件中battle_info的所有动作
        for i in range(len(battle_info)):
            bat_info = battle_info[i]  # 当前动作信息
            # 当前动作是胡牌 且 当前玩家是高手玩家
            if bat_info['action_type'] == 'A' and bat_info['seat_id'] == high_score_seatId:
                # 获取当前动作的手牌信息
                handCards = changeSeat(bat_info['handcards'], high_score_seatId)  # 将高手玩家的牌调整到第一位
                for sublist in handCards:
                    sublist.sort()
                # 获取高手玩家的手牌：
                handCards0 = handCards[0]
                #   将数据写入json文件
                fulu_ = changeSeat(bat_info['discards_op'], high_score_seatId)
                discards = bat_info['discards']
                discards_seq = changeSeat(bat_info['discards_real'], high_score_seatId)
                remain_card_num = get_remain_card(discards, fulu_, handCards)
                self_kingNum = self_king_num(king_card, handCards[0])  # 高手玩家的宝牌数
                fei_king_nums = get_feiKing_num(discards_seq, king_card)
                round_ = bat_info['round']
                storeFile = store_path + 'hu/' + f'hu{file_num_h}.json'
                dir_name = os.path.dirname(storeFile)
                # 如果文件夹不存在则创建文件夹
                if not os.path.exists(dir_name):
                    os.makedirs(dir_name)
                storeDict = {}
                storeDict['handCards0'] = handCards0
                storeDict['handCards'] = handCards
                storeDict['fulu_'] = fulu_
                storeDict['king_card'] = king_card
                storeDict['operate_card'] = battle_info[i - 1]['operate_card']
                storeDict['discards_seq'] = discards_seq
                storeDict['remain_card_num'] = remain_card_num
                storeDict['self_king_num'] = self_kingNum
                storeDict['fei_king_nums'] = fei_king_nums
                storeDict['discards'] = discards
                storeDict['round_'] = round_
                storeDict['dealer_flag'] = dealer_flag
                storeDict['high_score'] = high_score
                wall = get_remain_cards_set(discards, fulu_, handCards)
                _, score_dict, _ = recommend_card(cards=handCards0, suits=fulu_[0], king_card=king_card,
                                                  discards=discards, discards_real=discards_seq, discards_op=fulu_,
                                                  fei_king=fei_king_nums[0], round=round_, seat_id=0, hands=handCards,
                                                  wall=wall)
                hand_strength = sum(score_dict.values())
                storeDict['hand_strength'] = hand_strength
                storeDict['isHu'] = 1  # 胡牌为1
                with open(storeFile, 'w', encoding="utf-8") as fp:
                    json.dump(storeDict, fp, indent=4)
                    file_num_h += 1
                print("ishu", file_num_h)
            # 当前动作为摸牌 且 摸牌后向听数为0 且 且下一个动作不是胡牌 且 当前玩家是高手玩家
            elif bat_info['action_type'] == 'G' and i < len(battle_info) - 1 and battle_info[i + 1][
                'action_type'] != 'A' and bat_info[
                'seat_id'] == high_score_seatId:
                # 当前摸到的手牌不是宝牌
                if bat_info['operate_card'] != king_card:
                    # 将高手玩家的牌调整到第一位
                    handCards = changeSeat(bat_info['handcards'], high_score_seatId)
                    for sublist in handCards:
                        sublist.sort()
                    # 获取高手玩家的手牌：
                    handCards0 = handCards[0]
                    # 高手玩家的副露调整到第一位
                    fulu_ = changeSeat(bat_info['discards_op'], high_score_seatId)
                    catch_card = bat_info['operate_card']
                    handCards0.append(catch_card)
                    # 计算向听数是否为0
                    xts1 = wait_types_comm_king(handCards0, fulu_[0], king_card)
                    xts2 = wait_types_7(handCards0, fulu_[0], king_card)
                    xts4 = wait_types_13(handCards0, fulu_[0], 0)
                    xts5 = wait_types_19(handCards0, fulu_[0], 0)
                    if min(xts1, xts2, xts4, xts5) == 0:
                        #   将数据写入json文件
                        discards = bat_info['discards']
                        discards_seq = changeSeat(bat_info['discards_real'], high_score_seatId)
                        remain_card_num = get_remain_card(discards, fulu_, handCards)
                        self_kingNum = self_king_num(king_card, handCards[0])  # 高手玩家的宝牌数
                        fei_king_nums = get_feiKing_num(discards_seq, king_card)
                        round_ = bat_info['round']
                        storeFile = store_path + 'nhu/' + f'nhu{file_num_nh}.json'
                        dir_name = os.path.dirname(storeFile)
                        # 如果文件夹不存在则创建文件夹
                        if not os.path.exists(dir_name):
                            os.makedirs(dir_name)
                        storeDict = {}
                        storeDict['handCards0'] = handCards0
                        storeDict['handCards'] = handCards
                        storeDict['operate_card'] = catch_card
                        storeDict['fulu_'] = fulu_
                        storeDict['king_card'] = king_card
                        storeDict['discards_seq'] = discards_seq
                        storeDict['remain_card_num'] = remain_card_num
                        storeDict['self_king_num'] = self_kingNum
                        storeDict['fei_king_nums'] = fei_king_nums
                        storeDict['discards'] = discards
                        storeDict['round_'] = round_
                        storeDict['dealer_flag'] = dealer_flag
                        storeDict['high_score'] = high_score
                        wall = get_remain_cards_set(discards, fulu_, handCards)
                        _, score_dict, _ = recommend_card(cards=handCards0, suits=fulu_[0], king_card=king_card,
                                                          discards=discards, discards_real=discards_seq,
                                                          discards_op=fulu_,
                                                          fei_king=fei_king_nums[0], round=round_, seat_id=0,
                                                          hands=handCards,
                                                          wall=wall)
                        hand_strength = sum(score_dict.values())
                        storeDict['hand_strength'] = hand_strength
                        storeDict['isHu'] = 0  # 弃胡为0
                        with open(storeFile, 'w', encoding="utf-8") as fp:
                            json.dump(storeDict, fp, indent=4)
                            file_num_nh += 1
                        print("isnh", file_num_nh)
                # 当前摸到的手牌是宝牌
                else:
                    handCards = changeSeat(bat_info['handcards'], high_score_seatId)
                    for sublist in handCards:
                        sublist.sort()
                    # 获取高手玩家的手牌：
                    handCards0 = handCards[0]
                    self_kingNum = self_king_num(king_card, handCards[0])
                    # 手牌中已有一张宝牌，摸到的牌可以充当癞子牌
                    if self_kingNum > 1:
                        # 高手玩家的副露调整到第一位
                        fulu_ = changeSeat(bat_info['discards_op'], high_score_seatId)
                        catch_card = bat_info['operate_card']
                        handCards0.append(catch_card)
                        # 计算向听数是否为0
                        xts1 = wait_types_comm_king(handCards0, fulu_[0], king_card)
                        xts2 = wait_types_7(handCards0, fulu_[0], king_card)
                        xts4 = wait_types_13(handCards0, fulu_[0], 0)
                        xts5 = wait_types_19(handCards0, fulu_[0], 0)
                        if min(xts1, xts2, xts4, xts5) == 0:
                            #   将数据写入json文件
                            discards = bat_info['discards']
                            discards_seq = changeSeat(bat_info['discards_real'], high_score_seatId)
                            remain_card_num = get_remain_card(discards, fulu_, handCards)
                            fei_king_nums = get_feiKing_num(discards_seq, king_card)
                            round_ = bat_info['round']
                            storeFile = store_path + 'nhu/' + f'nhu{file_num_nh}.json'
                            dir_name = os.path.dirname(storeFile)
                            # 如果文件夹不存在则创建文件夹
                            if not os.path.exists(dir_name):
                                os.makedirs(dir_name)
                            storeDict = {}
                            storeDict['handCards0'] = handCards0
                            storeDict['handCards'] = handCards
                            storeDict['operate_card'] = catch_card
                            storeDict['fulu_'] = fulu_
                            storeDict['king_card'] = king_card
                            storeDict['discards_seq'] = discards_seq
                            storeDict['remain_card_num'] = remain_card_num
                            storeDict['self_king_num'] = self_kingNum
                            storeDict['fei_king_nums'] = fei_king_nums
                            storeDict['discards'] = discards
                            storeDict['round_'] = round_
                            storeDict['dealer_flag'] = dealer_flag
                            storeDict['high_score'] = high_score
                            wall = get_remain_cards_set(discards, fulu_, handCards)
                            _, score_dict, _ = recommend_card(cards=handCards0, suits=fulu_[0], king_card=king_card,
                                                              discards=discards, discards_real=discards_seq,
                                                              discards_op=fulu_,
                                                              fei_king=fei_king_nums[0], round=round_, seat_id=0,
                                                              hands=handCards,
                                                              wall=wall)
                            hand_strength = sum(score_dict.values())
                            storeDict['hand_strength'] = hand_strength
                            storeDict['isHu'] = 0  # 弃胡为0
                            with open(storeFile, 'w', encoding="utf-8") as fp:
                                json.dump(storeDict, fp, indent=4)
                                file_num_nh += 1
                            print("isnh", file_num_nh)
                    # 刚摸到的宝牌下一圈才能当成宝调
                    elif self_kingNum == 1:
                        # 高手玩家的副露调整到第一位
                        fulu_ = changeSeat(bat_info['discards_op'], high_score_seatId)
                        catch_card = bat_info['operate_card']
                        handCards0.append(catch_card)
                        # 计算向听数是否为0
                        xts1 = wait_types_comm_king(handCards0, fulu_[0], 0)
                        xts2 = wait_types_7(handCards0, fulu_[0], 0)
                        # xts3 = wait_types_haohua7(handCards0, fulu_[0], king_card)
                        xts4 = wait_types_13(handCards0, fulu_[0], 0)
                        xts5 = wait_types_19(handCards0, fulu_[0], 0)
                        if min(xts1, xts2, xts4, xts5) == 0:
                            #   将数据写入json文件
                            discards = bat_info['discards']
                            discards_seq = changeSeat(bat_info['discards_real'], high_score_seatId)
                            remain_card_num = get_remain_card(discards, fulu_, handCards)
                            fei_king_nums = get_feiKing_num(discards_seq, king_card)
                            round_ = bat_info['round']
                            storeFile = store_path + 'nhu/' + f'nhu{file_num_nh}.json'
                            dir_name = os.path.dirname(storeFile)
                            # 如果文件夹不存在则创建文件夹
                            if not os.path.exists(dir_name):
                                os.makedirs(dir_name)
                            storeDict = {}
                            storeDict['handCards0'] = handCards0
                            storeDict['handCards'] = handCards
                            storeDict['operate_card'] = catch_card
                            storeDict['fulu_'] = fulu_
                            storeDict['king_card'] = king_card
                            storeDict['discards_seq'] = discards_seq
                            storeDict['remain_card_num'] = remain_card_num
                            storeDict['self_king_num'] = self_kingNum
                            storeDict['fei_king_nums'] = fei_king_nums
                            storeDict['discards'] = discards
                            storeDict['round_'] = round_
                            storeDict['dealer_flag'] = dealer_flag
                            storeDict['high_score'] = high_score
                            wall = get_remain_cards_set(discards, fulu_, handCards)
                            _, score_dict, _ = recommend_card(cards=handCards0, suits=fulu_[0], king_card=king_card,
                                                              discards=discards, discards_real=discards_seq,
                                                              discards_op=fulu_,
                                                              fei_king=fei_king_nums[0], round=round_, seat_id=0,
                                                              hands=handCards,
                                                              wall=wall)
                            hand_strength = sum(score_dict.values())
                            storeDict['hand_strength'] = hand_strength
                            storeDict['isHu'] = 0  # 弃胡为0
                            with open(storeFile, 'w', encoding="utf-8") as fp:
                                json.dump(storeDict, fp, indent=4)
                                file_num_nh += 1
                            print("isnh", file_num_nh)
    print('文件数：不胡', file_num_nh, '->胡', file_num_h)


if __name__ == '__main__':
    file_num_nh = 0
    file_num_h = 0
    file_path = '/home/zonst/wjh/srmj/data/all/'
    store_path_hu = '/home/zonst/wjh/srmj/data/all/output/'
    for folder in os.listdir(file_path):
        try:
            folder_num = int(folder)
        except ValueError:
            # Skip folders that are not purely numeric
            continue
        if 0 <= folder_num <= 60:  # 提取编号为0-30文件夹的数据
            folder_path = file_path + folder + '/'
            if os.path.isdir(folder_path):
                print("处理文件夹:", folder_path)
                get_json_info_hu(folder_path, store_path_hu)
