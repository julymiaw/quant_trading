<template>
  <div class="indicator-list-container">
    <!-- 页面标题和操作按钮 -->
    <div class="page-header">
      <h1>指标管理</h1>
      <div class="header-actions">
        <el-select
          v-model="indicatorType"
          placeholder="选择指标类型"
          style="width: 150px; margin-right: 10px">
          <el-option label="我的指标" value="my" />
          <el-option label="系统指标" value="system" />
        </el-select>
        <el-button type="primary" @click="showAddIndicatorDialog">
          <el-icon><Plus /></el-icon>
          添加指标
        </el-button>
      </div>
    </div>

    <!-- 搜索和筛选区域 -->
    <div class="search-filter-area">
      <el-input
        v-model="searchKeyword"
        placeholder="搜索指标名称"
        prefix-icon="Search"
        class="search-input"
        clearable />
      <el-select
        v-model="isActive"
        placeholder="状态"
        style="width: 100px; margin-left: 10px">
        <el-option label="全部" value="all" />
        <el-option label="启用" value="true" />
        <el-option label="禁用" value="false" />
      </el-select>
      <el-button
        type="primary"
        @click="refreshIndicators"
        style="margin-left: 10px">
        <el-icon><Refresh /></el-icon>
        刷新
      </el-button>
    </div>

    <!-- 指标列表表格 -->
    <div class="table-container">
      <el-table
        v-loading="loading"
        :data="filteredIndicators"
        style="width: 100%"
        border
        row-key="id"
        height="100%"
        :resizable="false">
        <el-table-column prop="indicator_name" label="指标名称" min-width="180">
          <template #default="scope">
            <el-link
              type="primary"
              :underline="false"
              @click="goToIndicatorDetail(scope.row)">
              {{ scope.row.indicator_name }}
            </el-link>
          </template>
        </el-table-column>
        <el-table-column prop="creator_name" label="创建者" width="120" />
        <el-table-column prop="is_active" label="状态" width="80">
          <template #default="scope">
            <el-tag
              :type="scope.row.is_active ? 'success' : 'danger'"
              size="small">
              {{ scope.row.is_active ? "启用" : "禁用" }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column
          prop="description"
          label="指标说明"
          show-overflow-tooltip
          min-width="200" />
        <el-table-column prop="create_time" label="创建时间" width="160" />
        <el-table-column label="操作" width="300" fixed="right">
          <template #default="scope">
            <!-- 系统指标：只能查看代码和复制 -->
            <template v-if="scope.row.creator_name === 'system'">
              <el-button
                size="small"
                type="info"
                @click="goToIndicatorDetail(scope.row)">
                查看参数
              </el-button>
              <el-button
                size="small"
                type="info"
                @click="viewIndicatorCode(scope.row)">
                查看代码
              </el-button>
              <el-button
                size="small"
                type="success"
                @click="copyIndicator(scope.row)">
                复制
              </el-button>
            </template>
            <!-- 个人指标：可以编辑代码和删除 -->
            <template v-else-if="isCurrentUserCreator(scope.row)">
              <el-button
                size="small"
                type="primary"
                @click="goToIndicatorDetail(scope.row)">
                编辑参数
              </el-button>
              <el-button
                size="small"
                type="primary"
                @click="editIndicator(scope.row)">
                编辑代码
              </el-button>
              <el-button
                size="small"
                type="danger"
                @click="deleteIndicator(scope.row)">
                删除
              </el-button>
            </template>
            <!-- 其他用户指标：只能复制 -->
            <template v-else>
              <el-button
                size="small"
                type="success"
                @click="copyIndicator(scope.row)">
                复制
              </el-button>
            </template>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 分页控件 -->
    <div class="pagination-container">
      <el-pagination
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        :page-sizes="[10, 20, 50, 100]"
        layout="total, sizes, prev, pager, next, jumper"
        :total="total"
        @size-change="handleSizeChange"
        @current-change="handleCurrentChange" />
    </div>

    <!-- 添加/编辑指标弹窗 -->
    <el-dialog
      v-model="indicatorDialogVisible"
      :title="isEditMode ? '编辑指标' : '添加指标'"
      width="800px"
      :before-close="handleIndicatorDialogClose">
      <el-form
        ref="indicatorFormRef"
        :model="indicatorForm"
        :rules="indicatorRules"
        label-width="120px">
        <el-form-item label="指标名称" prop="indicator_name">
          <el-input
            v-model="indicatorForm.indicator_name"
            placeholder="请输入指标名称"
            class="input-wide" />
        </el-form-item>
        <el-form-item label="计算函数" prop="calculation_method">
          <div class="code-editor-wrapper">
            <CodeEditor
              v-model="indicatorForm.calculation_method"
              :default-code="defaultIndicatorFunc"
              placeholder="请输入指标计算函数" />
          </div>
        </el-form-item>
        <el-form-item label="指标说明" prop="description">
          <el-input
            v-model="indicatorForm.description"
            type="textarea"
            placeholder="请输入指标说明"
            class="textarea-wide" />
        </el-form-item>
        <el-form-item label="是否启用" prop="is_active">
          <el-switch v-model="indicatorForm.is_active" />
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="handleIndicatorDialogClose">取消</el-button>
          <el-button type="primary" @click="saveIndicator">确定</el-button>
        </span>
      </template>
    </el-dialog>

    <!-- 查看指标代码弹窗 -->
    <el-dialog
      v-model="viewCodeDialogVisible"
      :title="`${viewingIndicator?.indicator_name || ''} - 查看代码`"
      width="900px"
      :before-close="handleViewCodeDialogClose">
      <div class="view-code-content">
        <div class="code-info">
          <el-descriptions :column="2" border>
            <el-descriptions-item label="指标名称">
              {{ viewingIndicator?.indicator_name }}
            </el-descriptions-item>
            <el-descriptions-item label="创建者">
              {{ viewingIndicator?.creator_name }}
            </el-descriptions-item>
            <el-descriptions-item label="创建时间" :span="2">
              {{ viewingIndicator?.create_time }}
            </el-descriptions-item>
            <el-descriptions-item label="指标说明" :span="2">
              {{ viewingIndicator?.description || "无说明" }}
            </el-descriptions-item>
          </el-descriptions>
        </div>
        <div class="code-section">
          <h3>计算函数代码</h3>
          <div class="code-editor-wrapper readonly">
            <CodeEditor
              :model-value="viewingIndicator?.calculation_method || ''"
              :readonly="true"
              :height="'350'" />
          </div>
        </div>
      </div>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="handleViewCodeDialogClose">关闭</el-button>
          <el-button type="success" @click="copyIndicator(viewingIndicator)">
            复制此指标
          </el-button>
        </span>
      </template>
    </el-dialog>

    <!-- 查看指标参数弹窗（只读模式） -->
    <el-dialog
      v-model="viewParamsDialogVisible"
      :title="`${currentIndicator?.indicator_name || ''} - 查看参数`"
      width="800px"
      :before-close="handleViewParamsDialogClose">
      <div class="view-params-content">
        <div class="params-list">
          <div v-if="currentIndicatorParams.length === 0" class="empty-params">
            <el-empty description="暂无参数" />
          </div>
          <el-table
            v-else
            :data="currentIndicatorParams"
            style="width: 100%"
            border>
            <el-table-column prop="param_name" label="参数名称" width="150" />
            <el-table-column prop="param_type" label="参数类型" width="95">
              <template #default="scope">
                <el-tag
                  :type="
                    scope.row.param_type === 'table' ? 'primary' : 'success'
                  ">
                  {{ scope.row.param_type === "table" ? "数据表" : "指标" }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="data_id" label="数据来源" width="150" />
            <el-table-column prop="pre_period" label="历史天数" width="100" />
            <el-table-column prop="post_period" label="预测天数" width="100" />
            <el-table-column prop="agg_func" label="聚合函数" width="95" />
          </el-table>
        </div>
      </div>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="handleViewParamsDialogClose">关闭</el-button>
        </span>
      </template>
    </el-dialog>

    <!-- 管理指标参数弹窗（编辑模式） -->
    <el-dialog
      v-model="manageParamsDialogVisible"
      :title="`${currentIndicator?.indicator_name || ''} - 参数管理`"
      width="800px"
      :before-close="handleManageParamsDialogClose">
      <div class="indicator-params-content">
        <div class="params-list">
          <h3>已添加参数</h3>
          <div v-if="currentIndicatorParams.length === 0" class="empty-params">
            <el-empty description="暂无参数，请添加参数" />
          </div>
          <el-table
            v-else
            :data="currentIndicatorParams"
            style="width: 100%"
            border>
            <el-table-column prop="param_name" label="参数名称" width="150" />
            <el-table-column prop="param_type" label="参数类型" width="95">
              <template #default="scope">
                <el-tag
                  :type="
                    scope.row.param_type === 'table' ? 'primary' : 'success'
                  ">
                  {{ scope.row.param_type === "table" ? "数据表" : "指标" }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="data_id" label="数据来源" width="150" />
            <el-table-column prop="pre_period" label="历史天数" width="100" />
            <el-table-column prop="post_period" label="预测天数" width="100" />
            <el-table-column prop="agg_func" label="聚合函数" width="95" />
            <el-table-column label="操作" width="80" fixed="right">
              <template #default="scope">
                <el-button
                  type="danger"
                  size="small"
                  @click="removeIndicatorParam(scope.row)">
                  删除
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>

        <div class="add-param-section">
          <h3>添加参数</h3>
          <el-form
            ref="addParamFormRef"
            :model="addParamForm"
            :rules="addParamRules"
            label-width="120px"
            size="small">
            <el-form-item label="添加模式">
              <el-radio-group v-model="addParamMode">
                <el-radio label="existing">使用已有参数</el-radio>
                <el-radio label="new">新增参数</el-radio>
              </el-radio-group>
            </el-form-item>

            <!-- 使用已有参数 -->
            <template v-if="addParamMode === 'existing'">
              <el-form-item label="选择参数" prop="existing_param">
                <SmartAutocomplete
                  v-model="existingParamSelected"
                  node-type="参数"
                  placeholder="请选择已有参数，格式：creator.param_name" />
              </el-form-item>
              <el-button
                type="primary"
                @click="addIndicatorParam"
                style="margin-top: 10px">
                添加参数
              </el-button>
            </template>

            <!-- 新增参数 -->
            <template v-else>
              <el-row :gutter="20">
                <el-col :span="12">
                  <el-form-item label="参数名称" prop="param_name">
                    <el-input
                      v-model="addParamForm.param_name"
                      placeholder="请输入参数名称" />
                  </el-form-item>
                  <el-form-item label="参数类型" prop="param_type">
                    <el-select
                      v-model="addParamForm.param_type"
                      placeholder="请选择参数类型">
                      <el-option label="数据表" value="table" />
                      <el-option label="指标" value="indicator" />
                    </el-select>
                  </el-form-item>
                  <el-form-item label="数据来源" prop="data_id">
                    <SmartAutocomplete
                      v-model="addParamForm.data_id"
                      :node-type="
                        addParamForm.param_type === 'table' ? '数据表' : '指标'
                      "
                      :placeholder="
                        addParamForm.param_type === 'table'
                          ? '示例：daily.close'
                          : '示例：system.MACD'
                      "
                      @select="handleDataSourceSelect" />
                  </el-form-item>
                </el-col>
                <el-col :span="12">
                  <el-form-item label="历史天数" prop="pre_period">
                    <el-input-number
                      v-model="addParamForm.pre_period"
                      :min="0"
                      :max="365" />
                  </el-form-item>
                  <el-form-item label="预测天数" prop="post_period">
                    <el-input-number
                      v-model="addParamForm.post_period"
                      :min="0"
                      :max="365" />
                  </el-form-item>
                  <el-form-item label="聚合函数" prop="agg_func">
                    <el-select
                      v-model="addParamForm.agg_func"
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
                </el-col>
              </el-row>
              <el-button
                type="primary"
                @click="addIndicatorParam"
                style="margin-top: 10px">
                添加参数
              </el-button>
            </template>
          </el-form>
        </div>
      </div>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="handleManageParamsDialogClose">关闭</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script>
import { ref, reactive, computed, onMounted, watch } from "vue";
import { useRouter } from "vue-router";
import { ElMessage, ElMessageBox } from "element-plus";
import { Plus, Search, Refresh } from "@element-plus/icons-vue";
import axios from "axios";
import SmartAutocomplete from "@/components/SmartAutocomplete.vue";
import CodeEditor from "@/components/CodeEditor.vue";

export default {
  name: "IndicatorList",
  components: {
    Plus,
    Search,
    Refresh,
    SmartAutocomplete,
    CodeEditor,
  },
  setup() {
    const router = useRouter();
    const loading = ref(false);
    const indicators = ref([]);
    // Sort helper: newest create_time first
    const sortByCreateTimeDesc = (arr) => {
      if (!arr || !Array.isArray(arr)) return arr;
      arr.sort((a, b) => {
        const ta = a && a.create_time ? new Date(a.create_time).getTime() : 0;
        const tb = b && b.create_time ? new Date(b.create_time).getTime() : 0;
        return tb - ta;
      });
      return arr;
    };
    const searchKeyword = ref("");
    const isActive = ref("all");
    const indicatorType = ref("my");
    const currentPage = ref(1);
    const pageSize = ref(10);
    const total = ref(0);

    // 默认指标代码模板
    const defaultIndicatorFunc = `def calculation_method(params):
    """
    指标计算函数 - 计算自定义技术指标

    参数说明:
    - params: 参数字典，包含各种数据和指标值
      例如: params["daily.close"] - 当日收盘价
            params["system.ema_5"] - 5日EMA指标

    返回值:
    - 计算结果数值
    """
    # 示例：计算收盘价相对5日EMA的偏离度
    if "daily.close" in params and "system.ema_5" in params:
        close_price = params["daily.close"]
        ema_5 = params["system.ema_5"]

        # 计算偏离度（百分比）
        if ema_5 > 0:
            deviation = (close_price - ema_5) / ema_5 * 100
            return deviation

    # 默认返回值
    return 0.0`;

    // 弹窗相关状态
    const indicatorDialogVisible = ref(false);
    const isEditMode = ref(false);
    const editingIndicator = ref(null);
    const indicatorFormRef = ref(null);

    // 查看代码弹窗状态
    const viewCodeDialogVisible = ref(false);
    const viewingIndicator = ref(null);

    // 指标参数相关状态
    const viewParamsDialogVisible = ref(false);
    const manageParamsDialogVisible = ref(false);
    const currentIndicator = ref(null);
    const currentIndicatorParams = ref([]);
    const addParamFormRef = ref(null);

    // 添加参数模式（existing/new）和选择
    const addParamMode = ref("existing");
    const existingParamSelected = ref("");

    // 指标表单数据
    const indicatorForm = reactive({
      indicator_name: "",
      calculation_method: "",
      description: "",
      is_active: true,
    });

    // 添加参数表单数据
    const addParamForm = reactive({
      param_name: "",
      data_id: "",
      param_type: "table",
      pre_period: 0,
      post_period: 0,
      agg_func: null,
    });

    // 表单验证规则
    const indicatorRules = {
      indicator_name: [
        { required: true, message: "请输入指标名称", trigger: "blur" },
        {
          min: 1,
          max: 100,
          message: "指标名称长度在 1 到 100 个字符",
          trigger: "blur",
        },
      ],
      calculation_method: [
        { required: true, message: "请输入计算函数", trigger: "blur" },
        {
          min: 10,
          max: 10000,
          message: "计算函数长度在 10 到 10000 个字符",
          trigger: "blur",
        },
      ],
    };

    const addParamRules = {
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

    // 获取用户信息
    const getUserInfo = () => {
      const storedUserInfo = localStorage.getItem("userInfo");
      return storedUserInfo ? JSON.parse(storedUserInfo) : null;
    };

    // 判断是否是当前用户创建的指标
    const isCurrentUserCreator = (indicator) => {
      const userInfo = getUserInfo();
      return userInfo && indicator.creator_name === userInfo.user_name;
    };

    // 由于筛选和分页都在后端完成，这里直接返回indicators
    const filteredIndicators = computed(() => {
      return indicators.value;
    });

    // 获取指标列表
    const fetchIndicators = async () => {
      try {
        loading.value = true;

        const token = localStorage.getItem("token");
        if (!token) {
          ElMessage.error("请先登录");
          router.push("/login");
          return;
        }

        // 构建查询参数
        const params = {
          page: currentPage.value,
          limit: pageSize.value,
        };

        // 根据指标类型添加筛选条件
        if (indicatorType.value === "my") {
          const userInfo = getUserInfo();
          if (userInfo) {
            params.creator_name = userInfo.user_name;
          }
        } else if (indicatorType.value === "system") {
          params.creator_name = "system";
        }

        // 添加搜索条件
        if (searchKeyword.value.trim()) {
          params.search = searchKeyword.value.trim();
        }

        // 添加状态筛选
        if (isActive.value !== "all") {
          params.is_enabled = isActive.value === "true" ? 1 : 0;
        }

        const response = await axios.get("/api/indicators", {
          params,
          headers: {
            Authorization: `Bearer ${token}`,
          },
        });

        if (response.data) {
          // 后端返回的数据结构: {data: [...], pagination: {...}}
          const indicatorList = response.data.data || response.data;

          // 后端返回的字段已经是正确的格式，不需要转换
          indicators.value = indicatorList;
          sortByCreateTimeDesc(indicators.value);
          total.value = response.data.pagination
            ? response.data.pagination.total
            : indicatorList.length;
        }
      } catch (error) {
        console.error("获取指标列表失败:", error);
        if (error.response) {
          if (error.response.status === 401) {
            ElMessage.error("登录已过期，请重新登录");
            router.push("/login");
          } else {
            ElMessage.error(
              `获取指标列表失败: ${
                error.response.data.message || error.response.statusText
              }`
            );
          }
        } else {
          ElMessage.error("获取指标列表失败，请重试");
        }
      } finally {
        loading.value = false;
      }
    };

    // 刷新指标列表
    const refreshIndicators = () => {
      fetchIndicators();
    };

    // 跳转到指标详情页面
    const goToIndicatorDetail = (indicator) => {
      // 这里可以跳转到指标详情页面，目前暂时不实现
      // router.push({
      //   name: 'IndicatorDetail',
      //   params: {
      //     creatorName: indicator.creator_name,
      //     indicatorName: indicator.indicator_name
      //   }
      // })

      // 打开指标参数管理弹窗
      openIndicatorParamsDialog(indicator);
    };

    // 显示添加指标弹窗
    const showAddIndicatorDialog = () => {
      isEditMode.value = false;
      editingIndicator.value = null;

      // 重置表单
      Object.assign(indicatorForm, {
        indicator_name: "",
        calculation_method: defaultIndicatorFunc, // 使用默认模板
        description: "",
        is_active: true,
      });

      indicatorDialogVisible.value = true;
    };

    // 查看指标代码
    const viewIndicatorCode = (indicator) => {
      viewingIndicator.value = indicator;
      viewCodeDialogVisible.value = true;
    };

    // 编辑指标
    const editIndicator = (indicator) => {
      isEditMode.value = true;
      editingIndicator.value = indicator;

      // 填充表单
      Object.assign(indicatorForm, {
        indicator_name: indicator.indicator_name,
        calculation_method: indicator.calculation_method,
        description: indicator.description || "",
        is_active: indicator.is_active,
      });

      indicatorDialogVisible.value = true;
    };

    // 删除指标
    const deleteIndicator = (indicator) => {
      ElMessageBox.confirm(
        `确定要删除指标"${indicator.indicator_name}"吗？`,
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

            const token = localStorage.getItem("token");
            if (!token) {
              ElMessage.error("请先登录");
              router.push("/login");
              return;
            }

            // 使用后端API删除指标
            const indicatorId = `${indicator.creator_name}.${indicator.indicator_name}`;
            await axios.delete(`/api/indicators/${indicatorId}`, {
              headers: {
                Authorization: `Bearer ${token}`,
              },
            });

            ElMessage.success("指标删除成功");

            // 刷新列表
            await fetchIndicators();
          } catch (error) {
            console.error("删除指标失败:", error);
            if (error.response) {
              ElMessage.error(
                `删除指标失败: ${
                  error.response.data.message || error.response.statusText
                }`
              );
            } else {
              ElMessage.error("删除指标失败，请重试");
            }
          } finally {
            loading.value = false;
          }
        })
        .catch(() => {
          // 用户取消删除
        });
    };

    // 复制指标
    const copyIndicator = async (indicator) => {
      const userInfo = getUserInfo();
      if (!userInfo) {
        ElMessage.error("请先登录");
        return;
      }

      try {
        loading.value = true;

        const token = localStorage.getItem("token");
        if (!token) {
          ElMessage.error("请先登录");
          return;
        }

        const indicatorId = `${indicator.creator_name}.${indicator.indicator_name}`;
        const response = await axios.post(
          `/api/indicators/${indicatorId}/copy`,
          {
            indicator_name: `复制_${indicator.indicator_name}`,
            description: indicator.description || "",
          },
          {
            headers: {
              Authorization: `Bearer ${token}`,
              "Content-Type": "application/json",
            },
          }
        );

        if (response.data) {
          ElMessage.success("指标复制成功，已自动复制相关参数关系");
          // 刷新列表
          await fetchIndicators();
        }
      } catch (error) {
        console.error("复制指标失败:", error);
        if (error.response) {
          ElMessage.error(
            `复制指标失败: ${
              error.response.data.message || error.response.statusText
            }`
          );
        } else {
          ElMessage.error("复制指标失败，请重试");
        }
      } finally {
        loading.value = false;
      }
    };

    // 保存指标
    const saveIndicator = async () => {
      try {
        // 表单验证
        await indicatorFormRef.value.validate();

        loading.value = true;

        const token = localStorage.getItem("token");
        if (!token) {
          ElMessage.error("请先登录");
          router.push("/login");
          return;
        }

        // 准备提交数据，使用后端期望的字段名
        const submitData = {
          indicator_name: indicatorForm.indicator_name,
          calculation_method: indicatorForm.calculation_method,
          description: indicatorForm.description || "",
          is_active: indicatorForm.is_active,
        };

        let response;
        if (isEditMode.value) {
          // 编辑模式：PUT请求
          const indicatorId = `${editingIndicator.value.creator_name}.${editingIndicator.value.indicator_name}`;
          response = await axios.put(
            `/api/indicators/${indicatorId}`,
            submitData,
            {
              headers: {
                Authorization: `Bearer ${token}`,
                "Content-Type": "application/json",
              },
            }
          );
        } else {
          // 新建模式：POST请求
          response = await axios.post("/api/indicators", submitData, {
            headers: {
              Authorization: `Bearer ${token}`,
              "Content-Type": "application/json",
            },
          });
        }

        if (response.data) {
          ElMessage.success(isEditMode.value ? "指标更新成功" : "指标创建成功");

          // 关闭弹窗
          handleIndicatorDialogClose();

          // 刷新列表
          await fetchIndicators();
        }
      } catch (error) {
        console.error("保存指标失败:", error);
        if (error.response) {
          if (error.response.status === 401) {
            ElMessage.error("登录已过期，请重新登录");
            router.push("/login");
          } else {
            ElMessage.error(
              `保存指标失败: ${
                error.response.data.message || error.response.statusText
              }`
            );
          }
        } else {
          ElMessage.error("保存指标失败，请重试");
        }
      } finally {
        loading.value = false;
      }
    };

    // 切换指标状态
    const toggleIndicatorStatus = async (indicator) => {
      try {
        loading.value = true;

        const token = localStorage.getItem("token");
        if (!token) {
          ElMessage.error("请先登录");
          router.push("/login");
          return;
        }

        const indicatorId = `${indicator.creator_name}.${indicator.indicator_name}`;
        await axios.put(
          `/api/indicators/${indicatorId}/toggle-status`,
          {},
          {
            headers: {
              Authorization: `Bearer ${token}`,
            },
          }
        );

        ElMessage.success(`指标${indicator.is_active ? "启用" : "禁用"}成功`);
      } catch (error) {
        console.error("切换指标状态失败:", error);
        // 恢复原状态
        indicator.is_active = !indicator.is_active;
        if (error.response) {
          if (error.response.status === 401) {
            ElMessage.error("登录已过期，请重新登录");
            router.push("/login");
          } else {
            ElMessage.error(
              `切换指标状态失败: ${
                error.response.data.message || error.response.statusText
              }`
            );
          }
        } else {
          ElMessage.error("切换指标状态失败，请重试");
        }
      } finally {
        loading.value = false;
      }
    };

    // 打开指标参数弹窗（根据权限决定是查看还是管理）
    const openIndicatorParamsDialog = (indicator) => {
      currentIndicator.value = indicator;

      // 获取指标参数
      fetchIndicatorParams(indicator);

      // 根据用户权限决定打开哪个弹窗
      if (isCurrentUserCreator(indicator)) {
        // 用户自己的指标：打开管理弹窗
        // 重置添加参数表单
        Object.assign(addParamForm, {
          param_name: "",
          data_id: "",
          param_type: "table",
          pre_period: 0,
          post_period: 0,
          agg_func: null,
        });
        manageParamsDialogVisible.value = true;
      } else {
        // 系统指标或其他用户指标：打开查看弹窗
        viewParamsDialogVisible.value = true;
      }
    };

    // 获取指标参数（从后端拉取关系并映射为表格需要的字段）
    const fetchIndicatorParams = async (indicator) => {
      try {
        const token = localStorage.getItem("token");
        if (!token) {
          currentIndicatorParams.value = [];
          return;
        }

        const response = await axios.get(`/api/indicator-param-relations`, {
          params: {
            indicator_creator: indicator.creator_name,
            indicator_name: indicator.indicator_name,
            limit: 1000,
            page: 1,
          },
          headers: { Authorization: `Bearer ${token}` },
        });

        const relations = response.data?.data || [];

        // 将后端返回的关系行映射为当前表格期望的字段
        const mapped = relations.map((r) => {
          return {
            param_name: r.param_name,
            data_id: r.data_id || r.data_id || r.param_data_type || "",
            param_type: r.param_type || r.param_type || "table",
            pre_period: r.pre_period !== undefined ? r.pre_period : 0,
            post_period: r.post_period !== undefined ? r.post_period : 0,
            agg_func:
              r.agg_func !== undefined ? r.agg_func : r.default_value || null,
            creator_name: r.param_creator_name,
          };
        });

        currentIndicatorParams.value = mapped;
      } catch (error) {
        console.error("获取指标参数失败:", error);
        ElMessage.error("获取指标参数失败，请重试");
        currentIndicatorParams.value = [];
      }
    };

    // 处理数据源选择
    const handleDataSourceSelect = (value) => {
      addParamForm.data_id = value;
    };

    // 添加指标参数（支持 existing/new 两种模式，与 StrategyDetail 行为一致）
    const addIndicatorParam = async () => {
      try {
        loading.value = true;

        const token = localStorage.getItem("token");
        if (!token) {
          ElMessage.error("请先登录");
          loading.value = false;
          return;
        }

        const userInfo = JSON.parse(localStorage.getItem("userInfo") || "null");
        const currentUserName = userInfo?.user_name;

        if (addParamMode.value === "existing") {
          if (!existingParamSelected.value) {
            ElMessage.error("请选择已有参数");
            loading.value = false;
            return;
          }

          const parts = existingParamSelected.value.split(".");
          if (parts.length !== 2) {
            ElMessage.error("请选择格式为 creator.param_name 的参数");
            loading.value = false;
            return;
          }

          const [param_creator_name, param_name] = parts;

          // 关联已有参数到当前指标
          // 使用后端的指标参数关系创建接口
          await axios.post(
            `/api/indicator-param-relations`,
            {
              indicator_creator_name: currentIndicator.value.creator_name,
              indicator_name: currentIndicator.value.indicator_name,
              param_creator_name,
              param_name,
            },
            {
              headers: {
                Authorization: `Bearer ${token}`,
                "Content-Type": "application/json",
              },
            }
          );

          ElMessage.success("参数已添加到当前指标");
          // 刷新参数列表，但不关闭弹窗（与策略页面行为一致）
          await fetchIndicatorParams(currentIndicator.value);
        } else {
          // 新建参数并关联
          await addParamFormRef.value.validate();

          const paramData = {
            param_name: addParamForm.param_name,
            data_id: addParamForm.data_id,
            param_type: addParamForm.param_type,
            pre_period: Number(addParamForm.pre_period) || 0,
            post_period: Number(addParamForm.post_period) || 0,
            agg_func: addParamForm.agg_func || null,
          };

          try {
            await axios.post("/api/params", paramData, {
              headers: {
                Authorization: `Bearer ${token}`,
                "Content-Type": "application/json",
              },
            });
          } catch (err) {
            // 如果参数已存在，后端可能返回400，这里忽略并继续关联
            if (!err.response || err.response.status !== 400) throw err;
          }

          // 关联新创建的参数到指标（使用后端的指标参数关系创建接口）
          await axios.post(
            `/api/indicator-param-relations`,
            {
              indicator_creator_name: currentIndicator.value.creator_name,
              indicator_name: currentIndicator.value.indicator_name,
              param_creator_name: currentUserName,
              param_name: addParamForm.param_name,
            },
            {
              headers: {
                Authorization: `Bearer ${token}`,
                "Content-Type": "application/json",
              },
            }
          );

          ElMessage.success("新参数已创建并添加到当前指标");
          // 保持弹窗打开，重置新增表单并刷新参数列表
          if (addParamFormRef.value) {
            addParamFormRef.value.resetFields();
            addParamForm.param_type = "table";
            addParamForm.agg_func = null;
          }
          await fetchIndicatorParams(currentIndicator.value);
        }
      } catch (error) {
        console.error("添加参数失败:", error);
        ElMessage.error(
          error.response?.data?.message || "添加参数失败，请重试"
        );
      } finally {
        loading.value = false;
      }
    };

    // 从当前指标中移除参数关系（保留参数实体）
    const removeIndicatorParam = (param) => {
      ElMessageBox.confirm(
        `确定要将参数"${param.param_name}"从当前指标中移除吗？此操作不会删除参数实体，只会解除本指标的关联。`,
        "确认移除",
        {
          confirmButtonText: "确定",
          cancelButtonText: "取消",
          type: "warning",
        }
      )
        .then(async () => {
          try {
            loading.value = true;

            const token = localStorage.getItem("token");
            if (!token) {
              ElMessage.error("请先登录");
              loading.value = false;
              return;
            }

            // 构造 relation_id: indicator_creator.indicator_name.param_creator.param_name
            const relationId = `${currentIndicator.value.creator_name}.${
              currentIndicator.value.indicator_name
            }.${param.param_creator_name || param.creator_name}.${
              param.param_name
            }`;

            await axios.delete(`/api/indicator-param-relations/${relationId}`, {
              headers: { Authorization: `Bearer ${token}` },
            });

            // 刷新参数列表
            await fetchIndicatorParams(currentIndicator.value);

            ElMessage.success("参数已从当前指标移除");
          } catch (error) {
            console.error("移除参数失败:", error);
            ElMessage.error(
              error.response?.data?.message || "移除参数失败，请重试"
            );
          } finally {
            loading.value = false;
          }
        })
        .catch(() => {
          // 用户取消移除
        });
    };

    // 处理指标弹窗关闭
    const handleIndicatorDialogClose = () => {
      indicatorDialogVisible.value = false;

      // 重置表单
      if (indicatorFormRef.value) {
        indicatorFormRef.value.resetFields();
      }
    };

    // 处理查看参数弹窗关闭
    const handleViewParamsDialogClose = () => {
      viewParamsDialogVisible.value = false;
    };

    // 处理管理参数弹窗关闭
    const handleManageParamsDialogClose = () => {
      manageParamsDialogVisible.value = false;

      // 重置表单
      if (addParamFormRef.value) {
        addParamFormRef.value.resetFields();
      }
    };

    // 处理查看代码弹窗关闭
    const handleViewCodeDialogClose = () => {
      viewCodeDialogVisible.value = false;
      viewingIndicator.value = null;
    };

    // 分页处理
    const handleSizeChange = (newSize) => {
      pageSize.value = newSize;
      currentPage.value = 1;
      fetchIndicators();
    };

    const handleCurrentChange = (newCurrent) => {
      currentPage.value = newCurrent;
      fetchIndicators();
    };

    // 监听筛选条件变化 (不包括搜索关键字，因为搜索需要防抖)
    watch([indicatorType, isActive, currentPage, pageSize], () => {
      fetchIndicators();
    });

    // 搜索关键字使用防抖
    let searchTimer = null;
    watch(searchKeyword, () => {
      if (searchTimer) {
        clearTimeout(searchTimer);
      }
      searchTimer = setTimeout(() => {
        currentPage.value = 1; // 搜索时重置到第一页
        fetchIndicators();
      }, 500); // 500ms防抖
    });

    // 当参数类型改变时，清空之前选择的数据来源，避免仍使用旧类型的补全结果
    watch(
      () => addParamForm.param_type,
      (newVal, oldVal) => {
        if (newVal !== oldVal) {
          addParamForm.data_id = "";
          addParamForm.agg_func = null;
        }
      }
    );

    onMounted(() => {
      fetchIndicators();
    });

    return {
      loading,
      indicators,
      searchKeyword,
      isActive,
      indicatorType,
      currentPage,
      pageSize,
      total,
      indicatorDialogVisible,
      isEditMode,
      editingIndicator,
      indicatorFormRef,
      indicatorForm,
      indicatorRules,
      viewCodeDialogVisible,
      viewingIndicator,
      viewParamsDialogVisible,
      manageParamsDialogVisible,
      currentIndicator,
      currentIndicatorParams,
      addParamFormRef,
      addParamForm,
      addParamRules,
      filteredIndicators,
      defaultIndicatorFunc,
      fetchIndicators,
      refreshIndicators,
      goToIndicatorDetail,
      showAddIndicatorDialog,
      viewIndicatorCode,
      editIndicator,
      deleteIndicator,
      copyIndicator,
      saveIndicator,
      toggleIndicatorStatus,
      openIndicatorParamsDialog,
      fetchIndicatorParams,
      handleDataSourceSelect,
      addIndicatorParam,
      removeIndicatorParam,
      addParamMode,
      existingParamSelected,
      handleIndicatorDialogClose,
      handleViewCodeDialogClose,
      handleViewParamsDialogClose,
      handleManageParamsDialogClose,
      handleSizeChange,
      handleCurrentChange,
      isCurrentUserCreator,
    };
  },
};
</script>

<style scoped>
.indicator-list-container {
  background-color: white;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.page-header h1 {
  margin: 0;
  color: #333;
  font-size: 20px;
  font-weight: 600;
}

.header-actions {
  display: flex;
  align-items: center;
}

.search-filter-area {
  display: flex;
  align-items: center;
  margin-bottom: 20px;
}

.search-input {
  width: 300px;
}

.table-container {
  flex: 1;
  overflow: hidden;
  margin-bottom: 20px;
}

.pagination-container {
  margin-top: auto;
  display: flex;
  justify-content: flex-end;
  padding-top: 20px;
  border-top: 1px solid #f0f0f0;
}

.indicator-params-content {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.params-list h3,
.add-param-section h3 {
  margin: 0 0 15px 0;
  color: #333;
  font-size: 16px;
  font-weight: 600;
}

.empty-params {
  padding: 40px 0;
  text-align: center;
}

.code-editor-container {
  height: 30vh;
}

.code-editor-wrapper {
  border: 1px solid #e8e8e8;
  border-radius: 4px;
  overflow: hidden;
}

/* Prevent action buttons from wrapping and add spacing */
.el-table .cell .el-button {
  white-space: nowrap;
  margin-right: 8px;
}

/* Wider input/textarea for indicator form */
.input-wide {
  max-width: 560px; /* default wider width */
}

.textarea-wide {
  max-width: 560px;
}

/* 查看代码弹窗样式 */
.view-code-content {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.code-info {
  margin-bottom: 10px;
}

.code-section h3 {
  margin: 0 0 15px 0;
  color: #333;
  font-size: 16px;
  font-weight: 600;
}

.code-editor-wrapper.readonly {
  border: 1px solid #e8e8e8;
  border-radius: 4px;
  overflow: hidden;
  background-color: #f8f8f8;
}

/* 操作按钮间距优化 */
.el-table .cell .el-button + .el-button {
  margin-left: 4px;
}

/* 查看参数弹窗样式 */
.view-params-content {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.view-params-content .params-list {
  margin-bottom: 0;
}
</style>
