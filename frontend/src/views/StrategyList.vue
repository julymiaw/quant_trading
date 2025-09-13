<template>
  <div class="strategy-lis    <!-- 策略列表表格 -->
    <div class="table-container">
      <el-table
        v-loading="loading"
        :data="strategies"
        style="width: 100%"
        border
        row-key="id"
        height="100%">iner">
    <!-- 页面标题和操作按钮 -->
    <div class="page-header">
      <h1>策略管理</h1>
      <div class="header-actions">
        <el-select v-model="strategyType" placeholder="选择策略类型" style="width: 150px; margin-right: 10px;">
          <el-option label="我的策略" value="my" />
          <el-option label="系统策略" value="system" />
          <el-option label="公开策略" value="public" />
        </el-select>
        <el-button type="primary" @click="showAddStrategyDialog">
          <el-icon><Plus /></el-icon>
          添加策略
        </el-button>
      </div>
    </div>
    
    <!-- 搜索和筛选区域 -->
    <div class="search-filter-area">
      <el-input
        v-model="searchKeyword"
        placeholder="搜索策略名称"
        prefix-icon="Search"
        class="search-input"
        clearable
      />
      <el-select v-model="scopeType" placeholder="策略生效范围" style="width: 150px; margin-left: 10px;">
        <el-option label="全部" value="all" />
        <el-option label="单只股票" value="single_stock" />
        <el-option label="指数成分股" value="index" />
      </el-select>
      <el-button type="primary" @click="refreshStrategies" style="margin-left: 10px;">
        <el-icon><Refresh /></el-icon>
        刷新
      </el-button>
    </div>
    
    <!-- 策略列表表格 -->
    <el-table
      v-loading="loading"
      :data="filteredStrategies"
      style="width: 100%"
      border
      row-key="id"
    >
      <el-table-column prop="strategy_name" label="策略名称" min-width="180">
        <template #default="scope">
          <el-link type="primary" :underline="false" @click="goToStrategyDetail(scope.row)">
            {{ scope.row.strategy_name }}
          </el-link>
        </template>
      </el-table-column>
      <el-table-column prop="creator_name" label="创建者" width="120" />
      <el-table-column prop="public" label="是否公开" width="100">
        <template #default="scope">
          <el-switch v-model="scope.row.public" disabled />
        </template>
      </el-table-column>
      <el-table-column prop="scope_type" label="生效范围" width="120">
        <template #default="scope">
          <el-tag
            :type="
              scope.row.scope_type === 'all' ? 'primary'
                : scope.row.scope_type === 'single_stock' ? 'success'
                : 'warning'
            "
          >
            {{ scope.row.scope_type === 'all' ? '全部'
              : scope.row.scope_type === 'single_stock' ? '单只股票'
              : '指数成分股' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="scope_id" label="股票/指数ID" width="120" v-if="showScopeId" />
      <el-table-column prop="position_count" label="持仓数量" width="100" />
      <el-table-column prop="rebalance_interval" label="调仓间隔" width="100">
        <template #default="scope">
          {{ scope.row.rebalance_interval || 0 }}天
        </template>
      </el-table-column>
      <el-table-column prop="strategy_desc" label="策略描述" show-overflow-tooltip min-width="200" />
      <el-table-column prop="create_time" label="创建时间" width="160" />
      <el-table-column prop="update_time" label="更新时间" width="160" />
      <el-table-column label="操作" width="180" fixed="right">
        <template #default="scope">
          <el-button
            type="primary"
            size="small"
            @click="editStrategy(scope.row)"
            v-if="isCurrentUserCreator(scope.row)"
          >
            编辑
          </el-button>
          <el-button
            type="danger"
            size="small"
            @click="deleteStrategy(scope.row)"
            v-if="isCurrentUserCreator(scope.row)"
          >
            删除
          </el-button>
          <el-button
            type="default"
            size="small"
            @click="copyStrategy(scope.row)"
          >
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
        @current-change="handleCurrentChange"
      />
    </div>
    
    <!-- 添加/编辑策略弹窗 -->
    <el-dialog
      v-model="strategyDialogVisible"
      :title="isEditMode ? '编辑策略' : '添加策略'"
      width="600px"
      :before-close="handleStrategyDialogClose"
    >
      <el-form
        ref="strategyFormRef"
        :model="strategyForm"
        :rules="strategyRules"
        label-width="120px"
      >
        <el-form-item label="策略名称" prop="strategy_name">
          <el-input v-model="strategyForm.strategy_name" placeholder="请输入策略名称" />
        </el-form-item>
        <el-form-item label="是否公开" prop="public">
          <el-switch v-model="strategyForm.public" />
        </el-form-item>
        <el-form-item label="生效范围" prop="scope_type">
          <el-select v-model="strategyForm.scope_type" placeholder="请选择生效范围">
            <el-option label="全部" value="all" />
            <el-option label="单只股票" value="single_stock" />
            <el-option label="指数成分股" value="index" />
          </el-select>
        </el-form-item>
        <el-form-item 
          v-if="strategyForm.scope_type !== 'all'" 
          label="股票/指数ID" 
          prop="scope_id"
        >
          <el-input v-model="strategyForm.scope_id" placeholder="请输入股票代码或指数代码" />
        </el-form-item>
        <el-form-item 
          v-if="strategyForm.scope_type !== 'single_stock'" 
          label="持仓数量" 
          prop="position_count"
        >
          <el-input-number v-model="strategyForm.position_count" :min="1" :max="100" />
        </el-form-item>
        <el-form-item 
          v-if="strategyForm.scope_type !== 'single_stock'" 
          label="调仓间隔(天)" 
          prop="rebalance_interval"
        >
          <el-input-number v-model="strategyForm.rebalance_interval" :min="1" :max="365" />
        </el-form-item>
        <el-form-item label="买入手续费率" prop="buy_fee_rate">
          <el-input-number v-model="strategyForm.buy_fee_rate" :min="0" :max="0.1" :step="0.0001" />
        </el-form-item>
        <el-form-item label="卖出手续费率" prop="sell_fee_rate">
          <el-input-number v-model="strategyForm.sell_fee_rate" :min="0" :max="0.1" :step="0.0001" />
        </el-form-item>
        <el-form-item label="策略描述" prop="strategy_desc">
          <el-input v-model="strategyForm.strategy_desc" type="textarea" placeholder="请输入策略描述" />
        </el-form-item>
        <el-form-item label="选股函数" prop="select_func">
          <el-input 
            v-model="strategyForm.select_func" 
            type="textarea" 
            :rows="8"
            placeholder="请输入选股函数代码（Python）" 
          />
        </el-form-item>
        <el-form-item label="风控函数" prop="risk_control_func">
          <el-input 
            v-model="strategyForm.risk_control_func" 
            type="textarea" 
            :rows="6"
            placeholder="请输入风险控制函数代码（可选）" 
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="handleStrategyDialogClose">取消</el-button>
          <el-button type="primary" @click="saveStrategy">确定</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script>
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Search, Refresh } from '@element-plus/icons-vue'
import axios from 'axios'

export default {
  name: 'StrategyList',
  components: {
    Plus,
    Search,
    Refresh
  },
  setup() {
    const router = useRouter()
    const loading = ref(false)
    const strategies = ref([])
    const searchKeyword = ref('')
    const scopeType = ref('all')
    const strategyType = ref('my')
    const currentPage = ref(1)
    const pageSize = ref(10)
    const total = ref(0)
    
    // 弹窗相关状态
    const strategyDialogVisible = ref(false)
    const isEditMode = ref(false)
    const editingStrategy = ref(null)
    const strategyFormRef = ref(null)
    
    // 策略表单数据
    const strategyForm = reactive({
      strategy_name: '',
      public: true,
      scope_type: 'all',
      scope_id: '',
      position_count: 5,
      rebalance_interval: 5,
      buy_fee_rate: 0.001,
      sell_fee_rate: 0.001,
      strategy_desc: '',
      select_func: '',
      risk_control_func: ''
    })
    
    // 表单验证规则
    const strategyRules = {
      strategy_name: [
        { required: true, message: '请输入策略名称', trigger: 'blur' },
        { min: 1, max: 100, message: '策略名称长度在 1 到 100 个字符', trigger: 'blur' }
      ],
      scope_type: [
        { required: true, message: '请选择生效范围', trigger: 'change' }
      ],
      select_func: [
        { required: true, message: '请输入选股函数代码', trigger: 'blur' }
      ],
      scope_id: [
        {
          required: true,
          message: '请输入股票代码或指数代码',
          trigger: 'blur',
          validator: (rule, value, callback) => {
            if (strategyForm.scope_type !== 'all' && !value) {
              callback(new Error('请输入股票代码或指数代码'))
            } else {
              callback()
            }
          }
        }
      ],
      position_count: [
        {
          required: true,
          message: '请输入持仓数量',
          trigger: 'change',
          validator: (rule, value, callback) => {
            if (strategyForm.scope_type !== 'single_stock' && !value) {
              callback(new Error('请输入持仓数量'))
            } else {
              callback()
            }
          }
        }
      ],
      rebalance_interval: [
        {
          required: true,
          message: '请输入调仓间隔',
          trigger: 'change',
          validator: (rule, value, callback) => {
            if (strategyForm.scope_type !== 'single_stock' && !value) {
              callback(new Error('请输入调仓间隔'))
            } else {
              callback()
            }
          }
        }
      ]
    }
    
    // 获取用户信息
    const getUserInfo = () => {
      const storedUserInfo = localStorage.getItem('userInfo')
      return storedUserInfo ? JSON.parse(storedUserInfo) : null
    }
    
    // 判断是否是当前用户创建的策略
    const isCurrentUserCreator = (strategy) => {
      const userInfo = getUserInfo()
      return userInfo && strategy.creator_name === userInfo.user_name
    }
    
    // 计算筛选后的策略列表（后端已处理分页和筛选，前端直接显示）
    const filteredStrategies = computed(() => {
      return strategies.value
    })
    
    // 是否显示scope_id列
    const showScopeId = computed(() => {
      return scopeType.value !== 'all' || strategies.value.some(s => s.scope_id)
    })
    
    // 获取策略列表
    const fetchStrategies = async () => {
      try {
        loading.value = true
        
        // 获取用户token
        const token = localStorage.getItem('token')
        if (!token) {
          ElMessage.error('请先登录')
          return
        }
        
        // 构建查询参数
        const params = {
          page: currentPage.value,
          page_size: pageSize.value,
          strategy_type: strategyType.value,
          scope_type: scopeType.value === 'all' ? 'all' : scopeType.value
        }
        
        if (searchKeyword.value) {
          params.search = searchKeyword.value
        }
        
        // 调用真实的API
        const response = await axios.get('http://localhost:5000/api/strategies', {
          params: params,
          headers: {
            'Authorization': `Bearer ${token}`
          }
        })
        
        if (response.data.code === 200) {
          strategies.value = response.data.data.strategies || []
          total.value = response.data.data.total || 0
        } else {
          throw new Error(response.data.message || '获取策略列表失败')
        }
      } catch (error) {
        console.error('获取策略列表失败:', error)
        ElMessage.error('获取策略列表失败，请重试')
      } finally {
        loading.value = false
      }
    }
    
    // 刷新策略列表
    const refreshStrategies = () => {
      fetchStrategies()
    }
    
    // 跳转到策略详情页面
    const goToStrategyDetail = (strategy) => {
      router.push({
        name: 'StrategyDetail',
        params: {
          creatorName: strategy.creator_name,
          strategyName: strategy.strategy_name
        }
      })
    }
    
    // 显示添加策略弹窗
    const showAddStrategyDialog = () => {
      isEditMode.value = false
      editingStrategy.value = null
      
      // 重置表单
      Object.assign(strategyForm, {
        strategy_name: '',
        public: true,
        scope_type: 'all',
        scope_id: '',
        position_count: 5,
        rebalance_interval: 5,
        buy_fee_rate: 0.001,
        sell_fee_rate: 0.001,
        strategy_desc: '',
        select_func: '',
        risk_control_func: ''
      })
      
      strategyDialogVisible.value = true
    }
    
    // 编辑策略
    const editStrategy = (strategy) => {
      isEditMode.value = true
      editingStrategy.value = strategy
      
      // 填充表单
      Object.assign(strategyForm, {
        strategy_name: strategy.strategy_name,
        public: strategy.public,
        scope_type: strategy.scope_type,
        scope_id: strategy.scope_id || '',
        position_count: strategy.position_count || 5,
        rebalance_interval: strategy.rebalance_interval || 5,
        buy_fee_rate: strategy.buy_fee_rate || 0.001,
        sell_fee_rate: strategy.sell_fee_rate || 0.001,
        strategy_desc: strategy.strategy_desc || '',
        select_func: strategy.select_func || '',
        risk_control_func: strategy.risk_control_func || ''
      })
      
      strategyDialogVisible.value = true
    }
    
    // 删除策略
    const deleteStrategy = (strategy) => {
      ElMessageBox.confirm(
        `确定要删除策略"${strategy.strategy_name}"吗？`,
        '确认删除',
        {
          confirmButtonText: '确定',
          cancelButtonText: '取消',
          type: 'warning'
        }
      ).then(async () => {
        try {
          loading.value = true
          
          // 获取用户token
          const token = localStorage.getItem('token')
          if (!token) {
            ElMessage.error('请先登录')
            return
          }
          
          // 调用删除API
          const response = await axios.delete(
            `http://localhost:5000/api/strategies/${strategy.creator_name}/${strategy.strategy_name}`,
            {
              headers: {
                'Authorization': `Bearer ${token}`
              }
            }
          )
          
          if (response.data.code === 200) {
            ElMessage.success('策略删除成功')
            // 重新获取策略列表
            await fetchStrategies()
          } else {
            throw new Error(response.data.message || '删除策略失败')
          }
        } catch (error) {
          console.error('删除策略失败:', error)
          ElMessage.error(error.response?.data?.message || '删除策略失败，请重试')
        } finally {
          loading.value = false
        }
      }).catch(() => {
        // 用户取消删除
      })
    }
    
    // 复制策略
    const copyStrategy = (strategy) => {
      const userInfo = getUserInfo()
      if (!userInfo) {
        ElMessage.error('请先登录')
        return
      }
      
      // 重置表单
      Object.assign(strategyForm, {
        strategy_name: `复制_${strategy.strategy_name}`,
        public: false, // 默认不公开
        scope_type: strategy.scope_type,
        scope_id: strategy.scope_id || '',
        position_count: strategy.position_count || 5,
        rebalance_interval: strategy.rebalance_interval || 5,
        buy_fee_rate: strategy.buy_fee_rate || 0.001,
        sell_fee_rate: strategy.sell_fee_rate || 0.001,
        strategy_desc: strategy.strategy_desc || '',
        select_func: strategy.select_func || '',
        risk_control_func: strategy.risk_control_func || ''
      })
      
      isEditMode.value = false
      editingStrategy.value = null
      strategyDialogVisible.value = true
      
      ElMessage.info('已复制策略，您可以修改后保存')
    }
    
    // 保存策略
    const saveStrategy = async () => {
      try {
        // 表单验证
        await strategyFormRef.value.validate()
        
        loading.value = true
        
        // 获取用户token
        const token = localStorage.getItem('token')
        if (!token) {
          ElMessage.error('请先登录')
          return
        }
        
        // 准备提交的数据
        const submitData = {
          ...strategyForm
        }
        
        let response
        if (isEditMode.value) {
          // 更新策略
          response = await axios.put(
            `http://localhost:5000/api/strategies/${editingStrategy.value.creator_name}/${editingStrategy.value.strategy_name}`,
            submitData,
            {
              headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
              }
            }
          )
        } else {
          // 创建新策略
          response = await axios.post(
            'http://localhost:5000/api/strategies',
            submitData,
            {
              headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
              }
            }
          )
        }
        
        if (response.data.code === 200) {
          ElMessage.success(isEditMode.value ? '策略更新成功' : '策略创建成功')
          strategyDialogVisible.value = false
          // 重新获取策略列表
          await fetchStrategies()
        } else {
          throw new Error(response.data.message || '保存策略失败')
        }
      } catch (error) {
        console.error('保存策略失败:', error)
        ElMessage.error(error.response?.data?.message || '保存策略失败，请重试')
      } finally {
        loading.value = false
      }
    }
    
    // 处理策略弹窗关闭
    const handleStrategyDialogClose = () => {
      strategyDialogVisible.value = false
      
      // 重置表单
      if (strategyFormRef.value) {
        strategyFormRef.value.resetFields()
      }
    }
    
    // 分页处理
    const handleSizeChange = (newSize) => {
      pageSize.value = newSize
      currentPage.value = 1
      fetchStrategies()
    }
    
    const handleCurrentChange = (newCurrent) => {
      currentPage.value = newCurrent
      fetchStrategies()
    }
    
    // 监听筛选条件变化
    watch([strategyType, scopeType], () => {
      currentPage.value = 1
      fetchStrategies()
    })
    
    // 监听搜索关键词变化（防抖处理）
    let searchTimeout = null
    watch(searchKeyword, () => {
      if (searchTimeout) {
        clearTimeout(searchTimeout)
      }
      searchTimeout = setTimeout(() => {
        currentPage.value = 1
        fetchStrategies()
      }, 500)
    })
    
    onMounted(() => {
      fetchStrategies()
    })
    
    return {
      loading,
      strategies,
      searchKeyword,
      scopeType,
      strategyType,
      currentPage,
      pageSize,
      total,
      strategyDialogVisible,
      isEditMode,
      editingStrategy,
      strategyFormRef,
      strategyForm,
      strategyRules,
      filteredStrategies,
      showScopeId,
      fetchStrategies,
      refreshStrategies,
      goToStrategyDetail,
      showAddStrategyDialog,
      editStrategy,
      deleteStrategy,
      copyStrategy,
      saveStrategy,
      handleStrategyDialogClose,
      handleSizeChange,
      handleCurrentChange,
      isCurrentUserCreator
    }
  }
}
</script>

<style scoped>
.strategy-list-container {
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
</style>