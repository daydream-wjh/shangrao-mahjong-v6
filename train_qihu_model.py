import os

import torch.backends.cudnn as cudnn
from PIL.ImageOps import expand
from torch.optim import AdamW
from torch.utils.data import random_split, DataLoader
from tqdm import tqdm

from dataset import *
from extend_work.discard.densenet import *
from resnet2 import ResNet50NoPool
from resnet import ResNet50NoPool as ResNet50

seed = 42
torch.manual_seed(seed)
import random

np.random.seed(seed)
random.seed(seed)
cudnn.benchmark = True

if __name__ == '__main__':
    # 设置启用设备
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    # 数据路径
    hu_dir = '/home/zonst/wjh/srmj/data/all/output/hu'
    nhu_dir = '/home/zonst/wjh/srmj/data/all/output/nhu'

    # 加载数据集
    hu_dataset = HuDataset(hu_dir)
    nhu_dataset = HuDataset(nhu_dir)
    print(len(hu_dataset))
    print(len(nhu_dataset))

    # 设置划分比例
    train_ratio = 0.9

    # 计算训练和验证集的大小
    hu_train_size = int(train_ratio * len(hu_dataset))
    hu_val_size = len(hu_dataset) - hu_train_size
    nhu_train_size = int(train_ratio * len(nhu_dataset))
    nhu_val_size = len(nhu_dataset) - nhu_train_size

    # 划分数据集
    hu_train_dataset, hu_val_dataset = random_split(hu_dataset, [hu_train_size, hu_val_size])
    nhu_train_dataset, nhu_val_dataset = random_split(nhu_dataset, [nhu_train_size, nhu_val_size])

    # 合并训练集和验证集
    train_dataset = hu_train_dataset + nhu_train_dataset
    val_dataset = hu_val_dataset + nhu_val_dataset

    # 打印数据集大小
    print(f"Train dataset size: {len(train_dataset)}")
    print(f"Validation dataset size: {len(val_dataset)}")

    # 设置batch_size
    batch_size = 64

    # 创建数据加载器
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True, num_workers=4, pin_memory=True)
    val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False, num_workers=4, pin_memory=True)

    # 定义网络
    model = ResNet50(1)
    # 使用 DataParallel 封装
    model = nn.DataParallel(model, device_ids=[0, 1])  # 假设两张卡分别是 GPU 0 和 GPU 1
    model = model.cuda()  # 将模型放到 GPU 上
    # 定义损失函数
    loss = nn.BCEWithLogitsLoss()

    score_model = ResNet50NoPool(1)
    score_model = nn.DataParallel(score_model)
    state_dict = torch.load("/home/zonst/wjh/srmj/model/model_epoch50.pth", map_location=device)
    score_model.load_state_dict(state_dict)
    score_model.to(device)
    score_model.eval()  # 切换到推理模式
    # 设置学习率
    LR = 0.001

    # 定义优化器
    optim = AdamW(model.parameters(), lr=LR, weight_decay=0.01)

    # 训练轮次
    train_round = 30

    # 将loss和神经网络放到指定设备上执行
    loss.to(device)
    model.to(device)
    model_dir = "./model"
    if not os.path.exists(model_dir):
        os.makedirs(model_dir)
    for i in range(train_round):
        loss_sum = 0
        train_correct = 0
        train_total = 0
        model.train()
        print(f"------训练第{i + 1}开始------")
        print('训练数据长度：', len(train_loader.dataset))
        for feature, label in tqdm(train_loader):
            optim.zero_grad()
            inputs = feature.to(device)
            targets = label.to(device).float().unsqueeze(1)  # 调整目标标签的形状
            B = inputs.shape[0]
            with torch.no_grad():
                discard_flag = torch.tensor(1.0).expand(B)
                discard_flag = discard_flag.float().unsqueeze(1)  # => [B,1]
                discard_flag = discard_flag.unsqueeze(-1).unsqueeze(-1)  # => [B,1,1,1]
                discard_flag_4x9 = discard_flag.expand(-1, -1, 4, 9)  # => [B,1,4,9]
                discard_flag_4x9 = discard_flag_4x9.to(device)
                score1 = score_model(torch.cat([inputs[:, :88, :, :], discard_flag_4x9], dim=1))
                discard_flag = torch.tensor(0.0).expand(B)
                discard_flag = discard_flag.float().unsqueeze(1)  # => [B,1]
                discard_flag = discard_flag.unsqueeze(-1).unsqueeze(-1)  # => [B,1,1,1]
                discard_flag_4x9 = discard_flag.expand(-1, -1, 4, 9)  # => [B,1,4,9]
                discard_flag_4x9 = discard_flag_4x9.to(device)
                score2 = score_model(torch.cat([inputs[:, :88, :, :], discard_flag_4x9], dim=1))
                scores = score2 - score1
            # 3. 将分数扩展成 [B, 1, 4, 9] 形状
            #    这样每个样本的分数都能覆盖 4x9 的空间，成为一个新通道
            scores_4x9 = scores.unsqueeze(-1).unsqueeze(-1)  # [B, 1, 1, 1] -> [B, 1, 4, 9]
            scores_4x9 = scores_4x9.expand(-1, -1, 4, 9)  # 复制到 4x9 的区域

            # 4. 将分数通道和原特征在通道维度拼接
            new_features = torch.cat([inputs, scores_4x9], dim=1)  # [B, 90, 4, 9]
            # 进行训练
            outputs = model(new_features)
            # 计算损失，并计算梯度
            train_loss = loss(outputs, targets)
            train_loss.backward()
            optim.step()
            loss_sum += train_loss.item()
            # 统计训练准确率
            predicted = torch.sigmoid(outputs).round()  # 使用 sigmoid 激活函数并四舍五入，得到0或1
            train_total += targets.size(0)
            train_correct += (predicted == targets).sum().item()
        train_accuracy = train_correct / train_total
        print(f"训练损失为:{loss_sum}")
        print(f"训练准确率为: {train_accuracy:.4f}")
        # 开始验证
        # 验证过程中，调整为适合二分类的准确率计算方式
        print(f"----开始第{i + 1}次验证----")
        model.eval()
        sum_data = 0  # 记录测试样本数
        acc = 0  # 记录正确数
        with torch.no_grad():
            print('验证数据长度：', len(val_loader.dataset))
            for feature, label in tqdm(val_loader):
                inputs = feature.to(device)
                targets = label.to(device).float().unsqueeze(1)  # 确保目标标签为 [batch_size, 1]
                B = feature.shape[0]
                discard_flag = torch.tensor(1.0).expand(B)
                discard_flag = discard_flag.float().unsqueeze(1)  # => [B,1]
                discard_flag = discard_flag.unsqueeze(-1).unsqueeze(-1)  # => [B,1,1,1]
                discard_flag_4x9 = discard_flag.expand(-1, -1, 4, 9)  # => [B,1,4,9]
                discard_flag_4x9 = discard_flag_4x9.to(device)
                score1 = score_model(torch.cat([inputs[:, :88, :, :], discard_flag_4x9], dim=1))
                discard_flag = torch.tensor(0).expand(B)
                discard_flag = discard_flag.float().unsqueeze(1)  # => [B,1]
                discard_flag = discard_flag.unsqueeze(-1).unsqueeze(-1)  # => [B,1,1,1]
                discard_flag_4x9 = discard_flag.expand(-1, -1, 4, 9)  # => [B,1,4,9]
                discard_flag_4x9 = discard_flag_4x9.to(device)
                score2 = score_model(torch.cat([inputs[:, :88, :, :], discard_flag_4x9], dim=1))
                scores = score2 - score1
                # 3. 将分数扩展成 [B, 1, 4, 9] 形状
                #    这样每个样本的分数都能覆盖 4x9 的空间，成为一个新通道
                scores_4x9 = scores.unsqueeze(-1).unsqueeze(-1)  # [B, 1, 1, 1] -> [B, 1, 4, 9]
                scores_4x9 = scores_4x9.expand(-1, -1, 4, 9)  # 复制到 4x9 的区域

                # 4. 将分数通道和原特征在通道维度拼接
                new_features = torch.cat([inputs, scores_4x9], dim=1)  # [B, 90, 4, 9]
                # 进行预测
                outputs = model(new_features)
                # 将模型输出的 logits 转换为概率值并四舍五入得到 0 或 1
                predicted = torch.sigmoid(outputs).round()  # 四舍五入得到二进制预测
                sum_data += targets.size(0)  # 累计样本数
                acc += (predicted == targets).sum().item()  # 统计正确预测的样本数
        # 计算并打印准确率
        acc = acc / sum_data
        print(f"验证准确率为:{acc:.4f}")
        torch.save(model, f"./model/model{i}.pth")
    print("")
