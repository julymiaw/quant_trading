import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
import pandas as pd
from arch import arch_model
from tqdm import tqdm
import pickle
from torch.utils.data import TensorDataset, DataLoader


# --- [0] 参数设置 ---
# 数据参数
N_SAMPLES = 1200      # 总数据点数
WINDOW_SIZE = 30      # 滚动窗口大小

# GARCH 模型参数 (p, q)
GARCH_P = 1
GARCH_Q = 1

# GINN (LSTM) 模型参数
LSTM_HIDDEN_SIZE = 256
LSTM_NUM_LAYERS = 3
LINEAR_HIDDEN_SIZE = 128

# 训练参数
LAMBDA_LOSS = 0.7     # 损失函数中的 λ
EPOCHS = 50
BATCH_SIZE = 32
LEARNING_RATE = 1e-4

# 设置随机种子以保证结果可复现
np.random.seed(42)
torch.manual_seed(42)


# --- [4] 定义GINN(LSTM)模型和损失函数 ---
class GINN_LSTM(nn.Module):
    def __init__(self):
        super(GINN_LSTM, self).__init__()
        # 对应图3中的 "3 LSTM Layers (256 width)"
        self.lstm = nn.LSTM(
            input_size=1,
            # input_size=30, 
            hidden_size=LSTM_HIDDEN_SIZE, 
            num_layers=LSTM_NUM_LAYERS, 
            batch_first=True
        )
        # 对应图3中的后续层
        self.fc1 = nn.Linear(LSTM_HIDDEN_SIZE, LINEAR_HIDDEN_SIZE)
        self.batch_norm = nn.BatchNorm1d(LINEAR_HIDDEN_SIZE)
        self.relu = nn.ReLU()
        self.fc2 = nn.Linear(LINEAR_HIDDEN_SIZE, 1)

    def forward(self, x):
        # LSTM的输出是 (output, (h_n, c_n))
        # 我们只需要最后一个时间步的输出

        if x.dim() == 2:
            x = x.unsqueeze(1)

        lstm_out, _ = self.lstm(x)
        last_time_step_out = lstm_out[:, -1, :]
        
        # 通过全连接层
        out = self.fc1(last_time_step_out)
        out = self.batch_norm(out)
        out = self.relu(out)
        out = self.fc2(out)
        return out

class GINNLoss(nn.Module):
    """
    自定义损失函数 Loss = λ * MSE(σ_t^2, σ_hat_t^2_GINN) + (1-λ) * MSE(σ_hat_t^2_GARCH, σ_hat_t^2_GINN)
    """
    def __init__(self, lambda_val):
        super(GINNLoss, self).__init__()
        self.lambda_val = lambda_val
        self.mse = nn.MSELoss()

    def forward(self, ginn_pred, true_var, garch_pred):
        loss1 = self.mse(ginn_pred, true_var)
        loss2 = self.mse(ginn_pred, garch_pred)
        return self.lambda_val * loss1 + (1 - self.lambda_val) * loss2

# --- [1] 生成模拟数据 ---
# 在实际应用中，这里应该加载您的真实股票对数收益率数据
# 例如: returns = pd.read_csv('your_stock_returns.csv')['log_return']
# print(">>> [1] Generating simulated log return data...")
# 使用 GARCH(1,1) 过程生成模拟数据，使其具有波动聚集性
# garch_true = arch_model(np.random.randn(N_SAMPLES), p=GARCH_P, q=GARCH_Q)
# garch_true.vol = 'GARCH'
# sim_data = garch_true.simulate([0.01, 0.00005, 0.1, 0.85], N_SAMPLES)
# returns = sim_data.data.values


# --- [2] 第一阶段: AR+GARCH 预计算 ---
# 这是整个工作流中最耗时的部分，因为它需要在每个时间点上滚动拟合GARCH模型
# print(f">>> [2] Performing rolling AR+GARCH predictions for {N_SAMPLES - WINDOW_SIZE} steps...")

if __name__ == '__main__':

    mu_hats = []         # 存储预测的均值
    garch_vars = []      # 存储GARCH预测的方差
    true_vars = []       # 存储真实的方差

    # 迭代处理整个时间序列
    # tqdm 用于显示进度条
    # for t in tqdm(range(WINDOW_SIZE, len(returns))):
    #     # 1. 获取当前窗口的数据
    #     window_data = returns[t - WINDOW_SIZE : t]
        
    #     # 2. 拟合 AR(1)-GARCH(1,1) 模型
    #     # mean='ARX' 加上 lag=1 的外生变量就是AR(1)
    #     # 在这个例子中为简化，我们使用'Constant'均值模型，专注于方差
    #     model = arch_model(window_data, vol='Garch', p=GARCH_P, q=GARCH_Q, mean='Constant', dist='Normal')
    #     # disp='off' 表示不输出拟合信息
    #     res = model.fit(disp='off')
        
    #     # 3. 向前预测一步
    #     forecast = res.forecast(horizon=1)
        
    #     # 4. 提取预测结果
    #     pred_mu = forecast.mean.iloc[-1, 0]
    #     pred_garch_var = forecast.variance.iloc[-1, 0]
        
    #     # 5. 计算"真实"方差 (Ground Truth Variance)
    #     # 使用 t 时刻的真实收益率 和 t 时刻预测的均值
    #     actual_return_t = returns[t]
    #     true_var_t = (actual_return_t - pred_mu)**2
        
    #     # 6. 存储结果
    #     mu_hats.append(pred_mu)
    #     garch_vars.append(pred_garch_var)
    #     true_vars.append(true_var_t)




    # 将列表转换为Numpy数组
    # mu_hats = np.array(mu_hats)
    # garch_vars = np.array(garch_vars)
    # true_vars = np.array(true_vars)

    print(">>> [2] GARCH pre-calculation finished.")


    # --- [3] 第二阶段: 准备LSTM的输入和输出 ---
    # GINN(LSTM)的输入是过去90天的"真实方差" (true_vars)
    # 输出目标是下一天的方差
    print(">>> [3] Preparing data for LSTM training...")

    X_lstm = []
    y_true_var = [] # 真实方差 σ_t^2
    y_garch_var = [] # GARCH预测的方差 σ_hat_t^2_GARCH

    # 从 true_vars 和 garch_vars 中创建滚动窗口数据
    # for i in range(len(true_vars) - WINDOW_SIZE):
        # X_lstm.append(true_vars[i : i + WINDOW_SIZE])
        # y_true_var.append(true_vars[i + WINDOW_SIZE])
        # y_garch_var.append(garch_vars[i + WINDOW_SIZE])

    # X_lstm = np.array(X_lstm).reshape(-1, WINDOW_SIZE, 1) # (样本数, 窗口大小, 特征数)
    # y_true_var = np.array(y_true_var).reshape(-1, 1)
    # y_garch_var = np.array(y_garch_var).reshape(-1, 1)

    data = pd.read_csv('dataset.csv', header=0)
    # print(data[30])
    feature_columns = [f'feature_{i}' for i in range(30)]
    X_lstm = data[feature_columns]
    X_lstm = X_lstm.apply(pd.to_numeric, errors='coerce')
    X_lstm = X_lstm.fillna(0)

    y_true_var = pd.to_numeric(data['true_var'], errors='coerce').fillna(0)
    y_garch_var = pd.to_numeric(data['garch_var'], errors='coerce').fillna(0)

    X_lstm = X_lstm.values.astype(np.float32)

    y_true_var = y_true_var.values.astype(np.float32)
    y_garch_var = y_garch_var.values.astype(np.float32)

    X_lstm = np.array(X_lstm).reshape(-1, WINDOW_SIZE, 1) # (样本数, 窗口大小, 特征数)
    y_true_var = np.array(y_true_var).reshape(-1, 1)
    y_garch_var = np.array(y_garch_var).reshape(-1, 1)
    print(X_lstm)
    # 转换为PyTorch Tensors
    X_tensor = torch.from_numpy(X_lstm).float()
    y_true_tensor = torch.from_numpy(y_true_var).float()
    y_garch_tensor = torch.from_numpy(y_garch_var).float()

    # 创建数据集和数据加载器
    dataset = TensorDataset(X_tensor, y_true_tensor, y_garch_tensor)
    # 划分训练集和测试集 (80% 训练, 20% 测试)
    train_size = int(0.8 * len(dataset))
    test_size = len(dataset) - train_size
    train_dataset, test_dataset = torch.utils.data.random_split(dataset, [train_size, test_size])

    train_loader = DataLoader(train_dataset, batch_size=BATCH_SIZE, shuffle=True)
    test_loader = DataLoader(test_dataset, batch_size=BATCH_SIZE, shuffle=False)

    print(f">>> [3] Data ready. Train size: {len(train_dataset)}, Test size: {len(test_dataset)}")



    # --- [5] 训练和评估模型 ---
    print(">>> [4] Initializing model and starting training...")

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = GINN_LSTM().to(device)
    criterion = GINNLoss(lambda_val=LAMBDA_LOSS)
    # 论文中提到使用AdamW优化器
    optimizer = optim.AdamW(model.parameters(), lr=LEARNING_RATE)

    for epoch in range(EPOCHS):
        model.train()
        total_loss = 0
        for X_batch, y_true_batch, y_garch_batch in train_loader:
            X_batch, y_true_batch, y_garch_batch = \
                X_batch.to(device), y_true_batch.to(device), y_garch_batch.to(device)
            
            # print(X_batch.dim())
            # 前向传播
            outputs = model(X_batch)
            loss = criterion(outputs, y_true_batch, y_garch_batch)
            
            # 反向传播和优化
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            
            total_loss += loss.item()
        
        avg_train_loss = total_loss / len(train_loader)
        
        # 在测试集上评估
        model.eval()
        total_test_loss = 0
        with torch.no_grad():
            for X_batch, y_true_batch, y_garch_batch in test_loader:
                X_batch, y_true_batch, y_garch_batch = \
                    X_batch.to(device), y_true_batch.to(device), y_garch_batch.to(device)
                outputs = model(X_batch)
                loss = criterion(outputs, y_true_batch, y_garch_batch)
                total_test_loss += loss.item()
                
        avg_test_loss = total_test_loss / len(test_loader)
        
        print(f"Epoch [{epoch+1}/{EPOCHS}], Train Loss: {avg_train_loss:.6f}, Test Loss: {avg_test_loss:.6f}")
        print(f"Epoch [{epoch+1}/{EPOCHS}], Train Loss: {avg_train_loss:.6f}")

    print(">>> [5] Training finished.")
    # with open('model.pkl', 'wb') as f:
    #     pickle.dump(model, f)
    model_path = 'ginn_model_weights.pth' 
    torch.save(model.state_dict(), model_path)


    # --- 如何使用模型进行预测 ---
    # 假设你有一段新的过去90天的真实方差数据 `new_true_vars` (shape: 1, 90, 1)
    # model.eval()
    # with torch.no_grad():
    #     new_tensor = torch.from_numpy(new_true_vars).float().to(device)
    #     prediction = model(new_tensor)
    #     print(f"Predicted next day variance: {prediction.item()}")