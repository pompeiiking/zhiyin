<template>
  <div ref="codeContainer" class="coder_editor" :class="{ read: readOnly }" />
</template>

<script>
// 引入JavaScript支持
// import * as monaco from "monaco-editor/esm/vs/editor/editor.api";
import * as monaco from "monaco-editor";

export default {
  model: {
    prop: "value",
    event: "change",
  },
  props: {
    value: {
      type: String,
      default: "",
    },
    language: {
      type: String,
      default: "",
    },
    readOnly: {
      type: Boolean,
      default() {
        return false;
      },
    },
    theme: {
      type: String,
      default: "",
    },
  },
  data() {
    return {
      monacoEditor: null, // 语言编辑器,
      monacoEditorConfig: {
        automaticLayout: true, // 自动布局
        theme: this.theme || "vs-dark", // 官方自带三种主题vs, hc-black, or vs-dark
        tabSize: 0, // tab 缩进长度
        autoIndent: "None", // 控制编辑器在用户键入、粘贴、移动或缩进行时是否应自动调整缩进
        minimap: {
          enabled: false, // 关闭小地图
        },
        readOnly: false,
        lineNumbers: "on", // 隐藏控制行号
        autoClosingBrackets: true,
        formatOnPaste: true, //是否粘贴自动格式化
      },
    };
  },
  watch: {
    value(val) {
      if (this.readOnly) {
        this.monacoEditor.updateOptions({ readOnly: false });
        setTimeout(() => {
          this.monacoEditor.updateOptions({ readOnly: true });
        }, 500);
      }
      this.monacoEditor.setValue(val);
      this.monacoEditor.trigger("", "editor.action.formatDocument");
      this.monacoEditor.setValue(this.monacoEditor.getValue());
    },
  },
  mounted() {
    this.monacoEditorConfig.readOnly = this.readOnly;
    this.init();
    // method setWorkerUrl
  },
  methods: {
    init() {
      if (this.$refs.codeContainer) {
        // 初始化编辑器，确保dom已经渲染
        const config = Object.assign({}, this.monacoEditorConfig, {
          language: this.language,
          value: this.value,
        });
        this.monacoEditor = monaco.editor.create(
          this.$refs.codeContainer,
          config
        );
        //this.monacoEditor.editor.remeasureFonts();
        // 编辑器绑定事件
        this.monacoEditorBindEvent();
      }
    },
    // 销毁编辑器
    monacoEditorDispose() {
      this.monacoEditor && this.monacoEditor.dispose();
    },
    // 获取编辑器的值
    getCodeVal() {
      const content = this.monacoEditor && this.monacoEditor.getValue();
      if (!content) {
        this.$message.error("不能为空, 提交失败");
      }
      return content;
    },
    // 编辑器事件
    monacoEditorBindEvent() {
      if (this.monacoEditor) {
        // 实时获取编辑器的值
        this.monacoEditor.onDidChangeModelContent(() => {
          this.$emit("handleChange", this.monacoEditor.getValue());
        });
      }
    },
    checkJsonCode(strJsonCode) {
      let res = "";
      try {
        for (let i = 0, j = 0, k = 0, ii, ele; i < strJsonCode.length; i++) {
          ele = strJsonCode.charAt(i);
          if (j % 2 === 0 && ele === "}") {
            // eslint-disable-next-line no-plusplus
            k--;
            for (ii = 0; ii < k; ii++) ele = `    ${ele}`;
            ele = `\n${ele}`;
          } else if (j % 2 === 0 && ele === "{") {
            ele += "\n";
            // eslint-disable-next-line no-plusplus
            k++;
            for (ii = 0; ii < k; ii++) ele += "    ";
          } else if (j % 2 === 0 && ele === ",") {
            ele += "\n";
            for (ii = 0; ii < k; ii++) ele += "    ";
            // eslint-disable-next-line no-plusplus
          } else if (ele === '"') j++;
          res += ele;
        }
      } catch (error) {
        res = strJsonCode;
      }
      return res;
    },
  },
};
</script>

<style lang="scss" scoped>
.coder_editor {
  position: relative;
  width: 100%;
  height: 100%;
  .read {
    &::after {
      content: "";
      position: absolute;
      top: 0;
      right: 0;
      bottom: 0;
      left: 68px;
      z-index: 1;
    }
  }
}
</style>

