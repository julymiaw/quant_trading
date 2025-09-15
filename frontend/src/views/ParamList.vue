<template>
  <div class="param-list-container">
    <!-- 页面标题和操作按钮 -->
    <div class="page-header">
      <h1>参数管理</h1>
      <div class="header-actions">
        <el-select
          v-model="paramType"
          placeholder="选择参数类型"
          style="width: 150px; margin-right: 10px">
          <el-option label="我的参数" value="my" />
          <el-option label="系统参数" value="system" />
        </el-select>
        <el-button type="primary" @click="showAddParamDialog">
          <el-icon><Plus /></el-icon>
          添加参数
        </el-button>
      </div>
    </div>

    <!-- 搜索和筛选区域 -->
    <div class="search-filter-area">
      <el-input
        v-model="searchKeyword"
        placeholder="搜索参数ID或数据来源"
        prefix-icon="Search"
        class="search-input"
        clearable />
      <el-select
        v-model="paramSourceType"
        placeholder="参数类型"
        style="width: 120px; margin-left: 10px">
        <el-option label="全部" value="all" />
        <el-option label="数据表" value="table" />
        <el-option label="指标" value="indicator" />
      </el-select>
      <el-button
        type="primary"
        @click="refreshParams"
        style="margin-left: 10px">
        <el-icon><Refresh /></el-icon>
        刷新
      </el-button>
    </div>

    <!-- 参数列表表格 -->
    <div class="table-container">
      <el-table
        v-loading="loading"
        :data="filteredParams"
        style="width: 100%"
        border
        row-key="id"
        height="100%"
        :resizable="false">
        <el-table-column prop="param_name" label="参数名称" width="150" />
        <el-table-column prop="param_type" label="参数类型" width="120">
          <template #default="scope">
            <el-tag
              :type="scope.row.param_type === 'table' ? 'primary' : 'success'">
              {{ scope.row.param_type === "table" ? "数据表" : "指标" }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="data_id" label="数据来源" min-width="200" />
        <el-table-column prop="pre_period" label="历史天数" width="120" />
        <el-table-column prop="post_period" label="预测天数" width="120" />
        <el-table-column prop="agg_func" label="聚合函数" width="120">
          <template #default="scope">
            <el-tag v-if="scope.row.agg_func" type="info">{{
              scope.row.agg_func
            }}</el-tag>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column prop="creator_name" label="创建者" width="120" />
        <el-table-column prop="create_time" label="创建时间" width="160" />
        <el-table-column label="操作" width="240" fixed="right">
          <template #default="scope">
            <el-button
              type="primary"
              size="small"
              @click="editParam(scope.row)"
              v-if="isCurrentUserCreator(scope.row)">
              编辑
            </el-button>
            <el-button
              type="danger"
              size="small"
              @click="deleteParam(scope.row)"
              v-if="isCurrentUserCreator(scope.row)">
              删除
            </el-button>
            <el-button
              type="default"
              size="small"
              @click="copyParam(scope.row)">
              复制
            </el-button>
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

    <!-- 添加/编辑参数弹窗 -->
    <el-dialog
      v-model="paramDialogVisible"
      :title="isEditMode ? '编辑参数' : '添加参数'"
      width="600px"
      :before-close="handleParamDialogClose">
      <el-form
        ref="paramFormRef"
        :model="paramForm"
        :rules="paramRules"
        label-width="120px">
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="参数名称" prop="param_name">
              <el-input
                v-model="paramForm.param_name"
                placeholder="请输入参数名称" />
            </el-form-item>
            <el-form-item label="参数类型" prop="param_type">
              <el-select
                v-model="paramForm.param_type"
                placeholder="请选择参数类型">
                <el-option label="数据表" value="table" />
                <el-option label="指标" value="indicator" />
              </el-select>
            </el-form-item>
            <el-form-item label="数据来源" prop="data_id">
              <SmartAutocomplete
                v-model="paramForm.data_id"
                :node-type="
                  paramForm.param_type === 'table' ? '数据表' : '指标'
                "
                :placeholder="
                  paramForm.param_type === 'table'
                    ? '示例：daily.close'
                    : '示例：system.MACD'
                "
                @select="handleDataSourceSelect" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="历史天数" prop="pre_period">
              <el-input-number
                v-model="paramForm.pre_period"
                :min="0"
                :max="365" />
            </el-form-item>
            <el-form-item label="预测天数" prop="post_period">
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
          </el-col>
        </el-row>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="handleParamDialogClose">取消</el-button>
          <el-button type="primary" @click="saveParam">确定</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script>
import { ref, reactive, computed, onMounted, watch } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { Plus, Search, Refresh } from "@element-plus/icons-vue";
import axios from "axios";
import SmartAutocomplete from "@/components/SmartAutocomplete.vue";

export default {
  name: "ParamList",
  components: {
    Plus,
    Search,
    Refresh,
    SmartAutocomplete,
  },
  setup() {
    const loading = ref(false);
    const params = ref([]);
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
    const paramType = ref("my");
    const paramSourceType = ref("all");
    const currentPage = ref(1);
    const pageSize = ref(10);
    const total = ref(0);

    // 弹窗相关状态
    const paramDialogVisible = ref(false);
    const isEditMode = ref(false);
    const editingParam = ref(null);
    const paramFormRef = ref(null);

    // 参数表单数据
    const paramForm = reactive({
      param_name: "",
      data_id: "",
      param_type: "table",
      pre_period: 0,
      post_period: 0,
      agg_func: null,
    });

    // 表单验证规则
    const paramRules = {
      param_name: [
        { required: true, message: "请输入参数ID", trigger: "blur" },
        {
          min: 1,
          max: 50,
          message: "参数ID长度在 1 到 50 个字符",
          trigger: "blur",
        },
        {
          pattern: /^[a-zA-Z0-9_.]+$/,
          message: "参数ID只能包含字母、数字、下划线和点号",
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

    // 判断是否是当前用户创建的参数
    const isCurrentUserCreator = (param) => {
      const userInfo = getUserInfo();
      return userInfo && param.creator_name === userInfo.user_name;
    };

    // 计算筛选后的参数列表（现在直接返回从API获取的数据）
    const filteredParams = computed(() => {
      return params.value;
    });

    // 监听筛选条件变化，触发新的API请求
    const watchFilters = () => {
      // 重置到第一页
      currentPage.value = 1;
      // 重新获取数据
      fetchParams();
    }; // 获取参数列表
    const fetchParams = async () => {
      try {
        loading.value = true;

        // 获取认证token
        const token = localStorage.getItem("token");
        if (!token) {
          ElMessage.error("请先登录");
          return;
        }

        // 构建查询参数
        const queryParams = new URLSearchParams({
          page: currentPage.value.toString(),
          page_size: pageSize.value.toString(),
          param_type: paramType.value,
          param_source_type: paramSourceType.value,
        });

        if (searchKeyword.value) {
          queryParams.append("search", searchKeyword.value);
        }

        // 调用真实API
        const response = await axios.get(`/api/params?${queryParams}`, {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        });

        if (response.data && response.data.data) {
          params.value = response.data.data.params || [];
          sortByCreateTimeDesc(params.value);
          total.value = response.data.data.total || 0;
        } else {
          params.value = [];
          total.value = 0;
        }
      } catch (error) {
        console.error("获取参数列表失败:", error);
        ElMessage.error("获取参数列表失败，请重试");
      } finally {
        loading.value = false;
      }
    };

    // 刷新参数列表
    const refreshParams = () => {
      fetchParams();
    };

    // 显示添加参数弹窗
    const showAddParamDialog = () => {
      isEditMode.value = false;
      editingParam.value = null;

      // 重置表单
      Object.assign(paramForm, {
        param_name: "",
        data_id: "",
        param_type: "table",
        pre_period: 0,
        post_period: 0,
        agg_func: null,
      });

      paramDialogVisible.value = true;
    };

    // 编辑参数
    const editParam = (param) => {
      isEditMode.value = true;
      editingParam.value = param;

      // 填充表单
      Object.assign(paramForm, {
        param_name: param.param_name,
        data_id: param.data_id,
        param_type: param.param_type,
        pre_period: param.pre_period || 0,
        post_period: param.post_period || 0,
        agg_func: param.agg_func || null,
      });

      paramDialogVisible.value = true;
    };

    // 删除参数
    const deleteParam = (param) => {
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

            // 获取认证token
            const token = localStorage.getItem("token");
            if (!token) {
              ElMessage.error("请先登录");
              loading.value = false;
              return;
            }

            // 调用真实API删除参数
            await axios.delete(`/api/params/${param.id}`, {
              headers: {
                Authorization: `Bearer ${token}`,
              },
            });

            ElMessage.success("参数删除成功");

            // 重新获取参数列表
            await fetchParams();
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

    // 复制参数
    const copyParam = (param) => {
      const userInfo = getUserInfo();
      if (!userInfo) {
        ElMessage.error("请先登录");
        return;
      }

      // 重置表单
      Object.assign(paramForm, {
        param_name: `copy_${param.param_name}`,
        data_id: param.data_id,
        param_type: param.param_type,
        pre_period: param.pre_period || 0,
        post_period: param.post_period || 0,
        agg_func: param.agg_func || null,
      });

      isEditMode.value = false;
      editingParam.value = null;
      paramDialogVisible.value = true;

      ElMessage.info("已复制参数，您可以修改后保存");
    };

    // 保存参数
    const saveParam = async () => {
      try {
        // 表单验证
        await paramFormRef.value.validate();

        loading.value = true;

        // 获取认证token
        const token = localStorage.getItem("token");
        if (!token) {
          ElMessage.error("请先登录");
          loading.value = false;
          return;
        }

        // 准备要发送的数据，确保格式正确
        const submitData = {
          param_name: paramForm.param_name || "",
          data_id: paramForm.data_id || "",
          param_type: paramForm.param_type || "table",
          pre_period: Number(paramForm.pre_period) || 0,
          post_period: Number(paramForm.post_period) || 0,
          agg_func: paramForm.agg_func || null,
        };

        // 调用真实API
        if (isEditMode.value) {
          // 更新参数
          await axios.put(`/api/params/${editingParam.value.id}`, submitData, {
            headers: {
              Authorization: `Bearer ${token}`,
              "Content-Type": "application/json",
            },
          });
          ElMessage.success("参数更新成功");
        } else {
          // 创建新参数
          await axios.post("/api/params", submitData, {
            headers: {
              Authorization: `Bearer ${token}`,
              "Content-Type": "application/json",
            },
          });
          ElMessage.success("参数添加成功");
        }

        paramDialogVisible.value = false;

        // 重新获取参数列表，确保按创建时间排序，新添加/复制的参数会出现在正确位置
        await fetchParams();
      } catch (error) {
        console.error("保存参数失败:", error);
        if (
          error.response &&
          error.response.data &&
          error.response.data.message
        ) {
          ElMessage.error(error.response.data.message);
        } else {
          ElMessage.error("保存参数失败，请重试");
        }
      } finally {
        loading.value = false;
      }
    };

    // 处理数据源选择
    const handleDataSourceSelect = (value) => {
      paramForm.data_id = value;
      console.log("选择了数据源:", value);
    };

    // 处理参数弹窗关闭
    const handleParamDialogClose = () => {
      paramDialogVisible.value = false;

      // 重置表单
      if (paramFormRef.value) {
        paramFormRef.value.resetFields();
      }
    };

    // 分页处理
    const handleSizeChange = (newSize) => {
      pageSize.value = newSize;
      currentPage.value = 1;
      fetchParams();
    };

    const handleCurrentChange = (newCurrent) => {
      currentPage.value = newCurrent;
      fetchParams();
    };

    onMounted(() => {
      fetchParams();
    });

    // 监听筛选条件变化
    watch(
      [paramType, paramSourceType, searchKeyword],
      () => {
        watchFilters();
      },
      { deep: true }
    );

    // 当参数类型改变时，清空之前选择的数据来源，避免仍使用旧类型的补全结果
    watch(
      () => paramForm.param_type,
      (newVal, oldVal) => {
        if (newVal !== oldVal) {
          paramForm.data_id = "";
          paramForm.agg_func = null;
        }
      }
    );

    return {
      loading,
      params,
      searchKeyword,
      paramType,
      paramSourceType,
      currentPage,
      pageSize,
      total,
      paramDialogVisible,
      isEditMode,
      editingParam,
      paramFormRef,
      paramForm,
      paramRules,
      filteredParams,
      fetchParams,
      refreshParams,
      showAddParamDialog,
      editParam,
      deleteParam,
      copyParam,
      saveParam,
      handleDataSourceSelect,
      handleParamDialogClose,
      handleSizeChange,
      handleCurrentChange,
      isCurrentUserCreator,
      watchFilters,
    };
  },
};
</script>

<style scoped>
.param-list-container {
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

/* Prevent action buttons from wrapping and add spacing */
.el-table .cell .el-button {
  white-space: nowrap;
  margin-right: 8px;
}
</style>
