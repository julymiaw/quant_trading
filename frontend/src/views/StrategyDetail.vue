<template>
  <div class="strategy-detail-container">
    <!-- 页面标题和操作按钮 -->
    <div class="page-header">
      <div class="header-left">
        <el-breadcrumb separator="/">
          <el-breadcrumb-item
            ><el-link @click="goBack">策略管理</el-link></el-breadcrumb-item
          >
          <el-breadcrumb-item>{{ strategy.strategy_name }}</el-breadcrumb-item>
        </el-breadcrumb>
        <h1>{{ strategy.strategy_name }}</h1>
      </div>
      <div class="header-actions" v-if="canEdit">
        <el-button type="primary" @click="showSaveCodeDialog">
          <el-icon><Edit /></el-icon>
          编辑代码
        </el-button>
        <el-button type="success" @click="backtestStrategy">
          <el-icon><DataAnalysis /></el-icon>
          回测
        </el-button>
      </div>
    </div>

    <!-- 主要内容区域 -->
    <div class="strategy-content">
      <!-- 策略基本信息卡片 -->
      <el-card class="strategy-info-card" :loading="loading">
        <template #header>
          <div class="card-header">
            <span>策略基本信息</span>
            <el-button v-if="canEdit" type="text" @click="editBasicInfo">
              <el-icon><Edit /></el-icon>
              编辑
            </el-button>
          </div>
        </template>
        <div class="info-grid">
          <div class="info-item">
            <label>创建者：</label>
            <span>{{ strategy.creator_name }}</span>
          </div>
          <div class="info-item">
            <label>是否公开：</label>
            <el-switch v-model="strategy.public" disabled />
          </div>
          <div class="info-item">
            <label>生效范围：</label>
            <el-tag
              :type="
                strategy.scope_type === 'all'
                  ? 'primary'
                  : strategy.scope_type === 'single_stock'
                  ? 'success'
                  : 'warning'
              ">
              {{ scopeTypeText }}
            </el-tag>
          </div>
          <div class="info-item" v-if="strategy.scope_type !== 'all'">
            <label>股票/指数ID：</label>
            <span>{{ strategy.scope_id }}</span>
          </div>
          <div class="info-item" v-if="strategy.scope_type !== 'single_stock'">
            <label>持仓数量：</label>
            <span>{{ strategy.position_count }}只</span>
          </div>
          <div class="info-item" v-if="strategy.scope_type !== 'single_stock'">
            <label>调仓间隔：</label>
            <span>{{ strategy.rebalance_interval }}天</span>
          </div>
          <div class="info-item">
            <label>买入手续费率：</label>
            <span>{{ (strategy.buy_fee_rate * 100).toFixed(3) }}%</span>
          </div>
          <div class="info-item">
            <label>卖出手续费率：</label>
            <span>{{ (strategy.sell_fee_rate * 100).toFixed(3) }}%</span>
          </div>
        </div>
        <div class="info-item full-width">
          <label>策略描述：</label>
          <div class="strategy-desc">{{ strategy.strategy_desc }}</div>
        </div>
        <div class="info-item">
          <label>创建时间：</label>
          <span>{{ strategy.create_time }}</span>
        </div>
        <div class="info-item">
          <label>更新时间：</label>
          <span>{{ strategy.update_time }}</span>
        </div>
      </el-card>

      <!-- 策略代码展示 -->
      <el-card
        class="strategy-code-card"
        :loading="loading"
        style="margin-top: 20px">
        <template #header>
          <div class="card-header">
            <span>选股函数代码</span>
          </div>
        </template>
        <el-scrollbar height="400px" class="code-scrollbar">
          <pre class="code-block">{{ strategy.select_func }}</pre>
        </el-scrollbar>
      </el-card>

      <!-- 风险控制函数代码 -->
      <el-card
        class="strategy-code-card"
        :loading="loading"
        style="margin-top: 20px"
        v-if="strategy.risk_control_func">
        <template #header>
          <div class="card-header">
            <span>风险控制函数代码</span>
          </div>
        </template>
        <el-scrollbar height="400px" class="code-scrollbar">
          <pre class="code-block">{{ strategy.risk_control_func }}</pre>
        </el-scrollbar>
      </el-card>

      <!-- 参数列表 -->
      <el-card
        class="strategy-params-card"
        :loading="loading"
        style="margin-top: 20px">
        <template #header>
          <div class="card-header">
            <span>参数列表</span>
            <el-button
              v-if="canEdit"
              type="primary"
              @click="showAddParamDialog">
              <el-icon><Plus /></el-icon>
              添加参数
            </el-button>
          </div>
        </template>
        <el-table :data="strategyParams" style="width: 100%" border>
          <el-table-column prop="param_name" label="参数ID" width="150" />
          <el-table-column prop="data_id" label="数据来源ID" width="200" />
          <el-table-column prop="param_type" label="参数类型" width="120">
            <template #default="scope">
              <el-tag
                :type="
                  scope.row.param_type === 'table' ? 'primary' : 'success'
                ">
                {{ scope.row.param_type === "table" ? "数据表" : "指标" }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column
            prop="pre_period"
            label="向前取历史天数"
            width="150" />
          <el-table-column
            prop="post_period"
            label="向后预测天数"
            width="150" />
          <el-table-column prop="agg_func" label="聚合函数" width="120" />
          <el-table-column
            label="操作"
            width="120"
            fixed="right"
            v-if="canEdit">
            <template #default="scope">
              <el-button
                type="danger"
                size="small"
                @click="removeParam(scope.row)">
                删除
              </el-button>
            </template>
          </el-table-column>
        </el-table>
        <div v-if="strategyParams.length === 0" class="empty-params">
          <el-empty description="暂无参数" />
        </div>
      </el-card>

      <!-- 添加参数弹窗 -->
      <el-dialog
        v-model="addParamDialogVisible"
        title="添加参数"
        width="600px"
        :before-close="handleAddParamDialogClose">
        <el-form
          ref="paramFormRef"
          :model="paramForm"
          :rules="paramRules"
          label-width="120px">
          <el-form-item label="参数ID" prop="param_name">
            <el-input
              v-model="paramForm.param_name"
              placeholder="请输入参数ID" />
          </el-form-item>
          <el-form-item label="数据来源ID" prop="data_id">
            <SmartAutocomplete
              v-model="paramForm.data_id"
              node-type="数据表"
              placeholder="请输入数据来源ID，如：daily.open"
              @select="handleDataSourceSelect" />
          </el-form-item>
          <el-form-item label="参数类型" prop="param_type">
            <el-select
              v-model="paramForm.param_type"
              placeholder="请选择参数类型">
              <el-option label="数据表" value="table" />
              <el-option label="指标" value="indicator" />
            </el-select>
          </el-form-item>
          <el-form-item label="向前取历史天数" prop="pre_period">
            <el-input-number
              v-model="paramForm.pre_period"
              :min="0"
              :max="365" />
          </el-form-item>
          <el-form-item label="向后预测天数" prop="post_period">
            <el-input-number
              v-model="paramForm.post_period"
              :min="0"
              :max="365" />
          </el-form-item>
          <el-form-item label="聚合函数" prop="agg_func">
            <el-select
              v-model="paramForm.agg_func"
              placeholder="请选择聚合函数"
              clearable>
              <el-option label="SMA" value="SMA" />
              <el-option label="EMA" value="EMA" />
              <el-option label="MAX" value="MAX" />
              <el-option label="MIN" value="MIN" />
              <el-option label="SUM" value="SUM" />
              <el-option label="AVG" value="AVG" />
            </el-select>
          </el-form-item>
        </el-form>
        <template #footer>
          <span class="dialog-footer">
            <el-button @click="handleAddParamDialogClose">取消</el-button>
            <el-button type="primary" @click="addParam">确定</el-button>
          </span>
        </template>
      </el-dialog>

      <!-- 编辑基本信息弹窗 -->
      <el-dialog
        v-model="editBasicInfoDialogVisible"
        title="编辑基本信息"
        width="600px"
        :before-close="handleEditBasicInfoDialogClose">
        <el-form
          ref="editBasicInfoFormRef"
          :model="editBasicInfoForm"
          :rules="editBasicInfoRules"
          label-width="120px">
          <el-form-item label="策略名称" prop="strategy_name">
            <el-input
              v-model="editBasicInfoForm.strategy_name"
              placeholder="请输入策略名称" />
          </el-form-item>
          <el-form-item label="是否公开" prop="public">
            <el-switch v-model="editBasicInfoForm.public" />
          </el-form-item>
          <el-form-item label="策略描述" prop="strategy_desc">
            <el-input
              v-model="editBasicInfoForm.strategy_desc"
              type="textarea"
              placeholder="请输入策略描述" />
          </el-form-item>
        </el-form>
        <template #footer>
          <span class="dialog-footer">
            <el-button @click="handleEditBasicInfoDialogClose">取消</el-button>
            <el-button type="primary" @click="saveBasicInfo">确定</el-button>
          </span>
        </template>
      </el-dialog>

      <!-- 编辑代码弹窗 -->
      <el-dialog
        v-model="editCodeDialogVisible"
        title="编辑策略代码"
        width="900px"
        :before-close="handleEditCodeDialogClose">
        <div class="code-editor-tabs">
          <el-tabs
            v-model="activeTab"
            type="card"
            @tab-change="handleTabChange">
            <el-tab-pane label="选股函数" name="select_func">
              <div class="code-editor-wrapper">
                <CodeEditor
                  v-model="editCodeForm.select_func"
                  :default-code="defaultSelectFunc"
                  height="400px"
                  placeholder="请输入选股函数代码" />
              </div>
            </el-tab-pane>
            <el-tab-pane label="风险控制函数" name="risk_control_func">
              <div class="code-editor-wrapper">
                <CodeEditor
                  v-model="editCodeForm.risk_control_func"
                  :default-code="defaultRiskControlFunc"
                  height="400px"
                  placeholder="请输入风险控制函数代码" />
              </div>
            </el-tab-pane>
          </el-tabs>
        </div>
        <template #footer>
          <span class="dialog-footer">
            <el-button @click="handleEditCodeDialogClose">取消</el-button>
            <el-button type="primary" @click="saveCode">确定</el-button>
          </span>
        </template>
      </el-dialog>

      <!-- 回测弹窗 -->
      <el-dialog
        v-model="backtestDialogVisible"
        title="策略回测"
        width="800px"
        :before-close="handleBacktestDialogClose">
        <el-form
          ref="backtestFormRef"
          :model="backtestForm"
          :rules="backtestRules"
          label-width="120px">
          <el-form-item label="开始日期" prop="start_date">
            <el-date-picker
              v-model="backtestForm.start_date"
              type="date"
              placeholder="选择开始日期"
              style="width: 100%" />
          </el-form-item>
          <el-form-item label="结束日期" prop="end_date">
            <el-date-picker
              v-model="backtestForm.end_date"
              type="date"
              placeholder="选择结束日期"
              style="width: 100%" />
          </el-form-item>
          <el-form-item label="初始资金(元)" prop="initial_cash">
            <el-input-number
              v-model="backtestForm.initial_cash"
              :min="1000"
              :max="10000000"
              :step="1000" />
          </el-form-item>
          <el-form-item label="佣金费率" prop="commission_rate">
            <el-input-number
              v-model="backtestForm.commission_rate"
              :min="0"
              :max="0.1"
              :step="0.0001" />
          </el-form-item>
          <el-form-item label="滑点率" prop="slippage_rate">
            <el-input-number
              v-model="backtestForm.slippage_rate"
              :min="0"
              :max="0.1"
              :step="0.0001" />
          </el-form-item>
        </el-form>
        <template #footer>
          <span class="dialog-footer">
            <el-button @click="handleBacktestDialogClose">取消</el-button>
            <el-button type="primary" @click="confirmBacktest"
              >开始回测</el-button
            >
          </span>
        </template>
      </el-dialog>
    </div>
  </div>
</template>

<script>
import { ref, reactive, computed, onMounted } from "vue";
import { useRouter, useRoute } from "vue-router";
import { ElMessage, ElMessageBox } from "element-plus";
import { Edit, DataAnalysis, Plus } from "@element-plus/icons-vue";
import axios from "axios";
import SmartAutocomplete from "@/components/SmartAutocomplete.vue";
import CodeEditor from "@/components/CodeEditor.vue";

export default {
  name: "StrategyDetail",
  components: {
    Edit,
    DataAnalysis,
    Plus,
    SmartAutocomplete,
    CodeEditor,
  },
  setup() {
    const router = useRouter();
    const route = useRoute();
    const loading = ref(false);

    // 默认代码模板
    const defaultSelectFunc = `def select_func(candidates, params, position_count, current_holdings, date, context=None):
    """
    选股函数 - 根据策略逻辑选择要持有的股票

    参数说明:
    - candidates: 可选股票列表
    - params: 参数字典，包含各种技术指标和数据
    - position_count: 最大持仓股票数量
    - current_holdings: 当前持仓股票列表
    - date: 当前日期
    - context: 上下文对象，可用于存储状态信息

    返回值:
    - 选中的股票列表（最多position_count只）
    """
    # 示例：选择市值最小的position_count只股票
    if not candidates:
        return []

    # 获取股票市值数据
    market_values = []
    for stock in candidates:
        if f"system.total_mv" in params.get(stock, {}):
            mv = params[stock]["system.total_mv"]
            market_values.append((stock, mv))

    # 按市值从小到大排序，选择最小的position_count只
    market_values.sort(key=lambda x: x[1])
    selected = [stock for stock, _ in market_values[:position_count]]

    return selected`;

    const defaultRiskControlFunc = `def risk_control_func(current_holdings, params, date, context=None):
    """
    风险控制函数 - 对当前持仓进行风险控制

    参数说明:
    - current_holdings: 当前持仓股票列表
    - params: 参数字典，包含各种技术指标和数据
    - date: 当前日期
    - context: 上下文对象，可用于存储状态信息

    返回值:
    - 调整后的持仓股票列表（移除了需要卖出的股票）
    """
    if not current_holdings:
        return []

    sell_list = []

    for stock in current_holdings:
        stock_params = params.get(stock, {})

        # 示例风控逻辑：EMA60线下穿时卖出
        if "system.ema_60" in stock_params and "system.close" in stock_params:
            ema_60 = stock_params["system.ema_60"]
            close_price = stock_params["system.close"]

            if close_price < ema_60:
                sell_list.append(stock)

    # 返回剔除卖出股票后的持仓列表
    return [stock for stock in current_holdings if stock not in sell_list]`;

    // 策略数据
    const strategy = reactive({
      creator_name: "",
      strategy_name: "",
      public: true,
      scope_type: "all",
      scope_id: "",
      position_count: 0,
      rebalance_interval: 0,
      buy_fee_rate: 0.001,
      sell_fee_rate: 0.001,
      strategy_desc: "",
      select_func: "",
      risk_control_func: "",
      create_time: "",
      update_time: "",
    });

    // 策略参数列表
    const strategyParams = ref([]);

    // 获取用户信息
    const getUserInfo = () => {
      const storedUserInfo = localStorage.getItem("userInfo");
      return storedUserInfo ? JSON.parse(storedUserInfo) : null;
    };

    // 判断是否可以编辑策略
    const canEdit = computed(() => {
      const userInfo = getUserInfo();
      return userInfo && strategy.creator_name === userInfo.user_name;
    });

    // 生效范围文本
    const scopeTypeText = computed(() => {
      switch (strategy.scope_type) {
        case "all":
          return "全部";
        case "single_stock":
          return "单只股票";
        case "index":
          return "指数成分股";
        default:
          return "未知";
      }
    });

    // 获取策略详情
    const fetchStrategyDetail = async () => {
      try {
        loading.value = true;
        const { creatorName, strategyName } = route.params;

        // 获取用户token
        const token = localStorage.getItem("token");
        if (!token) {
          ElMessage.error("请先登录");
          router.push("/login");
          return;
        }

        // 调用真实的API获取策略详情
        const response = await axios.get(
          `http://localhost:5000/api/strategies/${creatorName}/${strategyName}`,
          {
            headers: {
              Authorization: `Bearer ${token}`,
            },
          }
        );

        if (response.data.code === 200) {
          Object.assign(strategy, response.data.data);
          // 获取策略参数
          fetchStrategyParams();
        } else {
          throw new Error(response.data.message || "获取策略详情失败");
        }
      } catch (error) {
        console.error("获取策略详情失败:", error);
        if (error.response?.status === 404) {
          ElMessage.error("策略不存在");
          router.push("/strategy-list");
        } else if (error.response?.status === 403) {
          ElMessage.error("无权限访问此策略");
          router.push("/strategy-list");
        } else {
          ElMessage.error(
            error.response?.data?.message || "获取策略详情失败，请重试"
          );
        }
      } finally {
        loading.value = false;
      }
    };

    // 获取策略参数
    const fetchStrategyParams = async () => {
      try {
        // 获取用户token
        const token = localStorage.getItem("token");
        if (!token) {
          return;
        }

        // 调用真实的API获取策略参数
        const response = await axios.get(
          `http://localhost:5000/api/strategies/${strategy.creator_name}/${strategy.strategy_name}/params`,
          {
            headers: {
              Authorization: `Bearer ${token}`,
            },
          }
        );

        if (response.data.code === 200) {
          strategyParams.value = response.data.data || [];
        } else {
          console.error("获取策略参数失败:", response.data.message);
          strategyParams.value = [];
        }
      } catch (error) {
        console.error("获取策略参数失败:", error);
        strategyParams.value = [];
      }
    };

    // 返回上一页
    const goBack = () => {
      router.push("/strategy-list");
    };

    // 编辑基本信息
    const editBasicInfo = () => {
      // 填充编辑表单
      Object.assign(editBasicInfoForm, {
        strategy_name: strategy.strategy_name,
        public: strategy.public,
        strategy_desc: strategy.strategy_desc,
      });

      editBasicInfoDialogVisible.value = true;
    };

    // 保存基本信息
    const saveBasicInfo = async () => {
      try {
        // 表单验证
        await editBasicInfoFormRef.value.validate();

        loading.value = true;

        // 获取用户token
        const token = localStorage.getItem("token");
        if (!token) {
          ElMessage.error("请先登录");
          return;
        }

        // 准备更新数据 - 包含完整的策略信息
        const updateData = {
          strategy_name: editBasicInfoForm.strategy_name,
          public: editBasicInfoForm.public,
          scope_type: strategy.scope_type,
          scope_id: strategy.scope_id,
          select_func: strategy.select_func,
          risk_control_func: strategy.risk_control_func,
          position_count: strategy.position_count,
          rebalance_interval: strategy.rebalance_interval,
          buy_fee_rate: strategy.buy_fee_rate,
          sell_fee_rate: strategy.sell_fee_rate,
          strategy_desc: editBasicInfoForm.strategy_desc,
        };

        // 调用更新API
        const response = await axios.put(
          `http://localhost:5000/api/strategies/${strategy.creator_name}/${strategy.strategy_name}`,
          updateData,
          {
            headers: {
              Authorization: `Bearer ${token}`,
              "Content-Type": "application/json",
            },
          }
        );

        if (response.data.code === 200) {
          // 更新本地策略数据
          Object.assign(strategy, editBasicInfoForm);
          ElMessage.success("基本信息更新成功");
          editBasicInfoDialogVisible.value = false;
        } else {
          throw new Error(response.data.message || "更新基本信息失败");
        }
      } catch (error) {
        console.error("保存基本信息失败:", error);
        ElMessage.error(
          error.response?.data?.message || "保存基本信息失败，请重试"
        );
      } finally {
        loading.value = false;
      }
    };

    // 显示编辑代码弹窗
    const showSaveCodeDialog = () => {
      // 填充编辑表单
      Object.assign(editCodeForm, {
        select_func: strategy.select_func,
        risk_control_func: strategy.risk_control_func,
      });

      editCodeDialogVisible.value = true;
    };

    // 保存代码
    const saveCode = async () => {
      try {
        loading.value = true;

        // 获取用户token
        const token = localStorage.getItem("token");
        if (!token) {
          ElMessage.error("请先登录");
          return;
        }

        // 准备更新数据 - 包含完整的策略信息
        const updateData = {
          strategy_name: strategy.strategy_name,
          public: strategy.public,
          scope_type: strategy.scope_type,
          scope_id: strategy.scope_id,
          select_func: editCodeForm.select_func,
          risk_control_func: editCodeForm.risk_control_func,
          position_count: strategy.position_count,
          rebalance_interval: strategy.rebalance_interval,
          buy_fee_rate: strategy.buy_fee_rate,
          sell_fee_rate: strategy.sell_fee_rate,
          strategy_desc: strategy.strategy_desc,
        };

        // 调用更新API
        const response = await axios.put(
          `http://localhost:5000/api/strategies/${strategy.creator_name}/${strategy.strategy_name}`,
          updateData,
          {
            headers: {
              Authorization: `Bearer ${token}`,
              "Content-Type": "application/json",
            },
          }
        );

        if (response.data.code === 200) {
          // 更新本地策略数据
          Object.assign(strategy, editCodeForm);
          ElMessage.success("策略代码更新成功");
          editCodeDialogVisible.value = false;
        } else {
          throw new Error(response.data.message || "更新策略代码失败");
        }
      } catch (error) {
        console.error("保存策略代码失败:", error);
        ElMessage.error(
          error.response?.data?.message || "保存策略代码失败，请重试"
        );
      } finally {
        loading.value = false;
      }
    };

    // 显示添加参数弹窗
    const showAddParamDialog = () => {
      // 重置表单
      Object.assign(paramForm, {
        param_name: "",
        data_id: "",
        param_type: "table",
        pre_period: 0,
        post_period: 0,
        agg_func: null,
      });

      addParamDialogVisible.value = true;
    };

    // 处理数据源选择
    const handleDataSourceSelect = (value) => {
      paramForm.data_id = value;
      console.log("选择了数据源:", value);
    };

    // 添加参数
    const addParam = async () => {
      try {
        // 表单验证
        await paramFormRef.value.validate();

        loading.value = true;

        // 检查参数ID是否已存在
        const exists = strategyParams.value.some(
          (p) => p.param_name === paramForm.param_name
        );
        if (exists) {
          ElMessage.error("参数ID已存在，请使用其他ID");
          loading.value = false;
          return;
        }

        // 获取用户token
        const token = localStorage.getItem("token");
        if (!token) {
          ElMessage.error("请先登录");
          loading.value = false;
          return;
        }

        // 首先创建参数（如果还不存在）
        const paramData = {
          param_name: paramForm.param_name,
          data_id: paramForm.data_id,
          param_type: paramForm.param_type,
          pre_period: Number(paramForm.pre_period) || 0,
          post_period: Number(paramForm.post_period) || 0,
          agg_func: paramForm.agg_func || null,
        };

        try {
          // 尝试创建参数
          await axios.post("http://localhost:5000/api/params", paramData, {
            headers: {
              Authorization: `Bearer ${token}`,
              "Content-Type": "application/json",
            },
          });
        } catch (paramError) {
          // 如果参数已存在，忽略错误，继续添加策略参数关系
          if (!paramError.response || paramError.response.status !== 400) {
            throw paramError;
          }
        }

        // 获取当前用户信息
        const userInfo = JSON.parse(localStorage.getItem("userInfo"));
        const currentUserName = userInfo?.user_name;

        // 添加策略参数关系
        const relationData = {
          param_creator_name: currentUserName,
          param_name: paramForm.param_name,
        };

        await axios.post(
          `http://localhost:5000/api/strategies/${strategy.creator_name}/${strategy.strategy_name}/params`,
          relationData,
          {
            headers: {
              Authorization: `Bearer ${token}`,
              "Content-Type": "application/json",
            },
          }
        );

        ElMessage.success("参数添加成功");
        addParamDialogVisible.value = false;

        // 重置表单
        if (paramFormRef.value) {
          paramFormRef.value.resetFields();
        }

        // 重新获取策略参数列表
        await fetchStrategyParams();
      } catch (error) {
        console.error("添加参数失败:", error);
        if (
          error.response &&
          error.response.data &&
          error.response.data.message
        ) {
          ElMessage.error(error.response.data.message);
        } else {
          ElMessage.error("添加参数失败，请重试");
        }
      } finally {
        loading.value = false;
      }
    };

    // 删除参数
    const removeParam = (param) => {
      ElMessageBox.confirm(
        `确定要删除参数"${param.param_name}"吗？`,
        "确认删除",
        {
          confirmButtonText: "确定",
          cancelButtonText: "取消",
          type: "warning",
        }
      )
        .then(async () => {
          try {
            loading.value = true;

            // 获取用户token
            const token = localStorage.getItem("token");
            if (!token) {
              ElMessage.error("请先登录");
              loading.value = false;
              return;
            }

            // 调用真实的API删除策略参数关系
            await axios.delete(
              `http://localhost:5000/api/strategies/${strategy.creator_name}/${strategy.strategy_name}/params/${param.creator_name}/${param.param_name}`,
              {
                headers: {
                  Authorization: `Bearer ${token}`,
                },
              }
            );

            ElMessage.success("参数删除成功");

            // 重新获取策略参数列表
            await fetchStrategyParams();
          } catch (error) {
            console.error("删除参数失败:", error);
            if (
              error.response &&
              error.response.data &&
              error.response.data.message
            ) {
              ElMessage.error(error.response.data.message);
            } else {
              ElMessage.error("删除参数失败，请重试");
            }
          } finally {
            loading.value = false;
          }
        })
        .catch(() => {
          // 用户取消删除
        });
    };

    // 回测策略
    const backtestStrategy = () => {
      // 设置默认回测参数
      const today = new Date();
      const threeMonthsAgo = new Date();
      threeMonthsAgo.setMonth(today.getMonth() - 3);

      Object.assign(backtestForm, {
        start_date: threeMonthsAgo,
        end_date: today,
        initial_cash: 100000,
        commission_rate: 0.0003,
        slippage_rate: 0.0001,
      });

      backtestDialogVisible.value = true;
    };

    // 确认回测
    const confirmBacktest = async () => {
      try {
        // 表单验证
        await backtestFormRef.value.validate();

        loading.value = true;

        // 这里使用模拟回测，实际开发中应替换为真实的API调用
        // const response = await axios.post(`/api/strategies/${strategy.creator_name}/${strategy.strategy_name}/backtest`, backtestForm)

        // 模拟回测成功
        ElMessage.success("回测已开始，请在回测结果页面查看");
        backtestDialogVisible.value = false;

        // 跳转到回测结果页面
        // router.push({ name: 'BacktestResult', params: { backtestId: response.data.backtest_id } })
      } catch (error) {
        console.error("回测失败:", error);
        ElMessage.error("回测失败，请重试");
      } finally {
        loading.value = false;
      }
    };

    // 标签切换处理
    const handleTabChange = () => {
      // 可以在这里添加标签切换时的逻辑
    };

    // 弹窗关闭处理
    const handleAddParamDialogClose = () => {
      addParamDialogVisible.value = false;
      if (paramFormRef.value) {
        paramFormRef.value.resetFields();
      }
    };

    const handleEditBasicInfoDialogClose = () => {
      editBasicInfoDialogVisible.value = false;
      if (editBasicInfoFormRef.value) {
        editBasicInfoFormRef.value.resetFields();
      }
    };

    const handleEditCodeDialogClose = () => {
      editCodeDialogVisible.value = false;
    };

    const handleBacktestDialogClose = () => {
      backtestDialogVisible.value = false;
      if (backtestFormRef.value) {
        backtestFormRef.value.resetFields();
      }
    };

    // 弹窗相关状态和表单
    const addParamDialogVisible = ref(false);
    const editBasicInfoDialogVisible = ref(false);
    const editCodeDialogVisible = ref(false);
    const backtestDialogVisible = ref(false);

    // 添加参数表单
    const paramFormRef = ref(null);
    const paramForm = reactive({
      param_name: "",
      data_id: "",
      param_type: "table",
      pre_period: 0,
      post_period: 0,
      agg_func: null,
    });

    const paramRules = {
      param_name: [
        { required: true, message: "请输入参数ID", trigger: "blur" },
        {
          min: 1,
          max: 50,
          message: "参数ID长度在 1 到 50 个字符",
          trigger: "blur",
        },
      ],
      data_id: [
        { required: true, message: "请输入数据来源ID", trigger: "blur" },
      ],
      param_type: [
        { required: true, message: "请选择参数类型", trigger: "change" },
      ],
      pre_period: [
        { required: true, message: "请输入向前取历史天数", trigger: "change" },
        {
          type: "number",
          min: 0,
          message: "向前取历史天数不能小于0",
          trigger: "change",
        },
      ],
      post_period: [
        { required: true, message: "请输入向后预测天数", trigger: "change" },
        {
          type: "number",
          min: 0,
          message: "向后预测天数不能小于0",
          trigger: "change",
        },
      ],
    };

    // 编辑基本信息表单
    const editBasicInfoFormRef = ref(null);
    const editBasicInfoForm = reactive({
      strategy_name: "",
      public: true,
      strategy_desc: "",
    });

    const editBasicInfoRules = {
      strategy_name: [
        { required: true, message: "请输入策略名称", trigger: "blur" },
        {
          min: 1,
          max: 100,
          message: "策略名称长度在 1 到 100 个字符",
          trigger: "blur",
        },
      ],
    };

    // 编辑代码表单
    const activeTab = ref("select_func");
    const editCodeForm = reactive({
      select_func: "",
      risk_control_func: "",
    });

    // 回测表单
    const backtestFormRef = ref(null);
    const backtestForm = reactive({
      start_date: "",
      end_date: "",
      initial_cash: 0,
      commission_rate: 0,
      slippage_rate: 0,
    });

    const backtestRules = {
      start_date: [
        { required: true, message: "请选择开始日期", trigger: "change" },
      ],
      end_date: [
        { required: true, message: "请选择结束日期", trigger: "change" },
        {
          validator: (rule, value, callback) => {
            if (
              value &&
              backtestForm.start_date &&
              new Date(value) < new Date(backtestForm.start_date)
            ) {
              callback(new Error("结束日期不能早于开始日期"));
            } else {
              callback();
            }
          },
          trigger: "change",
        },
      ],
      initial_cash: [
        { required: true, message: "请输入初始资金", trigger: "change" },
        {
          type: "number",
          min: 1000,
          message: "初始资金不能小于1000元",
          trigger: "change",
        },
      ],
      commission_rate: [
        { required: true, message: "请输入佣金费率", trigger: "change" },
        {
          type: "number",
          min: 0,
          max: 0.1,
          message: "佣金费率应在0到0.1之间",
          trigger: "change",
        },
      ],
      slippage_rate: [
        { required: true, message: "请输入滑点率", trigger: "change" },
        {
          type: "number",
          min: 0,
          max: 0.1,
          message: "滑点率应在0到0.1之间",
          trigger: "change",
        },
      ],
    };

    onMounted(() => {
      fetchStrategyDetail();
    });

    return {
      loading,
      strategy,
      strategyParams,
      canEdit,
      scopeTypeText,
      addParamDialogVisible,
      editBasicInfoDialogVisible,
      editCodeDialogVisible,
      backtestDialogVisible,
      paramFormRef,
      paramForm,
      paramRules,
      editBasicInfoFormRef,
      editBasicInfoForm,
      editBasicInfoRules,
      activeTab,
      editCodeForm,
      backtestFormRef,
      backtestForm,
      backtestRules,
      defaultSelectFunc,
      defaultRiskControlFunc,
      fetchStrategyDetail,
      fetchStrategyParams,
      goBack,
      editBasicInfo,
      saveBasicInfo,
      showSaveCodeDialog,
      saveCode,
      showAddParamDialog,
      handleDataSourceSelect,
      addParam,
      removeParam,
      backtestStrategy,
      confirmBacktest,
      handleTabChange,
      handleAddParamDialogClose,
      handleEditBasicInfoDialogClose,
      handleEditCodeDialogClose,
      handleBacktestDialogClose,
    };
  },
};
</script>

<style scoped>
.strategy-detail-container {
  background-color: white;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.strategy-content {
  flex: 1;
  overflow-y: auto;
  padding-right: 5px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 20px;
}

.header-left {
  flex: 1;
}

.header-left h1 {
  margin: 10px 0 0 0;
  color: #333;
  font-size: 24px;
  font-weight: 600;
}

.header-actions {
  display: flex;
  align-items: center;
}

.header-actions .el-button {
  margin-left: 10px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 15px;
  margin-bottom: 15px;
}

.info-item {
  display: flex;
  align-items: center;
}

.info-item.full-width {
  grid-column: 1 / -1;
  align-items: flex-start;
}

.info-item label {
  font-weight: 500;
  margin-right: 10px;
  min-width: 100px;
}

.strategy-desc {
  flex: 1;
  white-space: pre-wrap;
  word-break: break-word;
}

.code-scrollbar {
  border: 1px solid #e8e8e8;
  border-radius: 4px;
}

.code-block {
  margin: 0;
  padding: 15px;
  background-color: #fafafa;
  font-family: "Consolas", "Monaco", "Courier New", monospace;
  font-size: 14px;
  line-height: 1.6;
  color: #333;
  white-space: pre-wrap;
  word-break: break-word;
}

.empty-params {
  padding: 40px 0;
  text-align: center;
}

.code-editor-tabs {
  margin-top: 20px;
}

.code-editor-wrapper {
  border: 1px solid #e8e8e8;
  border-radius: 4px;
  overflow: hidden;
}
</style>
