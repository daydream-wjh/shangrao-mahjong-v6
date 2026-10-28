# qihu

上饶麻将 AI 的**第二代：v6 规则引擎 + 深度学习模型训练**。

仓库名 `qihu` 指"弃胡"（能胡的时候要不要胡、以及配套的弃牌/出牌决策）。内容分两块：

1. `shangraoMJ_v6_master/` —— v6 规则引擎，是 v5（`majiang` 仓库）的升级版；
2. 根目录的 `train_*.py` / `*DataExtract.py` / `resnet*.py` / `dataset.py` —— 用 PyTorch
   训练"是否弃胡"的二分类模型、局面分数预测模型，以及吃/碰/弃牌三个动作模型。

原仓库**没有 README**，本文件内容全部由源码整理而来。文件头署名信息保留如下：
`__init__.py` 为 `@Author: Zou`（2021/7/13），`shangraoMJ_v6.py` 为 `@Author: Ren`（2020/12/24，
注明 2021.9.14 刘鑫鑫改造为返回完整 JSON 信息），`qiHuDataExtract.py` / `pong_*.py` 为 `@Author: Joisen`（2022）。

## 项目简介

v6 引擎做的事和 v5 一样：给手牌、副露、宝牌、场面弃牌，算出打哪张、要不要吃碰杠胡。
区别在于 v6 是**全信息版本**——推荐接口除了自己的牌，还接收 `hands`（四家手牌）和 `wall`（牌墙），
用来算"对手手里还有哪些牌 / 牌墙里还有哪些牌"的概率表，从而把"这张牌对别人有多危险"
和"我下一张能摸到什么"都算进去。这让它适合做**离线数据生成与评估**（比如给模型造训练样本、
建立对手模型），而不是只依赖可见信息的纯线上接口。

深度学习部分是围绕"要不要弃胡"这个具体决策展开的：

- 用生产对局 JSON 里**高手玩家**的动作切样本（`qiHuDataExtract.py`），
  胡了记为 `hu/`，没胡（放弃胡）记为 `nhu/`；
- 特征沿用 Suphx 那套 4×9 牌面卷积编码（`feature_extract_me.py`），再把"分数预测模型"输出的一路
  标量铺成 4×9 通道拼进去，共 90 通道；
- 网络是 `ResNet50NoPool`（`resnet.py`），`BCEWithLogitsLoss` 二分类，输出"该不该胡"。

## 主要功能

### 一、v6 规则引擎

| 功能 | 实现 |
| --- | --- |
| 胡牌拆分 / 向听数 | `PingHu.pinghu_CS2()`（v6 新增 `is_ting` 参数）、`Qidui`、`ShiSanLan`、`JiuYao` |
| 番型 | `Fan_PH.fanDetect()`（碰碰胡 / 清一色 / 飞宝 / 宝还原，基础 4 分翻倍） |
| 出牌评分 | `SearchTree_PH.get_discard_score()`、`get_score_dict()` |
| **对手剩余牌概率表** | `get_RT()`：按座位算 RT1/RT2/RT3 三张表；`T_SELFMO` 按牌墙算自摸概率，并把牌墙第 4、8 张概率置 1 |
| **听牌识别** | `get_tingcards()`：13 张手牌且最小向听数 ≤1 时，直接返回所有听牌张与剩余张数 |
| **JSON 化推荐理由** | `get_score_dict()` 返回 `(score_dict, min_xts, RESULT_INFO)`，`RESULT_INFO` 形如 `{"play_type": "PH/SSL/JY/QD", "xts": n, "discard_need": {牌: [[需要牌], [剩余张数], 概率]}}` |
| 推荐出牌 / 操作 | `recommend_card()` / `recommend_op()`，按 `get_percentage()` 归一化成概率 |
| 线上接口适配 | `recommend.py`：`RecommendCard_shangraoMJ_v6(input)` / `RecommendOprate_shangraoMJ_v6(input)`，带 logging 记录每次输入输出 |

### 二、深度学习部分

| 脚本 | 作用 |
| --- | --- |
| `qiHuDataExtract.py` | 从原始对局 JSON 生成弃胡样本：定位高手玩家、做座位对齐（`changeSeat`）、补宝牌数/飞宝数/剩余牌，调 v6 引擎算 `hand_strength`，输出 `hu/`、`nhu/` 两类样本 |
| `discardDataExtract.py` | 同上，生成**弃牌**（出牌）动作的样本，含 `can_eat` / `can_pong` / `get_chi_position` 等可行性判定 |
| `feature_extract_me.py` | 特征提取：手牌 4 通道、吃 4×4×9、碰/杠各 1×4×9、弃牌 4×9、未出现牌 4×9、宝牌 4×9；`calculate_feature` 拼成 (C,4,9) 张量 |
| `feature_extract/` | 早期特征版本：`feature_extract.py`（Suphx 原始 4×9 编码 `suphx_cards_feature_code`、`card_preprocess_sr_suphx`）、`cal_xts.py`（各类牌型向听数）|
| `dataset.py` | `HuDataset`（图像特征 + `isHu` 标签）、`ScoreDataset`（图像特征 + `high_score` 标签），一次性把整个目录的 JSON 读进内存 |
| `resnet.py` / `resnet2.py` | `ResNet50NoPool`（去掉全局池化的 ResNet50，输出 4×9 特征图），两份几乎完全相同 |
| `train_qihu_model.py` | 弃胡二分类训练主脚本：数据 = hu + nhu 混合、9:1 切分、`BCEWithLogitsLoss`、30 轮、双卡 `DataParallel`、按准确率打印、存 `./model/model{i}.pth` |
| `test_score_model.py` | 用 `resnet2` 做弃胡模型的评测脚本（结构与训练脚本基本相同） |
| `train_score_predict.py` | 局面分数回归：`ScoreDataset` + `ResNet50NoPool`，`MSELoss`、`ReduceLROnPlateau`、TensorBoard 记录、200 轮 |
| `pong_model.py` / `pong_train_eval.py` | 碰牌决策模型：`Model_Me`（418→256→…→64，FC 到 34）与 `ResNet`，`CrossEntropyLoss`，用 `imblearn.RandomUnderSampler` 处理正负样本不均衡 |
| `load_model.py` | 只有 3 行（import torch + import ResNet50NoPool），实际没有加载逻辑 |
| `dataproccess.py` | 空文件（0 行） |

### 三、历史实验目录（保留原样）

- `works/`：2022 年 6-8 月的第一轮尝试——`works/eat/`（吃：`Net` / `ResNet` / `Model_Me` 三种结构）、
  `works/pong/`、`works/discard/`（含 `hzp_DisModel.py`），跑出过一批 TensorBoard events；
- `extend_work/`：第二轮——吃用 `DenseNet121`、弃牌用 `densenet.py` / `model_1.py`，数据路径是
  Windows 下的 `D:\ML\extend_work\...`；
- `mah_tool/so_lib/`：上饶麻将历史引擎的合集——`lib_MJ.py`（v5 底层库）、
  `shangraoMJ_v2.py`（5709 行，2020 年的"金币场版本"搜索树引擎，类名 `SearchTree/CatchNode/OutNode`）、
  `opp_srmj.py`（`DefendModel` 对手建模）、`sr_xt_ph.py`、`fan_cal.py`；
- `mah_tool/suphx_extract_features/`：`search_tree_ren.py`（`SearchInfo.getSearchInfo` 封装，
  从 v2 引擎拿"牌型 + 推荐牌 + 番型"）、`tool.py`。

## 技术栈 / 依赖

- **Python 3**（`train_qihu_model.py` 用了 f-string、`from PIL.ImageOps import expand` 等 py3 语法）。
- 规则引擎部分纯标准库（`copy` / `time` / `random` / `logging` / `itertools` / `datetime`）。
- 深度学习与数据处理需要（**仓库没有 requirements.txt，版本从 import 与 API 用法推断**）：

  | 包 | 依据 |
  | --- | --- |
  | `torch` | 全部模型与训练脚本；用到 `torch.optim.AdamW`、`DataParallel`、`torch.utils.tensorboard.SummaryWriter` |
  | `torchvision` | `pong_train_eval.py` 里 `import torchvision.models as models` |
  | `numpy` | `dataset`/特征提取 |
  | `tqdm` | 训练进度条 |
  | `imblearn`（imbalanced-learn） | `pong_train_eval.py` 的 `RandomUnderSampler` |
  | `ujson` | `qiHuDataExtract.py` 快速读 JSON |
  | `pandas` | `feature_extract/` 下的测试脚本 |
  | `requests` | 只有 `shangraoMJ_v6_master/recommend.py` 顶层 import（文件内未实际调用），不装则无法 import 该适配层 |
  | `Pillow` | `train_qihu_model.py` / `test_score_model.py` 里残留 `from PIL.ImageOps import expand`（未使用） |

- 显存/卡数：训练脚本写死双卡 `DataParallel(device_ids=[0, 1])`，单卡机器需要改。

## 目录结构

```
qihu/
├── shangraoMJ_v6_master/     # v6 规则引擎（唯一"产品代码"目录）
│   ├── shangraoMJ_v6.py      #   主引擎：牌型类 + 搜索树 + get_RT/get_tingcards + recommend_card/op
│   ├── lib_MJ.py             #   底层牌库：牌值转换、花色拆分、t1/t2/t3 组合表、快速胡牌
│   └── recommend.py          #   线上接口适配（输入 dict → 引擎，带 logging）
├── qiHuDataExtract.py        # 弃胡样本生成（高手玩家动作 → hu/nhu 样本）
├── discardDataExtract.py     # 弃牌样本生成（含吃/碰可行性判定）
├── feature_extract_me.py     # Suphx 风格 4×9 卷积特征（当前主用）
├── feature_extract/          # 早期特征版本 + 向听数工具
├── dataset.py                # HuDataset / ScoreDataset
├── resnet.py, resnet2.py     # ResNet50NoPool（两份重复）
├── train_qihu_model.py       # 弃胡二分类训练
├── test_score_model.py       # 弃胡模型评测
├── train_score_predict.py    # 局面分数回归训练
├── pong_model.py, pong_train_eval.py   # 碰牌模型与训练
├── load_model.py (3 行), dataproccess.py (空), resnet2.py(重复)   # 半成品/占位
├── mah_tool/
│   ├── so_lib/               # 历史引擎合集：lib_MJ / shangraoMJ_v2(金币场版) / opp_srmj(对手建模) / sr_xt_ph / fan_cal
│   └── suphx_extract_features/  # search_tree_ren(SearchInfo) / tool
├── works/                    # 2022 年第一轮实验：eat / pong / discard + TensorBoard events
└── extend_work/              # 第二轮实验：eat(DenseNet121) / discard(densenet) / pong + events
```

## 快速开始

### 1. 只跑 v6 规则引擎（无需 GPU、无需数据）

引擎用平铺 import（`from shangraoMJ_v6_master import lib_MJ as MJ`），要把仓库根目录放进 `sys.path`：

```python
import sys
sys.path.insert(0, '.')
from shangraoMJ_v6_master import shangraoMJ_v6 as MJ6

# 牌值：万 1-9、条 17-25、筒 33-41、字 49-55
# （代码内部是十进制整数，按 16 进制读即牌号：0x11 = 17、0x21 = 33、0x31 = 49）
cards   = [0x01, 0x02, 0x03, 0x11, 0x12, 0x13, 0x21, 0x21, 0x21, 0x31, 0x31, 0x05, 0x06]
suits   = []        # 副露
king    = 0x05      # 宝牌

# 只要评分：返回 (score_dict, min_xts, RESULT_INFO)
score_dict, min_xts, info = MJ6.get_score_dict(cards, suits, king, fei_king=0)

# 要推荐出牌：需要 hands / wall 才能算 RT 表；没有全信息时传空列表
card, score_dict, info = MJ6.recommend_card(
    cards=cards, suits=suits, king_card=king,
    discards=[[], [], [], []], discards_real=[[], [], [], []], discards_op=[[], [], [], []],
    fei_king=0, remain_num=136, round=5, seat_id=0,
    hands=[[], [], [], []], wall=[])
print(card)
```

也可以直接用 `recommend.py` 的接口形态（入参就是线上传的那份 dict；
该文件顶层 `import requests`，但全文件没用到 requests，装一个只为能 import）：

```python
# pip install requests
from shangraoMJ_v6_master import recommend
result = recommend.RecommendCard_shangraoMJ_v6({
    'seat_id': 0, 'catch_card': 0x05, 'king_card': 0x05, 'fei_king': 0,
    'user_cards': {'hand_cards': [0x01, 0x02, 0x03, 0x11, 0x12, 0x13, 0x21, 0x21, 0x21, 0x31, 0x31, 0x05, 0x06],
                   'operate_cards': []},
    'discards': [[], [], [], []], 'discards_real': [[], [], [], []], 'discards_op': [[], [], [], []],
    'remain_num': 136, 'round': 5, 'hands': [[], [], [], []], 'wall': [],
})
print(result)   # [{play_type, xts, discard_need: {...}}, ...]
```

### 2. 训练弃胡模型（需要自己的数据 + GPU）

```bash
pip install torch torchvision numpy tqdm ujson imbalanced-learn pandas requests
python qiHuDataExtract.py     # 1) 原始对局 JSON → hu/ 与 nhu/ 样本目录
python train_qihu_model.py    # 2) 训练，权重存 ./model/model{i}.pth
```

**已知问题（代码现状，如实记录）**

- 所有训练/数据脚本都**硬编码了服务器绝对路径**，必须改：
  `train_qihu_model.py` / `test_score_model.py` → `/home/zonst/wjh/srmj/data/all/output/{hu,nhu}`；
  `train_score_predict.py` 同上；`pong_train_eval.py` → `/home/tonnn/.nas/wjh/qihu/hu/hu/{hu,nhu}`；
  `dataset.py` 的 `__main__` 同理；`extend_work/eat/train_eval.py` → `D:\ML\extend_work\eat\train\`。
- `train_qihu_model.py` 里加载分数模型用的是硬编码权重 `/home/zonst/wjh/srmj/model/model_epoch50.pth`，
  **该权重不在仓库里**，缺它就跑不起来（分数通道是输入特征的一部分）。
- 原始对局 JSON（含 `battle_info` / `grade` / `high_score_player_id` 等字段）**没有入库**，
  `qiHuDataExtract.py` / `discardDataExtract.py` 无法端到端复现。
- 训练脚本写死 `nn.DataParallel(device_ids=[0, 1])`，单卡要改成 `[0]`。
- 仓库里有一批 TensorBoard `events.out.tfevents.*`（`works/`、`extend_work/`）被提交进来，
  是历史训练曲线，无法还原对应代码版本。
- `resnet.py` 与 `resnet2.py` 内容几乎一致、`model.py` / `model_1.py` / `eatModel*.py` 多版本并存，
  没有说明哪个是最终采用的；`load_model.py`（3 行）与 `dataproccess.py`（0 行）是空壳。
- `shangraoMJ_v6_master/recommend.py` 顶层 `import requests` 但未使用，纯 import 也要装；
- 没有 `requirements.txt`、没有测试、没有 LICENSE 文件。

## 核心模块说明

**`get_RT()` —— v6 相对 v5 最关键的新增**
输入四家手牌 `hands`、牌墙 `wall`、场面副露与真实弃牌，按 `get_seat_id_list(seat_id)` 得到相对座位顺序，
产出 `RT1/RT2/RT3` 三张 34×2 的表（下一家/对家/上家的出牌倾向或剩余牌概率），
再与 `T_SELFMO`（牌墙中各牌概率，取 `wall` 计数 / 剩余张数，并把牌墙第 4、8 张概率置 1）一起
进入搜索树评分。注释里保留了大量"某宝牌当宝还原"的统计表，说明这套表是用真实对局统计出来的。

**`get_score_dict()`**
先各算四种牌型的 `xts_list = [PH, SSL, JY, QD]`（七对要 `-1` 修正），
只对 `xts <= min_xts + 1` 的牌型建搜索树；每张牌的评分再减去 `value_t1(key) / 10**(min_xts+1) / 2`
的向听惩罚；宝牌评分 `*1.2`；同时把每种牌型的 `*_dis_effect_cards`（有效牌 → 需要牌 / 剩余张数）
打包进 `RESULT_INFO` 返回。13 张手牌、向听数 ≤1 且 `is_recommend=True` 时**走捷径**直接调 `get_tingcards()`。

**`get_tingcards()`**
用 `pinghu_CS2(is_ting=True)` 判"缺将牌 / 将牌已定"两种情况，枚举能胡的牌；
注意这里对分数用了 `random.randint(300, 400)` / `random.randint(200, 250)` 填充——
**不是真实评估值**，只是为了让听牌建议排在最前面。

**特征 `card_preprocess()`（`feature_extract_me.py`）**
按 Suphx 的思路把局面铺成 4×9 的牌面网格：
高手手牌 4 通道、每个玩家吃的牌 4×4×9、碰/杠各 1×4×9（逐玩家提取后堆叠）、弃牌 4×9、
未出现的牌 4×9、宝牌 4×9、飞宝 `extra_feature_encode_4_9`。
`calculate_feature_score()` 则只保留前 88 通道，供分数模型使用。

**训练循环（`train_qihu_model.py`）**
每步先跑冻结的分数模型两次（`discard_flag=1` / `0`），用两者差值 `score2 - score1` 作为"这一手值多少分"
的一路标量，`expand(-1, -1, 4, 9)` 成 4×9 通道拼到 88 通道特征后面得到 90 通道，
再送进 `ResNet50NoPool(1)` 做二分类；`BCEWithLogitsLoss` + `AdamW(lr=1e-3, weight_decay=0.01)`，
30 轮，逐轮打印训练/验证准确率。

## 与同系列仓库的关系

```
majiang（v5 规则引擎，2021）
    └── qihu（本仓库，v6 规则引擎 + 对手剩余牌概率建模 + 弃胡/分数/吃碰模型训练，2021-2022，2025-04 最后一次提交）
          ├── scmj（四川麻将分支，里面直接带了 shangraoMJ_v6_master/ 的副本，diff 仅 102 行）
          └── mahjongRL（2024，把 v5 库搬进 mah_lib/，换成 gym + PPO 的强化学习路线）
```

- v6 与 v5 的类结构一一对应（`PingHu` / `SearchTree_PH` / `Qidui` / `ShiSanLan` / `JiuYao` / `Fan_PH`），
  v6 新增 `get_RT` / `get_tingcards` / `get_min_xt` / `update` / `get_effect_card`，
  并把 `recommend_card` 的返回值从"一张牌"改成 `(card, score_dict, result_info)`；
- `mah_tool/so_lib/shangraoMJ_v2.py` 是更早的 2020 年引擎（金币场版本），
  与 v5/v6 的"组合树 + 有效牌"是完全不同的实现路线（`SearchTree` / `CatchNode` / `OutNode`），
  在本仓库里主要作为 `search_tree_ren.SearchInfo` 的依赖；
- 本仓库的 `shangraoMJ_v6_master/` 被 `scmj` 原样复制过去当"上饶"分支，说明 v6 是这条线的定稿；
- 后续 `mahjongRL` 选择了另一条路（不训练离线分类器，而是搭 gym 环境做在线策略学习），
  两者互补：本仓库出的是"专家动作分类器 + 分数模型"，`mahjongRL` 出的是"策略网络训练骨架"。

## 已知限制 / TODO

- **数据与权重都不在库里**：训练所需的原始对局 JSON、`model_epoch50.pth` 分数模型权重、
  训练好的 `model{i}.pth` 全部缺失，仓库只是"代码 + 历史实验"；
- `hands` / `wall` 这两个字段意味着 v6 的推荐依赖**全信息**（四家手牌 + 牌墙），
  纯可见信息场景下要传空列表，此时 `get_RT` 的概率表退化为均匀分布，效果会明显下降；
- `get_tingcards()` 里的评分是 `random.randint` 占位，不是模型或规则算出来的；
- 实验目录（`works/`、`extend_work/`）与主代码混在一起，路径一半 Linux（`/home/zonst`、`/home/tonnn`）
  一半 Windows（`D:\ML`），说明经历过多次迁移；
- 弃胡二分类的数据集是"高手玩家实际动作"，存在明显类别不均衡（`hu` 远少于 `nhu`），
  当前脚本没有做重采样（只有碰牌模型用了 `RandomUnderSampler`）；
- 训练脚本把分数模型当冻结模块串在特征里，两步训练没有联合优化；
- 无 `requirements.txt` / 无测试 / 无 LICENSE / 无 CI。
