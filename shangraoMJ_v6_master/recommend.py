# -*- coding: utf-8 -*-
import random
import requests
import time
import logging
import datetime
import shangraoMJ_v6 as shangraoMJ_v6

MOP_NONE = -1
MOP_PASS = 0
MOP_LCHI = 1
MOP_MCHI = 2
MOP_RCHI = 3
MOP_PENG = 4
MOP_MGANG = 5
MOP_AGANG = 6
MOP_BGANG = 7

# 日志输出
logger = logging.getLogger("shangraoMJ_log_recommond")
logger.setLevel(level=logging.DEBUG)
time_now = datetime.datetime.now()

logger.info("shangraoMJ recommond compile finished...")


def RecommendCard_shangraoMJ_v6(input={}):
    user_cards = input.get('user_cards', {})
    catch_card = input.get('catch_card', 0)
    king_card = input.get('king_card', 0)
    fei_king = input.get('fei_king', 0)
    seat_id = input.get('seat_id', 0)
    discards = input.get('discards', [])
    discards_real = input.get('discards_real', [])
    discards_op = input.get('discards_op', [])
    remain_num = input.get('remain_num', 136)

    hands = input.get('hands', [])
    wall = input.get('wall', [])

    round = input.get('round', [])
    hand_cards = user_cards.get('hand_cards', [])  # 手牌
    operate_cards = user_cards.get('operate_cards', [])  # 副露
    hand_cards.sort()
    [e.sort() for e in operate_cards]
    n = 0
    n += len(wall)
    for i in hands:
        n += len(i)
    for i in discards:
        n += len(i)
    for i in discards_op:
        for j in i:
            n += len(j)
    print(n)
    recommend_card, score_dict, result_info = shangraoMJ_v6.recommend_card(cards=hand_cards, suits=operate_cards,
                                                                           king_card=king_card,
                                                                           discards=discards,
                                                                           discards_real=discards_real,
                                                                           discards_op=discards_op, fei_king=fei_king,
                                                                           remain_num=remain_num, round=round,
                                                                           seat_id=seat_id, hands=hands, wall=wall)
    logger.info("out_cards: %s" % str(input))
    logger.info("result_info: %s", result_info)
    return result_info


def RecommendOprate_shangraoMJ_v6(input={}):
    user_cards = input.get('user_cards', {})
    out_card = input.get('out_card', 0)
    king_card = input.get('king_card', 0)
    fei_king = input.get('fei_king', 0)
    discards_op = input.get('discards_op', [])
    discards_real = input.get('discards_real', [])
    remain_num = input.get('remain_num', 0)
    isHu = input.get('isHu', False)
    seat_id = input.get('seat_id', 0)
    out_seat_id = input.get('out_seat_id', 0)
    discards = input.get('discards', [])
    round = input.get('round', 0)

    hands = input.get('hands', [])
    wall = input.get('wall', [])

    hand_cards = user_cards.get('hand_cards', [])
    operate_cards = user_cards.get('operate_cards', [])
    hand_cards.sort()
    [e.sort() for e in operate_cards]
    result_info = shangraoMJ_v6.recommend_op(op_card=out_card, cards=hand_cards, suits=operate_cards,
                                             king_card=king_card, discards=discards, discards_real=discards_real,
                                             discards_op=discards_op,
                                             seat_id=seat_id, out_seat_id=out_seat_id,
                                             self_turn=(len(hand_cards) % 3 == 2),
                                             fei_king=fei_king, isHu=isHu, round=round, hands=hands, wall=wall)
    logger.info("operate:%s" % str(input))
    logger.info("result_info:%s " % str(result_info))
    return result_info


if __name__ == '__main__':
    request = {"catch_card": 255, "discards": [[], [], [], []],
               "discards_op": [[], [], [], [[54, 54, 54]]], "discards_real": [[54], [], [], []], "fei_king": 0,
               "hands": [[3, 4, 5, 23, 25, 34, 36, 36, 37, 49, 49, 52, 55],
                         [1, 5, 9, 9, 18, 20, 22, 23, 33, 38, 38, 40, 55],
                         [6, 6, 9, 17, 24, 36, 39, 40, 51, 51, 53, 53, 55],
                         [2, 17, 23, 25, 34, 35, 40, 41, 50, 52, 53]], "king_card": 20, "need_pos": True, "round": 0,
               "seat_id": 3, "user_cards": {"hand_cards": [2, 17, 23, 25, 34, 35, 40, 41, 50, 52, 53],
                                            "operate_cards": [[54, 54, 54]]},
               "wall": [2, 22, 25, 25, 17, 54, 21, 33, 39, 2, 36, 41, 53, 52, 5, 24, 37, 19, 22, 39, 35, 19, 7, 24, 49,
                        50, 33, 41, 7, 9, 21, 6, 38, 34, 34, 4, 40, 8, 8, 33, 39, 3, 55, 20, 1, 3, 23, 41, 52, 4, 18,
                        50, 20, 8, 4, 37, 35, 7, 18, 49, 8, 35, 37, 38, 51, 21, 22, 17, 50, 21, 18, 2, 6, 7, 19, 20, 1,
                        5, 1, 51, 3, 24, 19]}

    outs = RecommendCard_shangraoMJ_v6(request)
    print(outs)
    for out in outs:
        print(out)

    request_op = {
        "discards": [[53, 23, 3, 5, 9, 33, 51, 52, 54], [51, 50, 55, 7, 25, 9, 25, 41, 50], [23, 55, 7, 25, 53, 50, 51],
                     [53, 23, 7, 55, 17, 9, 52, 49]],
        "discards_op": [[[36, 36, 36]], [], [], [[40, 40, 40]]],
        "discards_real": [[53, 23, 3, 5, 9, 33, 51, 52, 54], [51, 50, 55, 7, 25, 9, 25, 41, 50],
                          [40, 23, 55, 7, 25, 53, 50, 51, 36], [53, 23, 7, 55, 17, 9, 52, 49]],
        "fei_king": 0,
        "hands": [[8, 22, 22, 24, 24, 33, 37, 38, 38, 50], [4, 6, 8, 20, 21, 33, 34, 34, 37, 3, 38, 20, 35],
                  [1, 5, 21, 22, 24, 34, 35, 17, 18, 34, 41, 41, 35], [2, 18, 36, 39, 54, 54, 1, 18, 33, 54]],
        "isHu": False, "king_card": 33,
        "need_pos": True,
        "out_card": 54,
        "out_seat_id": 0,
        "remain_num": [1, 52, 19, 7, 21, 49, 49, 20, 3, 8, 37, 6, 2, 20, 37, 3, 55, 52, 39, 19, 38, 2, 2, 17, 25, 39,
                       23, 19, 4, 40, 8, 49, 5, 17, 39, 4, 1, 9, 6, 51, 24, 6, 21, 4, 35, 22, 5, 18, 19, 53, 41],
        "round": 8, "seat_id": 3,
        "user_cards": {"hand_cards": [2, 18, 36, 39, 54, 54, 1, 18, 33, 54], "operate_cards": [[40, 40, 40]]},
        "wall": [1, 52, 19, 7, 21, 49, 49, 20, 3, 8, 37, 6, 2, 20, 37, 3, 55, 52, 39, 19, 38, 2, 2, 17, 25, 39, 23, 19,
                 4, 40, 8, 49, 5, 17, 39, 4, 1, 9, 6, 51, 24, 6, 21, 4, 35, 22, 5, 18, 19, 53, 41]}

    print("op=", RecommendOprate_shangraoMJ_v6(request_op))
