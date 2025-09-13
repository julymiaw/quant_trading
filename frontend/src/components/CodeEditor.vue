<template>
  <div class="code-editor-container">
    <div ref="editorRef" class="code-editor"></div>
  </div>
</template>

<script>
import { ref, onMounted, onUnmounted, watch } from "vue";
import { EditorView } from "@codemirror/view";
import { EditorState } from "@codemirror/state";
import { python } from "@codemirror/lang-python";
import { oneDark } from "@codemirror/theme-one-dark";
import { highlightActiveLineGutter, lineNumbers } from "@codemirror/view";
import { highlightActiveLine } from "@codemirror/view";
import { bracketMatching } from "@codemirror/language";
import { closeBrackets } from "@codemirror/autocomplete";
import { history } from "@codemirror/commands";
import { foldGutter } from "@codemirror/language";
import { indentOnInput } from "@codemirror/language";
import { defaultKeymap } from "@codemirror/commands";
import { keymap } from "@codemirror/view";

export default {
  name: "CodeEditor",
  props: {
    modelValue: {
      type: String,
      default: "",
    },
    placeholder: {
      type: String,
      default: "",
    },
    defaultCode: {
      type: String,
      default: "",
    },
    height: {
      type: String,
      default: "200px",
    },
    readonly: {
      type: Boolean,
      default: false,
    },
  },
  emits: ["update:modelValue"],
  setup(props, { emit }) {
    const editorRef = ref(null);
    let editorView = null;

    const createEditor = () => {
      if (!editorRef.value) return;

      // 如果有默认代码且当前值为空，使用默认代码
      const initialValue = props.modelValue || props.defaultCode || "";

      const state = EditorState.create({
        doc: initialValue,
        extensions: [
          // 核心功能
          lineNumbers(),
          highlightActiveLineGutter(),
          highlightActiveLine(),
          history(),
          foldGutter(),
          indentOnInput(),
          bracketMatching(),
          closeBrackets(),

          // Python语法高亮
          python(),

          // 主题
          oneDark,

          // 键盘映射
          keymap.of(defaultKeymap),

          // 更新监听器
          EditorView.updateListener.of((update) => {
            if (update.docChanged) {
              emit("update:modelValue", update.state.doc.toString());
            }
          }),

          // 主题配置
          EditorView.theme({
            "&": {
              height: props.height,
              minHeight: "200px",
              fontSize: "14px",
            },
            ".cm-editor": {
              height: "100%",
              minHeight: "200px",
            },
            ".cm-focused": {
              outline: "none",
            },
          }),

          // 只读模式
          ...(props.readonly ? [EditorView.editable.of(false)] : []),
        ],
      });

      editorView = new EditorView({
        state,
        parent: editorRef.value,
      });

      // 如果使用了默认代码，确保父组件知道这个值
      if (!props.modelValue && props.defaultCode) {
        emit("update:modelValue", props.defaultCode);
      }
    };

    const destroyEditor = () => {
      if (editorView) {
        editorView.destroy();
        editorView = null;
      }
    };

    // 监听modelValue变化，更新编辑器内容
    watch(
      () => props.modelValue,
      (newValue) => {
        if (editorView && newValue !== editorView.state.doc.toString()) {
          editorView.dispatch({
            changes: {
              from: 0,
              to: editorView.state.doc.length,
              insert: newValue || props.defaultCode || "",
            },
          });
        }
      }
    );

    // 监听defaultCode变化，如果当前值为空则使用默认代码
    watch(
      () => props.defaultCode,
      (newDefaultCode) => {
        if (editorView && !props.modelValue && newDefaultCode) {
          editorView.dispatch({
            changes: {
              from: 0,
              to: editorView.state.doc.length,
              insert: newDefaultCode,
            },
          });
          emit("update:modelValue", newDefaultCode);
        }
      }
    );

    onMounted(() => {
      createEditor();
    });

    onUnmounted(() => {
      destroyEditor();
    });

    return {
      editorRef,
    };
  },
};
</script>

<style scoped>
.code-editor-container {
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  overflow: hidden;
  min-height: 200px;
}

.code-editor {
  width: 100%;
  min-height: 200px;
}

.code-editor :deep(.cm-editor) {
  height: 100%;
}

.code-editor :deep(.cm-focused) {
  outline: 1px solid #409eff;
  outline-offset: -1px;
}
</style>
