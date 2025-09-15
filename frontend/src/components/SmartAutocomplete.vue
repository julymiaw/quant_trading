<template>
  <div class="smart-autocomplete">
    <el-input
      v-model="inputValue"
      :placeholder="placeholder"
      :clearable="clearable"
      @input="handleInput"
      @focus="handleFocus"
      @blur="handleBlur"
      ref="inputRef" />
    <div
      v-if="showSuggestions && suggestions.length > 0"
      class="suggestions-dropdown"
      ref="suggestionsRef">
      <div
        v-for="(suggestion, index) in suggestions"
        :key="index"
        :class="['suggestion-item', { active: selectedIndex === index }]"
        @click.stop="selectSuggestion(suggestion, index)"
        @mousedown.prevent
        @mouseenter="selectedIndex = index">
        <template v-if="typeof suggestion === 'string'">
          {{ suggestion }}
        </template>
        <template v-else>
          <span style="font-weight: 500">{{ suggestion.code }}</span>
          <span style="color: #999; margin-left: 8px">{{
            suggestion.name
          }}</span>
        </template>
      </div>
      <div v-if="suggestions.length > 5" class="scroll-hint">
        滚动查看更多选项...
      </div>
    </div>
  </div>
</template>

<script>
import { ref, watch, nextTick } from "vue";
import axios from "axios";

export default {
  name: "SmartAutocomplete",
  props: {
    modelValue: {
      type: String,
      default: "",
    },
    nodeType: {
      type: String,
      required: true,
      // 扩展支持股票/指数/基准等类型
      validator: (value) =>
        ["策略", "参数", "指标", "数据表", "股票", "指数", "基准"].includes(
          value
        ),
    },
    placeholder: {
      type: String,
      default: "请输入...",
    },
    clearable: {
      type: Boolean,
      default: true,
    },
  },
  emits: ["update:modelValue", "select"],
  setup(props, { emit }) {
    const inputValue = ref(props.modelValue);
    const suggestions = ref([]);
    const showSuggestions = ref(false);
    const selectedIndex = ref(-1);
    const inputRef = ref(null);
    const suggestionsRef = ref(null);

    let fetchTimeout = null;

    // 监听modelValue变化
    watch(
      () => props.modelValue,
      (newValue) => {
        inputValue.value = newValue;
      }
    );

    // 监听inputValue变化
    watch(inputValue, (newValue) => {
      emit("update:modelValue", newValue);
    });

    // 监听nodeType变化，重新获取建议
    watch(
      () => props.nodeType,
      (newNodeType, oldNodeType) => {
        if (newNodeType !== oldNodeType) {
          // 清空当前建议列表
          suggestions.value = [];
          selectedIndex.value = -1;

          // 如果输入框有焦点或有内容，重新获取建议
          if (showSuggestions.value || inputValue.value) {
            fetchSuggestions(inputValue.value);
          }
        }
      }
    );

    // 处理输入事件
    const handleInput = (value) => {
      inputValue.value = value;
      emit("update:modelValue", value);

      // 重置选中索引
      selectedIndex.value = -1;

      // 防抖处理
      if (fetchTimeout) {
        clearTimeout(fetchTimeout);
      }

      fetchTimeout = setTimeout(() => {
        fetchSuggestions(value);
      }, 300);
    };

    // 处理焦点事件
    const handleFocus = () => {
      // 总是重新获取建议，确保 nodeType 变化后能正确更新
      fetchSuggestions(inputValue.value || "");
    };

    // 处理失焦事件
    const handleBlur = (event) => {
      // 检查焦点是否移动到建议下拉框内
      setTimeout(() => {
        const activeElement = document.activeElement;
        const suggestionsEl = suggestionsRef.value;

        // 如果焦点不在建议框内，才隐藏下拉框
        if (!suggestionsEl || !suggestionsEl.contains(activeElement)) {
          showSuggestions.value = false;
          selectedIndex.value = -1;
        }
      }, 100);
    };

    // 获取建议
    const fetchSuggestions = async (inputText) => {
      try {
        const token = localStorage.getItem("token");
        if (!token) {
          console.warn("未找到认证token");
          return;
        }

        const response = await axios.post(
          "/api/suggestions",
          {
            node_type: props.nodeType,
            input_text: inputText || "",
          },
          {
            headers: {
              Authorization: `Bearer ${token}`,
              "Content-Type": "application/json",
            },
          }
        );

        if (response.data.success) {
          const raw = response.data.suggestions || [];
          suggestions.value = raw.map((it) => {
            if (typeof it === "string") return it;
            // 支持后端返回 {code, name} 或 {ts_code, name}
            if (it && (it.code || it.ts_code)) {
              return {
                code: it.code || it.ts_code,
                name: it.name || it.fullname || "",
              };
            }
            return String(it);
          });
          showSuggestions.value = suggestions.value.length > 0;
          selectedIndex.value = -1;
        } else {
          console.error("获取建议失败:", response.data.error);
          suggestions.value = [];
          showSuggestions.value = false;
        }
      } catch (error) {
        console.error("获取建议时发生错误:", error);
        suggestions.value = [];
        showSuggestions.value = false;
      }
    };

    // 选择建议
    const selectSuggestion = (suggestion, index) => {
      // 直接设置输入框的值
      const valueToSet =
        typeof suggestion === "string" ? suggestion : suggestion.code;
      inputValue.value = valueToSet;
      selectedIndex.value = index;
      showSuggestions.value = false;

      // 触发事件通知父组件
      emit("update:modelValue", valueToSet);
      emit("select", suggestion);

      // 让输入框重新获得焦点
      nextTick(() => {
        if (inputRef.value && inputRef.value.$el) {
          const input = inputRef.value.$el.querySelector("input");
          if (input) {
            input.focus();
            // 将光标移到文本末尾
            input.setSelectionRange(valueToSet.length, valueToSet.length);
          }
        }
      });
    };

    // 键盘导航
    const handleKeydown = (event) => {
      if (!showSuggestions.value || suggestions.value.length === 0) {
        return;
      }

      switch (event.key) {
        case "ArrowDown":
          event.preventDefault();
          selectedIndex.value = Math.min(
            selectedIndex.value + 1,
            suggestions.value.length - 1
          );
          scrollToSelected();
          break;
        case "ArrowUp":
          event.preventDefault();
          selectedIndex.value = Math.max(selectedIndex.value - 1, -1);
          scrollToSelected();
          break;
        case "Enter":
          event.preventDefault();
          if (
            selectedIndex.value >= 0 &&
            suggestions.value[selectedIndex.value]
          ) {
            selectSuggestion(
              suggestions.value[selectedIndex.value],
              selectedIndex.value
            );
          }
          break;
        case "Escape":
          showSuggestions.value = false;
          selectedIndex.value = -1;
          break;
      }
    };

    // 滚动到选中项
    const scrollToSelected = () => {
      if (selectedIndex.value >= 0 && suggestionsRef.value) {
        const selectedItem = suggestionsRef.value.children[selectedIndex.value];
        if (selectedItem) {
          selectedItem.scrollIntoView({ block: "nearest" });
        }
      }
    };

    return {
      inputValue,
      suggestions,
      showSuggestions,
      selectedIndex,
      inputRef,
      suggestionsRef,
      handleInput,
      handleFocus,
      handleBlur,
      selectSuggestion,
      handleKeydown,
    };
  },
  mounted() {
    // 添加键盘事件监听
    this.$refs.inputRef.$el
      .querySelector("input")
      .addEventListener("keydown", this.handleKeydown);
  },
  beforeUnmount() {
    // 清理事件监听
    const inputEl = this.$refs.inputRef?.$el?.querySelector("input");
    if (inputEl) {
      inputEl.removeEventListener("keydown", this.handleKeydown);
    }
  },
};
</script>

<style scoped>
.smart-autocomplete {
  position: relative;
  width: 100%;
}

.suggestions-dropdown {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  background: white;
  border: 1px solid #dcdfe6;
  border-top: none;
  border-radius: 0 0 4px 4px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  max-height: 200px;
  overflow-y: auto;
  z-index: 1000;
}

/* 自定义滚动条样式 */
.suggestions-dropdown::-webkit-scrollbar {
  width: 8px;
}

.suggestions-dropdown::-webkit-scrollbar-track {
  background: #f1f1f1;
  border-radius: 4px;
}

.suggestions-dropdown::-webkit-scrollbar-thumb {
  background: #c1c1c1;
  border-radius: 4px;
}

.suggestions-dropdown::-webkit-scrollbar-thumb:hover {
  background: #a8a8a8;
}

.suggestion-item {
  padding: 10px 12px;
  cursor: pointer;
  border-bottom: 1px solid #f5f5f5;
  font-size: 14px;
  color: #606266;
  transition: background-color 0.2s;
}

.suggestion-item:hover,
.suggestion-item.active {
  background-color: #f5f7fa;
  color: #409eff;
}

.suggestion-item:last-child {
  border-bottom: none;
}

.scroll-hint {
  padding: 8px 12px;
  text-align: center;
  font-size: 12px;
  color: #909399;
  background-color: #fafafa;
  border-top: 1px solid #f0f0f0;
}
</style>
