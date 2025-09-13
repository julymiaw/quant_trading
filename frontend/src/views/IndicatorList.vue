<template>
  <div class="indicator-list-container">
    <!-- 页面标题和操作按钮 -->
    <div class="page-header">
      <h1>指标管理</h1>
      <div class="header-actions">
        <el-select v-model="indicatorType" placeholder="选择指标类型" style="width: 150px; margin-right: 10px;">
          <el-option label="我的指标" value="my" />
          <el-option label="系统指标" value="system" />
          <el-option label="公开指标" value="public" />
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
        clearable
      />
      <el-select v-model="isActive" placeholder="状态" style="width: 100px; margin-left: 10px;">
        <el-option label="全部" value="all" />
        <el-option label="启用" value="true" />
        <el-option label="禁用" value="false" />
      </el-select>
      <el-button type="primary" @click="refreshIndicators" style="margin-left: 10px;">
        <el-icon><Refresh /></el-icon>
        刷新
      </el-button>
    </div>
    
    <!-- 指标列表表格 -->
    <el-table
      v-loading="loading"
      :data="filteredIndicators"
      style="width: 100%"
      border
      row-key="id"
    >
      <el-table-column prop="indicator_name" label="指标名称" min-width="180">
        <template #default="scope">
          <el-link type="primary" :underline="false" @click="goToIndicatorDetail(scope.row)">
            {{ scope.row.indicator_name }}
          </el-link>
        </template>
      </el-table-column>
      <el-table-column prop="creator_name" label="创建者" width="120" />
      <el-table-column prop="is_active" label="状态" width="80">
        <template #default="scope">
          <el-switch 
            v-model="scope.row.is_active" 
            @change="toggleIndicatorStatus(scope.row)"
            :disabled="!isCurrentUserCreator(scope.row)"
          />
        </template>
      </el-table-column>
      <el-table-column prop="description" label="指标说明" show-overflow-tooltip min-width="200" />
      <el-table-column prop="create_time" label="创建时间" width="160" />
      <el-table-column label="操作" width="180" fixed="right">
        <template #default="scope">
          <el-button
            type="primary"
            size="small"
            @click="editIndicator(scope.row)"
            v-if="isCurrentUserCreator(scope.row)"
          >
            编辑
          </el-button>
          <el-button
            type="danger"
            size="small"
            @click="deleteIndicator(scope.row)"
            v-if="isCurrentUserCreator(scope.row)"
          >
            删除
          </el-button>
          <el-button
            type="default"
            size="small"
            @click="copyIndicator(scope.row)"
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
    
    <!-- 添加/编辑指标弹窗 -->
    <el-dialog
      v-model="indicatorDialogVisible"
      :title="isEditMode ? '编辑指标' : '添加指标'"
      width="600px"
      :before-close="handleIndicatorDialogClose"
    >
      <el-form
        ref="indicatorFormRef"
        :model="indicatorForm"
        :rules="indicatorRules"
        label-width="120px"
      >
        <el-form-item label="指标名称" prop="indicator_name">
          <el-input v-model="indicatorForm.indicator_name" placeholder="请输入指标名称" />
        </el-form-item>
        <el-form-item label="计算函数" prop="calculation_method">
          <el-input 
            v-model="indicatorForm.calculation_method" 
            type="textarea" 
            :rows="8"
            placeholder="请输入指标计算函数"
          />
        </el-form-item>
        <el-form-item label="指标说明" prop="description">
          <el-input v-model="indicatorForm.description" type="textarea" placeholder="请输入指标说明" />
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
    
    <!-- 添加/编辑指标参数弹窗 -->
    <el-dialog
      v-model="indicatorParamsDialogVisible"
      :title="`${currentIndicator?.indicator_name || ''} - 参数管理`"
      width="800px"
      :before-close="handleIndicatorParamsDialogClose"
    >
      <div class="indicator-params-content">
        <div class="params-list">
          <h3>已添加参数</h3>
          <el-table
            :data="currentIndicatorParams"
            style="width: 100%"
            border
            v-if="currentIndicatorParams.length > 0"
          >
            <el-table-column prop="param_name" label="参数ID" width="150" />
            <el-table-column prop="data_id" label="数据来源ID" width="200" />
            <el-table-column prop="param_type" label="参数类型" width="120">
              <template #default="scope">
                <el-tag :type="scope.row.param_type === 'table' ? 'primary' : 'success'">
                  {{ scope.row.param_type === 'table' ? '数据表' : '指标' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="pre_period" label="向前取历史天数" width="150" />
            <el-table-column prop="post_period" label="向后预测天数" width="150" />
            <el-table-column prop="agg_func" label="聚合函数" width="120" />
            <el-table-column label="操作" width="80" fixed="right">
              <template #default="scope">
                <el-button type="danger" size="small" @click="removeIndicatorParam(scope.row)">
                  删除
                </el-button>
              </template>
            </el-table-column>
          </el-table>
          <div v-else class="empty-params">
            <el-empty description="暂无参数" />
          </div>
        </div>
        
        <div class="add-param-section">
          <h3>添加参数</h3>
          <el-form
            ref="addParamFormRef"
            :model="addParamForm"
            :rules="addParamRules"
            label-width="120px"
            size="small"
          >
            <el-row :gutter="20">
              <el-col :span="12">
                <el-form-item label="参数ID" prop="param_name">
                  <el-input v-model="addParamForm.param_name" placeholder="请输入参数ID" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="参数类型" prop="param_type">
                  <el-select v-model="addParamForm.param_type" placeholder="请选择参数类型">
                    <el-option label="数据表" value="table" />
                    <el-option label="指标" value="indicator" />
                  </el-select>
                </el-form-item>
              </el-col>
            </el-row>
            <el-row :gutter="20">
              <el-col :span="12">
                <el-form-item label="数据来源ID" prop="data_id">
                  <el-autocomplete
                    v-model="addParamForm.data_id"
                    :fetch-suggestions="queryDataSources"
                    placeholder="请输入数据来源ID"
                    :trigger-on-focus="false"
                    style="width: 100%"
                    :remote="true"
                  />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="聚合函数" prop="agg_func">
                  <el-select v-model="addParamForm.agg_func" placeholder="请选择聚合函数" clearable>
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
            <el-row :gutter="20">
              <el-col :span="12">
                <el-form-item label="向前取历史天数" prop="pre_period">
                  <el-input-number v-model="addParamForm.pre_period" :min="0" :max="365" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="向后预测天数" prop="post_period">
                  <el-input-number v-model="addParamForm.post_period" :min="0" :max="365" />
                </el-form-item>
              </el-col>
            </el-row>
            <el-button type="primary" @click="addIndicatorParam" style="margin-top: 10px;">
              添加参数
            </el-button>
          </el-form>
        </div>
      </div>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="handleIndicatorParamsDialogClose">关闭</el-button>
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
  name: 'IndicatorList',
  components: {
    Plus,
    Search,
    Refresh
  },
  setup() {
    const router = useRouter()
    const loading = ref(false)
    const indicators = ref([])
    const searchKeyword = ref('')
    const isActive = ref('all')
    const indicatorType = ref('my')
    const currentPage = ref(1)
    const pageSize = ref(10)
    const total = ref(0)
    
    // 弹窗相关状态
    const indicatorDialogVisible = ref(false)
    const isEditMode = ref(false)
    const editingIndicator = ref(null)
    const indicatorFormRef = ref(null)
    
    // 指标参数相关状态
    const indicatorParamsDialogVisible = ref(false)
    const currentIndicator = ref(null)
    const currentIndicatorParams = ref([])
    const addParamFormRef = ref(null)
    
    // 指标表单数据
    const indicatorForm = reactive({
      indicator_name: '',
      calculation_method: '',
      description: '',
      is_active: true
    })
    
    // 添加参数表单数据
    const addParamForm = reactive({
      param_name: '',
      data_id: '',
      param_type: 'table',
      pre_period: 0,
      post_period: 0,
      agg_func: null
    })
    
    // 表单验证规则
    const indicatorRules = {
      indicator_name: [
        { required: true, message: '请输入指标名称', trigger: 'blur' },
        { min: 1, max: 100, message: '指标名称长度在 1 到 100 个字符', trigger: 'blur' }
      ],
      calculation_method: [
        { required: true, message: '请输入计算函数', trigger: 'blur' },
        { min: 10, max: 10000, message: '计算函数长度在 10 到 10000 个字符', trigger: 'blur' }
      ]
    }
    
    const addParamRules = {
      param_name: [
        { required: true, message: '请输入参数ID', trigger: 'blur' },
        { min: 1, max: 50, message: '参数ID长度在 1 到 50 个字符', trigger: 'blur' }
      ],
      data_id: [
        { required: true, message: '请输入数据来源ID', trigger: 'blur' }
      ],
      param_type: [
        { required: true, message: '请选择参数类型', trigger: 'change' }
      ],
      pre_period: [
        { required: true, message: '请输入向前取历史天数', trigger: 'change' },
        { type: 'number', min: 0, message: '向前取历史天数不能小于0', trigger: 'change' }
      ],
      post_period: [
        { required: true, message: '请输入向后预测天数', trigger: 'change' },
        { type: 'number', min: 0, message: '向后预测天数不能小于0', trigger: 'change' }
      ]
    }
    
    // 获取用户信息
    const getUserInfo = () => {
      const storedUserInfo = localStorage.getItem('userInfo')
      return storedUserInfo ? JSON.parse(storedUserInfo) : null
    }
    
    // 判断是否是当前用户创建的指标
    const isCurrentUserCreator = (indicator) => {
      const userInfo = getUserInfo()
      return userInfo && indicator.creator_name === userInfo.user_name
    }
    
    // 由于筛选和分页都在后端完成，这里直接返回indicators
    const filteredIndicators = computed(() => {
      return indicators.value
    })
    
    // 获取指标列表
    const fetchIndicators = async () => {
      try {
        loading.value = true
        
        const token = localStorage.getItem('token')
        if (!token) {
          ElMessage.error('请先登录')
          router.push('/login')
          return
        }
        
        // 构建查询参数
        const params = {
          page: currentPage.value,
          limit: pageSize.value
        }
        
        // 根据指标类型添加筛选条件
        if (indicatorType.value === 'my') {
          const userInfo = getUserInfo()
          if (userInfo) {
            params.creator_name = userInfo.user_name
          }
        } else if (indicatorType.value === 'system') {
          params.creator_name = 'system'
        }
        
        // 添加搜索条件
        if (searchKeyword.value.trim()) {
          params.search = searchKeyword.value.trim()
        }
        
        // 添加状态筛选
        if (isActive.value !== 'all') {
          params.is_enabled = isActive.value === 'true' ? 1 : 0
        }
        
        const response = await axios.get('/api/indicators', {
          params,
          headers: {
            'Authorization': `Bearer ${token}`
          }
        })
        
        if (response.data) {
          // 后端返回的数据结构: {data: [...], pagination: {...}}
          const indicatorList = response.data.data || response.data
          
          // 后端返回的字段已经是正确的格式，不需要转换
          indicators.value = indicatorList
          total.value = response.data.pagination ? response.data.pagination.total : indicatorList.length
        }
      } catch (error) {
        console.error('获取指标列表失败:', error)
        if (error.response) {
          if (error.response.status === 401) {
            ElMessage.error('登录已过期，请重新登录')
            router.push('/login')
          } else {
            ElMessage.error(`获取指标列表失败: ${error.response.data.message || error.response.statusText}`)
          }
        } else {
          ElMessage.error('获取指标列表失败，请重试')
        }
      } finally {
        loading.value = false
      }
    }
    
    // 刷新指标列表
    const refreshIndicators = () => {
      fetchIndicators()
    }
    
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
      openIndicatorParamsDialog(indicator)
    }
    
    // 显示添加指标弹窗
    const showAddIndicatorDialog = () => {
      isEditMode.value = false
      editingIndicator.value = null
      
      // 重置表单
      Object.assign(indicatorForm, {
        indicator_name: '',
        calculation_method: '',
        description: '',
        is_active: true
      })
      
      indicatorDialogVisible.value = true
    }
    
    // 编辑指标
    const editIndicator = (indicator) => {
      isEditMode.value = true
      editingIndicator.value = indicator
      
      // 填充表单
      Object.assign(indicatorForm, {
        indicator_name: indicator.indicator_name,
        calculation_method: indicator.calculation_method,
        description: indicator.description || '',
        is_active: indicator.is_active
      })
      
      indicatorDialogVisible.value = true
    }
    
    // 删除指标
    const deleteIndicator = (indicator) => {
      ElMessageBox.confirm(
        `确定要删除指标"${indicator.indicator_name}"吗？`,
        '确认删除',
        {
          confirmButtonText: '确定',
          cancelButtonText: '取消',
          type: 'warning'
        }
      ).then(async () => {
        try {
          loading.value = true
          
          const token = localStorage.getItem('token')
          if (!token) {
            ElMessage.error('请先登录')
            router.push('/login')
            return
          }
          
          // 使用后端API删除指标
          const indicatorId = `${indicator.creator_name}.${indicator.indicator_name}`
          await axios.delete(`/api/indicators/${indicatorId}`, {
            headers: {
              'Authorization': `Bearer ${token}`
            }
          })
          
          ElMessage.success('指标删除成功')
          
          // 刷新列表
          await fetchIndicators()
        } catch (error) {
          console.error('删除指标失败:', error)
          if (error.response) {
            ElMessage.error(`删除指标失败: ${error.response.data.message || error.response.statusText}`)
          } else {
            ElMessage.error('删除指标失败，请重试')
          }
        } finally {
          loading.value = false
        }
      }).catch(() => {
        // 用户取消删除
      })
    }
    
    // 复制指标
    const copyIndicator = (indicator) => {
      const userInfo = getUserInfo()
      if (!userInfo) {
        ElMessage.error('请先登录')
        return
      }
      
      // 重置表单
      Object.assign(indicatorForm, {
        indicator_name: `复制_${indicator.indicator_name}`,
        calculation_method: indicator.calculation_method,
        description: indicator.description || '',
        is_active: true
      })
      
      isEditMode.value = false
      editingIndicator.value = null
      indicatorDialogVisible.value = true
      
      ElMessage.info('已复制指标，您可以修改后保存')
    }
    
    // 保存指标
    const saveIndicator = async () => {
      try {
        // 表单验证
        await indicatorFormRef.value.validate()
        
        loading.value = true
        
        const token = localStorage.getItem('token')
        if (!token) {
          ElMessage.error('请先登录')
          router.push('/login')
          return
        }
        
        // 准备提交数据，使用后端期望的字段名
        const submitData = {
          indicator_name: indicatorForm.indicator_name,
          calculation_method: indicatorForm.calculation_method,
          description: indicatorForm.description || '',
          is_active: indicatorForm.is_active
        }
        
        let response
        if (isEditMode.value) {
          // 编辑模式：PUT请求
          const indicatorId = `${editingIndicator.value.creator_name}.${editingIndicator.value.indicator_name}`
          response = await axios.put(`/api/indicators/${indicatorId}`, submitData, {
            headers: {
              'Authorization': `Bearer ${token}`,
              'Content-Type': 'application/json'
            }
          })
        } else {
          // 新建模式：POST请求
          response = await axios.post('/api/indicators', submitData, {
            headers: {
              'Authorization': `Bearer ${token}`,
              'Content-Type': 'application/json'
            }
          })
        }
        
        if (response.data) {
          ElMessage.success(isEditMode.value ? '指标更新成功' : '指标创建成功')
          
          // 关闭弹窗
          handleIndicatorDialogClose()
          
          // 刷新列表
          await fetchIndicators()
        }
        
      } catch (error) {
        console.error('保存指标失败:', error)
        if (error.response) {
          if (error.response.status === 401) {
            ElMessage.error('登录已过期，请重新登录')
            router.push('/login')
          } else {
            ElMessage.error(`保存指标失败: ${error.response.data.message || error.response.statusText}`)
          }
        } else {
          ElMessage.error('保存指标失败，请重试')
        }
      } finally {
        loading.value = false
      }
    }
    
    // 切换指标状态
    const toggleIndicatorStatus = async (indicator) => {
      try {
        loading.value = true
        
        const token = localStorage.getItem('token')
        if (!token) {
          ElMessage.error('请先登录')
          router.push('/login')
          return
        }
        
        const indicatorId = `${indicator.creator_name}.${indicator.indicator_name}`
        await axios.put(`/api/indicators/${indicatorId}/toggle-status`, {}, {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        })
        
        ElMessage.success(`指标${indicator.is_active ? '启用' : '禁用'}成功`)
      } catch (error) {
        console.error('切换指标状态失败:', error)
        // 恢复原状态
        indicator.is_active = !indicator.is_active
        if (error.response) {
          if (error.response.status === 401) {
            ElMessage.error('登录已过期，请重新登录')
            router.push('/login')
          } else {
            ElMessage.error(`切换指标状态失败: ${error.response.data.message || error.response.statusText}`)
          }
        } else {
          ElMessage.error('切换指标状态失败，请重试')
        }
      } finally {
        loading.value = false
      }
    }
    
    // 打开指标参数管理弹窗
    const openIndicatorParamsDialog = (indicator) => {
      currentIndicator.value = indicator
      
      // 获取指标参数
      fetchIndicatorParams(indicator)
      
      // 重置添加参数表单
      Object.assign(addParamForm, {
        param_name: '',
        data_id: '',
        param_type: 'table',
        pre_period: 0,
        post_period: 0,
        agg_func: null
      })
      
      indicatorParamsDialogVisible.value = true
    }
    
    // 获取指标参数
    const fetchIndicatorParams = async (indicator) => {
      try {
        // 这里使用模拟数据，实际开发中应替换为真实的API调用
        // const response = await axios.get(`/api/indicators/${indicator.creator_name}/${indicator.indicator_name}/params`)
        
        // 模拟指标参数数据
        let mockParams = []
        
        if (indicator.indicator_name === 'MACD') {
          mockParams = [
            {
              param_name: 'close_price',
              data_id: 'daily.close',
              param_type: 'table',
              pre_period: 26, // MACD通常使用26天的数据
              post_period: 0,
              agg_func: null
            }
          ]
        } else if (indicator.indicator_name === 'RSI') {
          mockParams = [
            {
              param_name: 'close_price',
              data_id: 'daily.close',
              param_type: 'table',
              pre_period: 14, // RSI通常使用14天的数据
              post_period: 0,
              agg_func: null
            }
          ]
        } else if (indicator.indicator_name === 'KDJ') {
          mockParams = [
            {
              param_name: 'high_price',
              data_id: 'daily.high',
              param_type: 'table',
              pre_period: 9, // KDJ通常使用9天的数据
              post_period: 0,
              agg_func: null
            },
            {
              param_name: 'low_price',
              data_id: 'daily.low',
              param_type: 'table',
              pre_period: 9,
              post_period: 0,
              agg_func: null
            },
            {
              param_name: 'close_price',
              data_id: 'daily.close',
              param_type: 'table',
              pre_period: 9,
              post_period: 0,
              agg_func: null
            }
          ]
        }
        
        currentIndicatorParams.value = mockParams
      } catch (error) {
        console.error('获取指标参数失败:', error)
        ElMessage.error('获取指标参数失败，请重试')
      }
    }
    
    // 查询数据源
    const queryDataSources = (queryString, callback) => {
      // 模拟数据源列表
      const dataSources = [
        'valuation.market_cap',
        'valuation.pe_ratio',
        'valuation.pb_ratio',
        'daily.open',
        'daily.close',
        'daily.high',
        'daily.low',
        'daily.volume',
        'daily.amount',
        'indicator.MACD',
        'indicator.KDJ',
        'indicator.RSI'
      ]
      
      // 根据查询字符串过滤
      const results = queryString
        ? dataSources.filter(source => source.toLowerCase().includes(queryString.toLowerCase()))
        : dataSources
      
      // 格式化为autocomplete需要的格式
      const suggestions = results.map(source => ({
        value: source
      }))
      
      callback(suggestions)
    }
    
    // 添加指标参数
    const addIndicatorParam = async () => {
      try {
        // 表单验证
        await addParamFormRef.value.validate()
        
        loading.value = true
        
        // 检查参数ID是否已存在
        const exists = currentIndicatorParams.value.some(p => p.param_name === addParamForm.param_name)
        if (exists) {
          ElMessage.error('参数ID已存在，请使用其他ID')
          loading.value = false
          return
        }
        
        // 这里使用模拟保存，实际开发中应替换为真实的API调用
        // await axios.post(
        //   `/api/indicators/${currentIndicator.value.creator_name}/${currentIndicator.value.indicator_name}/params`, 
        //   addParamForm
        // )
        
        // 添加参数到列表
        currentIndicatorParams.value.push({ ...addParamForm })
        
        // 重置表单
        Object.assign(addParamForm, {
          param_name: '',
          data_id: '',
          param_type: 'table',
          pre_period: 0,
          post_period: 0,
          agg_func: null
        })
        
        ElMessage.success('参数添加成功')
      } catch (error) {
        console.error('添加参数失败:', error)
        ElMessage.error('添加参数失败，请重试')
      } finally {
        loading.value = false
      }
    }
    
    // 删除指标参数
    const removeIndicatorParam = (param) => {
      ElMessageBox.confirm(
        `确定要删除参数"${param.param_name}"吗？`,
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
          // await axios.delete(
          //   `/api/indicators/${currentIndicator.value.creator_name}/${currentIndicator.value.indicator_name}/params/${param.param_name}`
          // )
          
          // 从列表中删除参数
          currentIndicatorParams.value = currentIndicatorParams.value.filter(p => p.param_name !== param.param_name)
          
          ElMessage.success('参数删除成功')
        } catch (error) {
          console.error('删除参数失败:', error)
          ElMessage.error('删除参数失败，请重试')
        } finally {
          loading.value = false
        }
      }).catch(() => {
        // 用户取消删除
      })
    }
    
    // 处理指标弹窗关闭
    const handleIndicatorDialogClose = () => {
      indicatorDialogVisible.value = false
      
      // 重置表单
      if (indicatorFormRef.value) {
        indicatorFormRef.value.resetFields()
      }
    }
    
    // 处理指标参数弹窗关闭
    const handleIndicatorParamsDialogClose = () => {
      indicatorParamsDialogVisible.value = false
      
      // 重置表单
      if (addParamFormRef.value) {
        addParamFormRef.value.resetFields()
      }
    }
    
    // 分页处理
    const handleSizeChange = (newSize) => {
      pageSize.value = newSize
      currentPage.value = 1
      fetchIndicators()
    }
    
    const handleCurrentChange = (newCurrent) => {
      currentPage.value = newCurrent
      fetchIndicators()
    }
    
    // 监听筛选条件变化 (不包括搜索关键字，因为搜索需要防抖)
    watch([indicatorType, isActive, currentPage, pageSize], () => {
      fetchIndicators()
    })
    
    // 搜索关键字使用防抖
    let searchTimer = null
    watch(searchKeyword, () => {
      if (searchTimer) {
        clearTimeout(searchTimer)
      }
      searchTimer = setTimeout(() => {
        currentPage.value = 1 // 搜索时重置到第一页
        fetchIndicators()
      }, 500) // 500ms防抖
    })
    
    onMounted(() => {
      fetchIndicators()
    })
    
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
      indicatorParamsDialogVisible,
      currentIndicator,
      currentIndicatorParams,
      addParamFormRef,
      addParamForm,
      addParamRules,
      filteredIndicators,
      fetchIndicators,
      refreshIndicators,
      goToIndicatorDetail,
      showAddIndicatorDialog,
      editIndicator,
      deleteIndicator,
      copyIndicator,
      saveIndicator,
      toggleIndicatorStatus,
      openIndicatorParamsDialog,
      fetchIndicatorParams,
      queryDataSources,
      addIndicatorParam,
      removeIndicatorParam,
      handleIndicatorDialogClose,
      handleIndicatorParamsDialogClose,
      handleSizeChange,
      handleCurrentChange,
      isCurrentUserCreator
    }
  }
}
</script>

<style scoped>
.indicator-list-container {
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
</style>