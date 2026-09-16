<template>
    <el-drawer
    title="schema"
    :visible.sync="dialogVisible"
    size="45%"
    :close-on-click-modal="false"
    :before-close="handleClose">
        <span class="schema-copy">{{$t('list.clickCopy')}}</span>
        <div ref="codeContainer" class="schema-textarea"  />
    </el-drawer>
</template>

<script>

import isBase64 from "is-base64";
import { Base64 } from "js-base64";
import * as monaco from "monaco-editor";
export default {
  data(){
    return{
      dialogVisible:false,
      code:"",
      monacoEditor: null, // 语言编辑器,
      monacoEditorConfig: {
        automaticLayout: true, // 自动布局
        theme: this.theme || "vs-dark", // 官方自带三种主题vs, hc-black, or vs-dark
        tabSize: 0, // tab 缩进长度
        autoIndent: "None", // 控制编辑器在用户键入、粘贴、移动或缩进行时是否应自动调整缩进
        minimap: {
          enabled: false, // 关闭小地图
        },
        readOnly: true,
        lineNumbers: "on", // 隐藏控制行号
        autoClosingBrackets: true,
        language:'json',
        formatOnPaste: true, //是否粘贴自动格式化
      },
    }
  },
  created(){

  },
  methods: {
    openDialog(data){

        let result = JSON.parse(Base64.decode(data))

       this.code = this.checkJsonCode(JSON.stringify(result))
       this.dialogVisible = true
       this.$nextTick(()=>{
            this.init()
             let copys = document.getElementsByClassName("schema-copy");
            for (var i = 0; i < copys.length; i++) {
                copys[i].addEventListener("click", (e) => {
                    this.$copy(this.code);
                    e.target.innerText = this.$t('list.copySuccess');
                    setTimeout(() => {
                        e.target.innerText = this.$t('list.clickCopy');
                    }, 1000);
                });
            }
       })
    },
    handleClose(){
        this.dialogVisible = false
        this.monacoEditor.dispose()
    },
    checkJsonCode(strJsonCode) {
        let res = '';
        try {
            for (let i = 0, j = 0, k = 0, ii, ele; i < strJsonCode.length; i++) {
            ele = strJsonCode.charAt(i);
            if (j % 2 === 0 && ele === '}') {
                // eslint-disable-next-line no-plusplus
                k--;
                for (ii = 0; ii < k; ii++) ele = `    ${ele}`;
                ele = `\n${ele}`;
            } else if (j % 2 === 0 && ele === '{') {
                ele += '\n';
                // eslint-disable-next-line no-plusplus
                k++;
                for (ii = 0; ii < k; ii++) ele += '    ';
            } else if (j % 2 === 0 && ele === ',') {
                ele += '\n';
                for (ii = 0; ii < k; ii++) ele += '    ';
                // eslint-disable-next-line no-plusplus
            } else if (ele === '"') j++;
            res += ele;
            }
        } catch (error) {
            res = strJsonCode;
        }
        return res;
    },
    init() {
      if (this.$refs.codeContainer) {
        // 初始化编辑器，确保dom已经渲染
        const config = Object.assign({}, this.monacoEditorConfig, {
          value: this.code,
        });
        this.monacoEditor = monaco.editor.create(
          this.$refs.codeContainer,
          config
        );
      }
    },
  }
}
</script>

<style lang="scss" scoped>
.schema-textarea{
    height: 90%;
    width: 90%;
    margin: 0 auto;
}
.schema-copy{
    position:absolute;
    left: 100px;
    top: 23px;
    cursor:pointer;
}
</style>
