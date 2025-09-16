from flask import Flask, jsonify, Response
from flask_cors import CORS
import matplotlib

matplotlib.use("Agg")  # 设置非GUI后端，避免线程问题
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.utils import PlotlyJSONEncoder
import json
import io
import base64

# 新增mpld3导入
import mpld3

# 配置中文字体
plt.rcParams["font.sans-serif"] = ["SimHei", "DejaVu Sans", "Arial"]  # 中文字体
plt.rcParams["axes.unicode_minus"] = False  # 解决负号显示问题

app = Flask(__name__)
CORS(app)  # 允许跨域请求


class PlotlyJSONEncoder(PlotlyJSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return super(PlotlyJSONEncoder, self).default(obj)


@app.route("/api/plot/line", methods=["GET"])
def generate_line_plot():
    """生成交互式折线图"""
    # 生成示例数据
    x = np.linspace(0, 10, 100)
    y1 = np.sin(x)
    y2 = np.cos(x)
    y3 = np.sin(x) * np.cos(x)

    # 创建Plotly图表
    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=x, y=y1, mode="lines", name="sin(x)", line=dict(color="blue", width=2)
        )
    )

    fig.add_trace(
        go.Scatter(
            x=x, y=y2, mode="lines", name="cos(x)", line=dict(color="red", width=2)
        )
    )

    fig.add_trace(
        go.Scatter(
            x=x,
            y=y3,
            mode="lines",
            name="sin(x)*cos(x)",
            line=dict(color="green", width=2),
        )
    )

    fig.update_layout(
        title="交互式数学函数图",
        xaxis_title="X轴",
        yaxis_title="Y轴",
        hovermode="x unified",
        template="plotly_white",
    )

    # 转换为JSON格式
    graphJSON = json.dumps(fig, cls=PlotlyJSONEncoder)

    return jsonify({"status": "success", "plot_data": json.loads(graphJSON)})


@app.route("/api/plot/scatter", methods=["GET"])
def generate_scatter_plot():
    """生成交互式散点图"""
    # 生成示例数据
    np.random.seed(42)
    n = 200
    x = np.random.randn(n)
    y = 2 * x + np.random.randn(n) * 0.5
    colors = np.random.randint(1, 5, n)
    sizes = np.random.randint(5, 20, n)

    fig = go.Figure(
        data=go.Scatter(
            x=x,
            y=y,
            mode="markers",
            marker=dict(
                size=sizes,
                color=colors,
                colorscale="Viridis",
                showscale=True,
                colorbar=dict(title="颜色值"),
            ),
            text=[f"点 {i+1}" for i in range(n)],
            hovertemplate="<b>%{text}</b><br>X: %{x:.2f}<br>Y: %{y:.2f}<extra></extra>",
        )
    )

    fig.update_layout(
        title="交互式散点图",
        xaxis_title="X轴",
        yaxis_title="Y轴",
        template="plotly_white",
    )

    graphJSON = json.dumps(fig, cls=PlotlyJSONEncoder)

    return jsonify({"status": "success", "plot_data": json.loads(graphJSON)})


@app.route("/api/plot/3d", methods=["GET"])
def generate_3d_plot():
    """生成3D交互图表"""
    # 生成3D数据
    n = 50
    x = np.linspace(-5, 5, n)
    y = np.linspace(-5, 5, n)
    X, Y = np.meshgrid(x, y)
    Z = np.sin(np.sqrt(X**2 + Y**2))

    fig = go.Figure(
        data=[
            go.Surface(x=X, y=Y, z=Z, colorscale="Viridis", colorbar=dict(title="Z值"))
        ]
    )

    fig.update_layout(
        title="3D交互式表面图",
        scene=dict(xaxis_title="X轴", yaxis_title="Y轴", zaxis_title="Z轴"),
        template="plotly_white",
    )

    graphJSON = json.dumps(fig, cls=PlotlyJSONEncoder)

    return jsonify({"status": "success", "plot_data": json.loads(graphJSON)})


@app.route("/api/plot/histogram", methods=["GET"])
def generate_histogram():
    """生成交互式直方图"""
    # 生成示例数据
    np.random.seed(42)
    data1 = np.random.normal(0, 1, 1000)
    data2 = np.random.normal(2, 1.5, 1000)

    fig = go.Figure()

    fig.add_trace(go.Histogram(x=data1, name="数据集1", opacity=0.7, nbinsx=30))

    fig.add_trace(go.Histogram(x=data2, name="数据集2", opacity=0.7, nbinsx=30))

    fig.update_layout(
        title="交互式直方图",
        xaxis_title="数值",
        yaxis_title="频次",
        barmode="overlay",
        template="plotly_white",
    )

    graphJSON = json.dumps(fig, cls=PlotlyJSONEncoder)

    return jsonify({"status": "success", "plot_data": json.loads(graphJSON)})


@app.route("/api/plot/matplotlib-to-plotly", methods=["GET"])
def matplotlib_to_plotly():
    """演示如何将matplotlib图表转换为Plotly格式"""
    # 首先用matplotlib创建图表
    plt.figure(figsize=(10, 6))
    x = np.linspace(0, 2 * np.pi, 100)
    y1 = np.sin(x)
    y2 = np.cos(x)

    plt.plot(x, y1, label="sin(x)", linewidth=2)
    plt.plot(x, y2, label="cos(x)", linewidth=2)
    plt.xlabel("X轴")
    plt.ylabel("Y轴")
    plt.title("从Matplotlib转换的图表")
    plt.legend()
    plt.grid(True)

    # 将matplotlib转换为Plotly
    # 这里我们手动重建，实际项目中可以使用mplplotly或plotly.tools.mpl_to_plotly
    fig = go.Figure()

    fig.add_trace(
        go.Scatter(x=x, y=y1, mode="lines", name="sin(x)", line=dict(width=2))
    )

    fig.add_trace(
        go.Scatter(x=x, y=y2, mode="lines", name="cos(x)", line=dict(width=2))
    )

    fig.update_layout(
        title="从Matplotlib转换的交互式图表",
        xaxis_title="X轴",
        yaxis_title="Y轴",
        template="plotly_white",
        showlegend=True,
    )

    # 清理matplotlib图表
    plt.close()

    graphJSON = json.dumps(fig, cls=PlotlyJSONEncoder)

    return jsonify(
        {
            "status": "success",
            "plot_data": json.loads(graphJSON),
            "note": "这个图表原本是用matplotlib创建的，然后转换为Plotly格式以支持前端交互",
        }
    )


# 替代方案：返回matplotlib生成的静态图片（base64编码）
@app.route("/api/plot/matplotlib-png", methods=["GET"])
def matplotlib_png_plot():
    """返回matplotlib生成的PNG图片（base64编码）"""
    fig, ax = plt.subplots(figsize=(8, 5))
    x = np.linspace(0, 10, 100)
    y = np.sin(x) + np.random.normal(0, 0.1, size=100)
    ax.plot(x, y, marker="o", label="sin(x)+noise", markersize=3)
    ax.set_title("Matplotlib Generated Chart")
    ax.set_xlabel("X Axis")
    ax.set_ylabel("Y Axis")
    ax.legend()
    ax.grid(True, alpha=0.3)

    # 将图片保存为base64
    img_buffer = io.BytesIO()
    plt.savefig(img_buffer, format="png", dpi=100, bbox_inches="tight")
    img_buffer.seek(0)
    img_base64 = base64.b64encode(img_buffer.read()).decode("utf-8")
    plt.close(fig)

    return jsonify(
        {"status": "success", "image": f"data:image/png;base64,{img_base64}"}
    )


# Plotly交互式图表接口（推荐）
@app.route("/api/plot/plotly-interactive", methods=["GET"])
def plotly_interactive_plot():
    """返回Plotly交互式图表数据"""
    x = np.linspace(0, 10, 100)
    y = np.sin(x) + np.random.normal(0, 0.1, size=100)

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=x,
            y=y,
            mode="lines+markers",
            name="sin(x)+noise",
            marker=dict(size=4),
            line=dict(width=2),
        )
    )

    fig.update_layout(
        title="Plotly Interactive Chart",
        xaxis_title="X Axis",
        yaxis_title="Y Axis",
        template="plotly_white",
        hovermode="x",
    )

    graphJSON = json.dumps(fig, cls=PlotlyJSONEncoder)
    return jsonify({"status": "success", "plot_data": json.loads(graphJSON)})


if __name__ == "__main__":
    app.run(debug=True, port=5000)
