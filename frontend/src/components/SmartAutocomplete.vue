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
        @click="selectSuggestion(suggestion, index)"
        @mouseenter="selectedIndex = index">
        {{ suggestion }}
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
      validator: (value) => ["策略", "参数", "指标", "数据表"].includes(value),
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

    // 处理输入事件
    const handleInput = (value) => {
      inputValue.value = value;

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
      if (inputValue.value || suggestions.value.length > 0) {
        showSuggestions.value = true;
      } else {
        fetchSuggestions("");
      }
    };

    // 处理失焦事件
    const handleBlur = () => {
      // 延迟隐藏，以便点击建议项能够正常工作
      setTimeout(() => {
        showSuggestions.value = false;
        selectedIndex.value = -1;
      }, 200);
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
          suggestions.value = response.data.suggestions || [];
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
      inputValue.value = suggestion;
      selectedIndex.value = index;
      showSuggestions.value = false;

      emit("select", suggestion);

      // 让输入框重新获得焦点
      nextTick(() => {
        inputRef.value?.focus();
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
          if (selectedIndex.value >= 0) {
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
