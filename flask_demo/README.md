# Flask + Vue.js 数据可视化Demo

## 项目简介

这是一个探索**前端交互式图表渲染后端matplotlib对象**的Demo项目。通过Flask后端和Vue.js前端的结合，展示了两种主要的数据可视化方案：
- **静态图片方案**：后端matplotlib生成PNG，前端直接展示
- **交互式图表方案**：后端生成Plotly数据，前端用Plotly.js渲染交互图表

## 项目结构

```
flask_demo/
├── backend/              # Flask后端
│   ├── app.py           # 主应用文件
│   └── requirements.txt # Python依赖
├── frontend/            # Vue.js前端
│   ├── src/
│   │   ├── App.vue     # 主页面组件
│   │   └── main.js     # 入口文件
│   ├── index.html      # HTML模板
│   └── package.json    # Node.js依赖
└── README.md           # 本文档
```

## 技术栈

### 后端 (Flask)
- **Flask**: Python Web框架
- **Flask-CORS**: 解决跨域问题
- **matplotlib**: 数据可视化库（生成静态图）
- **Plotly**: 交互式图表库
- **NumPy**: 数学计算库

### 前端 (Vue.js)
- **Vue 3**: 渐进式JavaScript框架
- **Vite**: 现代前端构建工具
- **Plotly.js**: 前端交互式图表库

## 核心功能

### 1. 静态图片展示 (`/api/plot/matplotlib-png`)
- 后端用matplotlib生成图表
- 转换为base64编码的PNG图片
- 前端用`<img>`标签直接展示

### 2. 交互式图表 (`/api/plot/plotly-interactive`)
- 后端生成Plotly图表数据
- 返回JSON格式的图表配置
- 前端用Plotly.js渲染，支持缩放、悬停等交互

## 快速开始

### 后端启动

1. 进入后端目录：
```bash
cd backend
```

2. 安装Python依赖：
```bash
pip install -r requirements.txt
```

3. 启动Flask服务：
```bash
python app.py
```
> 默认运行在 http://localhost:5000

### 前端启动

1. 进入前端目录：
```bash
cd frontend
```

2. 安装Node.js依赖：
```bash
npm install
```

3. 启动开发服务器：
```bash
npm run dev
```
> 默认运行在 http://localhost:5173

### 访问应用

打开浏览器访问 `http://localhost:5173`，点击按钮体验两种图表展示方式。

## 关键经验总结

### 1. matplotlib在Web服务中的配置

```python
import matplotlib
matplotlib.use('Agg')  # 设置非GUI后端，避免线程问题
```

**经验**：在Flask等Web框架中使用matplotlib时，必须设置为非GUI后端，否则会出现线程警告。

### 2. 中文字体处理

```python
plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans', 'Arial']
plt.rcParams['axes.unicode_minus'] = False
```

**经验**：matplotlib默认不支持中文显示，需要配置中文字体。为了避免字体缺失问题，建议使用英文标签或确保服务器安装了相应字体。

### 3. 跨域问题解决

```python
from flask_cors import CORS
CORS(app)  # 允许跨域请求
```

**经验**：前后端分离开发时，必须处理CORS跨域问题，否则前端无法访问后端API。

### 4. 图片数据传输方案

#### 方案A：base64编码
```python
img_base64 = base64.b64encode(img_buffer.read()).decode('utf-8')
return jsonify({"image": f"data:image/png;base64,{img_base64}"})
```

#### 方案B：直接返回图片流
```python
return Response(img_buffer.getvalue(), mimetype='image/png')
```

**经验**：base64方案适合小图片且需要在JSON中传输；直接返回图片流更高效，但需要用`<img src="api_url">`方式展示。

### 5. 前端异步数据处理

```javascript
async function fetchData() {
  try {
    const res = await fetch('http://localhost:5000/api/...')
    const data = await res.json()
    // 处理数据
  } catch (e) {
    // 错误处理
  }
}
```

**经验**：使用async/await处理异步请求，并做好错误处理和加载状态管理。

### 6. Plotly.js集成

```html
<!-- 引入最新版本 -->
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
```

```javascript
// 渲染图表
Plotly.newPlot('chart-div', data, layout)
```

**经验**：避免使用`plotly-latest.min.js`，应指定具体版本号以确保稳定性。

## 两种方案对比

| 特性         | 静态图片方案       | 交互式图表方案             |
| ------------ | ------------------ | -------------------------- |
| **实现难度** | 简单               | 中等                       |
| **交互性**   | 无                 | 丰富（缩放、悬停、选择等） |
| **性能**     | 高（图片直接展示） | 中等（需要JS渲染）         |
| **文件大小** | 较大（PNG图片）    | 较小（JSON数据）           |
| **定制性**   | 低                 | 高                         |
| **适用场景** | 静态报表、简单展示 | 数据探索、交互分析         |

## 扩展建议

### 1. 添加更多图表类型
- 散点图、柱状图、热力图等
- 3D图表、动态图表

### 2. 数据源集成
- 连接数据库
- 读取CSV/Excel文件
- 实时数据流

### 3. 用户交互功能
- 参数调整界面
- 图表配置选项
- 数据筛选器

### 4. 性能优化
- 图片缓存机制
- 数据压缩
- 异步加载

## 部署注意事项

1. **生产环境配置**：
   ```python
   app.run(host='0.0.0.0', port=5000, debug=False)
   ```

2. **静态文件服务**：考虑用Nginx等服务器处理静态文件

3. **安全性**：添加API认证、输入验证等安全机制

## 总结

这个Demo成功展示了如何将后端matplotlib对象转换为前端可交互的图表。通过对比静态图片和交互式图表两种方案，我们学会了：

- Web环境下matplotlib的正确配置方法
- 前后端数据传输的多种方案
- 交互式图表库的集成和使用
- 跨域、字体、异步等常见问题的解决方案

这些经验可以应用到量化交易、数据分析等更复杂的项目中，为构建专业的数据可视化应用奠定基础。