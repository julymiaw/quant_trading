<template>
  <div class="strategy-list-container">
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
import { ref, reactive, computed, onMounted } from 'vue'
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
      strategy_desc: ''
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
    
    // 计算筛选后的策略列表
    const filteredStrategies = computed(() => {
      let result = [...strategies.value]
      
      // 根据策略类型筛选
      if (strategyType.value === 'my') {
        const userInfo = getUserInfo()
        if (userInfo) {
          result = result.filter(s => s.creator_name === userInfo.user_name)
        }
      } else if (strategyType.value === 'system') {
        result = result.filter(s => s.creator_name === 'system')
      } else if (strategyType.value === 'public') {
        result = result.filter(s => s.public)
      }
      
      // 根据搜索关键词筛选
      if (searchKeyword.value) {
        const keyword = searchKeyword.value.toLowerCase()
        result = result.filter(s => 
          s.strategy_name.toLowerCase().includes(keyword) ||
          (s.strategy_desc && s.strategy_desc.toLowerCase().includes(keyword))
        )
      }
      
      // 根据生效范围筛选
      if (scopeType.value !== 'all') {
        result = result.filter(s => s.scope_type === scopeType.value)
      }
      
      // 更新总数
      total.value = result.length
      
      // 分页
      const start = (currentPage.value - 1) * pageSize.value
      const end = start + pageSize.value
      return result.slice(start, end)
    })
    
    // 是否显示scope_id列
    const showScopeId = computed(() => {
      return scopeType.value !== 'all' || strategies.value.some(s => s.scope_id)
    })
    
    // 获取策略列表
    const fetchStrategies = async () => {
      try {
        loading.value = true
        
        // 这里使用模拟数据，实际开发中应替换为真实的API调用
        // const response = await axios.get('/api/strategies')
        
        // 模拟策略数据
        const mockStrategies = [
          {
            id: '1',
            creator_name: 'system',
            strategy_name: '小市值策略',
            public: true,
            scope_type: 'all',
            scope_id: '',
            position_count: 3,
            rebalance_interval: 5,
            buy_fee_rate: 0.0003,
            sell_fee_rate: 0.0013,
            strategy_desc: '市值20-30亿，市值最小的3只',
            create_time: '2025-09-01 00:00:00',
            update_time: '2025-09-01 00:00:00'
          },
          {
            id: '2',
            creator_name: 'system',
            strategy_name: '双均线策略',
            public: true,
            scope_type: 'single_stock',
            scope_id: '000001.XSHE',
            position_count: 1,
            rebalance_interval: 1,
            buy_fee_rate: 0.0003,
            sell_fee_rate: 0.0013,
            strategy_desc: '5日均线上穿/下穿日线，择时买卖',
            create_time: '2025-09-01 00:00:00',
            update_time: '2025-09-01 00:00:00'
          },
          {
            id: '3',
            creator_name: 'system',
            strategy_name: 'MACD策略',
            public: true,
            scope_type: 'single_stock',
            scope_id: '000001.XSHE',
            position_count: 1,
            rebalance_interval: 1,
            buy_fee_rate: 0.0003,
            sell_fee_rate: 0.0013,
            strategy_desc: '9日MACD线下穿日线买入，上穿卖出',
            create_time: '2025-09-01 00:00:00',
            update_time: '2025-09-01 00:00:00'
          },
          {
            id: '4',
            creator_name: 'test_user',
            strategy_name: '自定义动量策略',
            public: false,
            scope_type: 'index',
            scope_id: '000300.XSHG',
            position_count: 10,
            rebalance_interval: 10,
            buy_fee_rate: 0.001,
            sell_fee_rate: 0.001,
            strategy_desc: '选择沪深300指数中动量最强的10只股票',
            create_time: '2025-09-10 10:00:00',
            update_time: '2025-09-10 10:00:00'
          }
        ]
        
        strategies.value = mockStrategies
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
        strategy_desc: ''
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
        strategy_desc: strategy.strategy_desc || ''
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
          
          // 这里使用模拟删除，实际开发中应替换为真实的API调用
          // await axios.delete(`/api/strategies/${strategy.id}`)
          
          // 模拟删除成功
          strategies.value = strategies.value.filter(s => s.id !== strategy.id)
          
          ElMessage.success('策略删除成功')
        } catch (error) {
          console.error('删除策略失败:', error)
          ElMessage.error('删除策略失败，请重试')
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
        strategy_desc: strategy.strategy_desc || ''
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
        
        // 这里使用模拟保存，实际开发中应替换为真实的API调用
        // if (isEditMode.value) {
        //   await axios.put(`/api/strategies/${editingStrategy.value.id}`, strategyForm)
        // } else {
        //   await axios.post('/api/strategies', strategyForm)
        // }
        
        // 模拟保存成功
        const userInfo = getUserInfo()
        const newStrategy = {
          ...strategyForm,
          id: isEditMode.value ? editingStrategy.value.id : Date.now().toString(),
          creator_name: isEditMode.value ? editingStrategy.value.creator_name : userInfo.user_name,
          create_time: isEditMode.value ? editingStrategy.value.create_time : new Date().toLocaleString('zh-CN'),
          update_time: new Date().toLocaleString('zh-CN')
        }
        
        if (isEditMode.value) {
          // 更新现有策略
          const index = strategies.value.findIndex(s => s.id === editingStrategy.value.id)
          if (index !== -1) {
            strategies.value[index] = newStrategy
          }
        } else {
          // 添加新策略
          strategies.value.unshift(newStrategy)
        }
        
        ElMessage.success(isEditMode.value ? '策略更新成功' : '策略添加成功')
        strategyDialogVisible.value = false
      } catch (error) {
        console.error('保存策略失败:', error)
        ElMessage.error('保存策略失败，请重试')
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
    }
    
    const handleCurrentChange = (newCurrent) => {
      currentPage.value = newCurrent
    }
    
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

.pagination-container {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}
</style>