import torch
import numpy as np
import pandas as pd
from train_ginn import GINN_LSTM
from collections import deque

model_path = "./ginn_model_weights.pth"


def predict(vars, n_days=5):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = GINN_LSTM().to(device)
    model.load_state_dict(torch.load(model_path))
    model.eval()

    predictions = []
    current_window = deque(vars.flatten().tolist(), maxlen=30)

    for _ in range(n_days):

        input_raw = np.array(current_window).reshape(-1, 1)

        # 转换为Tensor并进行预测
        input_tensor = torch.from_numpy(input_raw).float().unsqueeze(0).to(device)

        with torch.no_grad():
            scaled_prediction = model(input_tensor)

        # d. 反向还原预测结果
        final_prediction_np = scaled_prediction.cpu().numpy()
        predicted_value = final_prediction_np[0, 0]

        # e. 保存本次的预测结果
        predictions.append(predicted_value)

        # f. 更新输入窗口：移除最旧的数据点，并添加新的预测值
        # deque 的 maxlen 属性会自动处理移除旧数据点的操作
        current_window.append(predicted_value)

    return predictions


X_lstm = []
y_true_var = []  # 真实方差 σ_t^2
y_garch_var = []  # GARCH预测的方差 σ_hat_t^2_GARCH
WINDOW_SIZE = 30
data = pd.read_csv("dataset.csv", header=0)
feature_columns = [f"feature_{i}" for i in range(30)]
X_lstm = data[feature_columns]
X_lstm = X_lstm.apply(pd.to_numeric, errors="coerce")
X_lstm = X_lstm.fillna(0)
X_lstm = X_lstm.values.astype(np.float32)


X_lstm = np.array(X_lstm).reshape(-1, WINDOW_SIZE, 1)  # (样本数, 窗口大小, 特征数)

first_sample = X_lstm[0]

predictions = predict(first_sample, 5)
print(first_sample)
print(np.sqrt(predictions))
