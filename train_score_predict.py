import os
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, random_split
from tqdm import tqdm

# 新增：导入 TensorBoard 的 SummaryWriter
from torch.utils.tensorboard import SummaryWriter

# 假设 ScoreDataset 已在 dataset.py 中实现，用于加载场面信息及最终得分
from dataset import ScoreDataset
from resnet import ResNet50NoPool

# 设置 cudnn benchmark 提高性能
torch.backends.cudnn.benchmark = True

if __name__ == '__main__':
    # 设置使用设备
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    # 数据目录（两个目录均相同，分别对应 hu 和 nhu 数据）
    hu_dir = '/home/zonst/wjh/srmj/data/all/output/hu'
    nhu_dir = '/home/zonst/wjh/srmj/data/all/output/nhu'

    # 加载数据集
    hu_dataset = ScoreDataset(hu_dir)
    nhu_dataset = ScoreDataset(nhu_dir)
    print("Hu 数据集大小:", len(hu_dataset))
    print("Nhu 数据集大小:", len(nhu_dataset))

    # 设置训练集和验证集的划分比例
    train_ratio = 0.9
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

    print(f"训练集大小: {len(train_dataset)}")
    print(f"验证集大小: {len(val_dataset)}")

    # 设置 DataLoader
    batch_size = 128
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True, num_workers=4, pin_memory=True)
    val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False, num_workers=4, pin_memory=True)

    # 定义回归模型，输出为 1 个神经元（预测分数）
    model = ResNet50NoPool(1)
    # 使用 DataParallel 封装，假设你有两块 GPU
    model = nn.DataParallel(model, device_ids=[0, 1])
    model = model.to(device)

    # 定义均方误差损失函数用于回归
    criterion = nn.MSELoss()

    # 定义优化器
    LR = 0.0005
    optimizer = optim.AdamW(model.parameters(), lr=LR, weight_decay=0.01)

    # 训练轮次
    num_epochs = 500

    # 模型保存目录
    model_dir = "./model"
    if not os.path.exists(model_dir):
        os.makedirs(model_dir)

    # 新增：创建 TensorBoard 的日志记录器，指定日志保存目录
    writer = SummaryWriter(log_dir="logs")

    for epoch in range(num_epochs):
        model.train()
        train_loss_sum = 0.0
        print(f"------ 第 {epoch + 1} 轮训练开始 ------")
        print('训练数据长度：', len(train_loader.dataset))

        # 训练阶段
        for features, score in tqdm(train_loader):
            optimizer.zero_grad()
            inputs = features.to(device)
            # 将目标分数转换为 [batch_size, 1] 的形状
            targets = score.to(device).float().unsqueeze(1)
            outputs = model(inputs)
            loss = criterion(outputs, targets)
            loss.backward()
            optimizer.step()
            train_loss_sum += loss.item()

        # 计算并打印本轮训练的平均损失
        avg_train_loss = train_loss_sum / len(train_loader)
        print(f"训练损失：{avg_train_loss:.4f}")

        # 验证阶段
        model.eval()
        val_loss_sum = 0.0
        with torch.no_grad():
            print(f"---- 第 {epoch + 1} 轮验证开始 ----")
            print('验证数据长度：', len(val_loader.dataset))
            for features, score in tqdm(val_loader):
                inputs = features.to(device)
                targets = score.to(device).float().unsqueeze(1)
                outputs = model(inputs)
                loss = criterion(outputs, targets)
                val_loss_sum += loss.item()

        # 计算并打印本轮验证的平均损失
        avg_val_loss = val_loss_sum / len(val_loader)
        print(f"验证损失：{avg_val_loss:.4f}")

        # 使用 TensorBoard 记录本轮训练和验证损失
        writer.add_scalar("Loss/Train", avg_train_loss, epoch + 1)
        writer.add_scalar("Loss/Val", avg_val_loss, epoch + 1)

        # 保存当前轮次的模型权重
        torch.save(model.state_dict(), os.path.join(model_dir, f"model_epoch{epoch + 1}.pth"))

    print("训练完成！")

    # 训练结束后，关闭 writer
    writer.close()


def load_score_model(checkpoint_path, device="cpu"):
    model = ResNet50NoPool(1)
    state_dict = torch.load(checkpoint_path, map_location=device)
    model.load_state_dict(state_dict)
    model.to(device)
    model.eval()  # 切换到推理模式
    return model
if __name__ == "__main__":
    # 在程序入口处或全局只执行一次
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    score_model = load_score_model("./model/model_epoch30.pth", device=device)
