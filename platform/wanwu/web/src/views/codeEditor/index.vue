<template>
  <div class="coder_editor_box">
    <div class="title">
      <span
        >Python

        <el-tooltip
          popper-class="coder_editor_tip"
          effect="dark"
          content="使用输入参数中的变量，构建函数功能。需要通过 return 一个对象来输出结果。可参考示例代码编写一个函数。（运行环境: Python3； 预置 Package：NumPy；）"
          placement="bottom"
        >
          <i class="el-icon-question"></i>
        </el-tooltip>
      </span>
      <i class="el-icon-d-arrow-right" @click="handleTake"></i>
    </div>
    <div class="code_editor_content">
      <codeEditor
        :value="codeValue"
        :language="'python'"
        :readOnly="false"
        @handleChange="codeValuehandleChange"
      ></codeEditor>
    </div>
    <div
      class="footer"
      v-loading="runloading"
      element-loading-spinner="el-icon-loading"
      element-loading-background="rgba(0, 0, 0, 0.8)"
    >
      <div class="editor_input">
        <div class="editor_input_title">
          <span>输入测试</span>
          <div class="input_box">
            <el-button @click="handleFillData">
              <i class="el-icon-s-order"></i>
              填充数据
            </el-button>
            <el-button
              @click="handleRun"
              :disabled="!newInputValue"
              :class="{ input_stop: !run }"
            >
              <i
                :class="{
                  'el-icon-video-play': run,
                  'el-icon-video-pause': !run,
                }"
              ></i>
              {{ run ? "运行" : "停止" }}
            </el-button>
          </div>
        </div>
        <codeEditor
          class="footer_codeEditor"
          :value="inputValue"
          @handleChange="inputValuehandleChange"
          :language="'json'"
          :readOnly="false"
        ></codeEditor>
      </div>
      <div class="editor_out" :class="{ noData: !outValue && !loading }">
        <div class="editor_out_title">
          <span>输出结果</span>
          <div class="input_box">
            <el-button @click="handleCopy" :disabled="!outValue">
              <i class="el-icon-document-copy"></i>
              复制
            </el-button>
            <el-button :disabled="!outValue" @click="handleAnalyze">
              <i class="el-icon-refresh"></i>
              解析到输出参数
            </el-button>
          </div>
        </div>
        <codeEditor
          v-loading="loading"
          element-loading-text="运行中"
          element-loading-spinner="el-icon-loading"
          element-loading-background="rgba(0, 0, 0, 0)"
          class="footer_codeEditor"
          :value="outValue"
          :language="'json'"
          :readOnly="true"
        ></codeEditor>
      </div>
    </div>
  </div>
</template>

<script>
import { runPythonNode } from "@/api/workflow";
import { Base64 } from "js-base64";
import codeEditor from "./components/codeEditor.vue";

export default {
  props: ["node"],
  data() {
    return {
      codeValue: "",
      newCodeValue: "",
      /*# 定义一个 main 函数，用户只能在main函数里做代码开发。
        # 其中，固定传入 params 参数（字典格式），它包含了节点配置的所有输入变量。
        # 其中，固定返回 output_params 参数（字典格式），它包含了节点配置的所有输出变量。
        # 运行环境 Python3.

        # main 函数，固定传入 params 参数
        def main(params):
            # 用户自定义部分......

            # 固定返回 output_params 参数
            output_params = {
              # 用户自定义部分......
            }
            return output_params
        */
      inputValue: "", //'{"pois":[{"adcode":"110101","address":"雍和宫大街28号(雍和宫地铁站F东南口步行250米)","adname":"东城区","citycode":"010","cityname":"北京市","distance":"","id":"B000A7BGMG","location":"116.417296,39.947239","name":"雍和宫","parent":"","pcode":"110000","pname":"北京市","type":"风景名胜;风景名胜;风景名胜","typecode":"110200"}]}', // 输入value
      newInputValue: "",
      outValue: "", // 输出value
      run: true, // true：为启动；false：已启动
      loading: false, // 输出部分loading
      runloading: false,
    };
  },
  /*watch: {
      newCodeValue: {
          handler:function (newVal, oldVal) {
          },
          deep:true
      },
  },*/
  methods: {
    setCode(settings) {
      this.codeValue = settings.code;
      console.log(this.codeValue);
    },
    // 填充数据事件
    handleFillData() {
      this.inputValue = `{
        "city": "Beijing",
        "days": 3,
        "weather": "snow"
      }`;
      this.newInputValue = `{
        "city": "Beijing",
        "days": 3,
        "weather": "snow"
      }`;
    },
    // 实时获取编辑器的值
    codeValuehandleChange(val) {
      this.newCodeValue = val;
      this.$emit("refreshCodeValue", val);
    },
    inputValuehandleChange(val) {
      this.newInputValue = val;
    },
    // 运行
    async handleRun() {
      this.outValue = "";
      let params = {
        data: JSON.parse(this.newInputValue),
        nodeSchema: {
          nodes: [
            {
              id: this.node.data.id,
              type: this.node.data.type,
              name: this.node.data.name,
              data: {
                settings: {
                  code: Base64.encode(this.newCodeValue),
                  language: "Python",
                },
                inputs: [],
                // 在单个节点调试运行时，其output出参要求为空数组，与整个workflow画布调试运行时的场景，作区分
                outputs: [], //this.node.data.data
              },
            },
          ],
        },
      };
      this.runloading = true;
      try {
        let res = await runPythonNode(params);
        if (res.code === 0) {
          this.outValue = JSON.stringify(res.data);
        }
      } finally {
        this.runloading = false;
      }
    },
    //  let res = { "key":"雍和宫"}
    // 输出复制
    handleCopy() {
      if (!this.outValue) return;
      var textarea = document.createElement("textarea");
      textarea.style.position = "fixed";
      textarea.style.opacity = 0;
      textarea.value = this.outValue;
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand("copy");
      document.body.removeChild(textarea);
      this.$message.success("已复制");
    },
    // 右上角收回
    handleTake() {
      this.$emit("handleTake");
    },
    // 解析到输出参数事件
    handleAnalyze() {
      let resObj = JSON.parse(this.outValue);
      let arr = [];
      for (var key in resObj) {
        arr.push({
          desc: "",
          list_schema: null,
          name: key,
          object_schema: null,
          required: false,
          type: "string",
          value: {
            content: "",
            type: "generated",
          },
        });
      }
      this.$emit("setOutputsData", arr);
    },
  },
  components: {
    codeEditor,
  },
};
</script>

<style lang="scss" scoped>
.coder_editor_tip {
  width: 300px;
}
.coder_editor_box {
  float: right;
  width: 75%;
  height: 100%;
  background: #fff;
  font-size: 12px;
  .title {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 10px 16px;
    background: #2d2e2e;
    color: #fff;
    font-weight: bold;

    .el-icon-question {
      font-weight: bold;

      // color: #2d2e2e;
      &:hover {
        cursor: pointer;
      }
    }
    .el-icon-d-arrow-right {
      &:hover {
        cursor: pointer;
      }
    }
  }
  .el-loading-text {
    color: #999;
  }
  .el-loading-spinner i {
    color: #999;
  }
  .code_editor_content {
    width: 100%;
    height: calc(100% - 336px);
  }
  .footer {
    display: flex;
    justify-content: space-around;
    height: 300px;
    .editor_input {
      width: 50%;
    }
    .editor_out {
      position: relative;
      width: 50%;
      height: 100%;
      &.noData {
        &::after {
          content: "请在左侧填写输入数据，运行后查看输出结果";
          position: absolute;
          top: 50%;
          left: 50%;
          transform: translate(-50%, -50%);
          color: #999;
        }
      }
      // &::before {
      //   content: "";
      //   position: absolute;
      //   display: block;
      //   width: 100%;
      //   height: calc(100% - 32.5px);
      //   bottom: 0;
      //   left: 0;
      //   right: 0;
      //   z-index: 1;
      // }
    }
    .footer_codeEditor {
      height: calc(100% - 40.5px);
    }
    .el-button {
      font-weight: bold;
      background: transparent !important;
      border: 0 !important;
      border-radius: 0 !important;
      padding: 5px !important;
      margin-left: 0 !important;
    }
    .editor_input_title {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 8px 16px;
      background: #2d2e2e;

      span {
        color: #fff;
        font-size: 12px;
      }

      .input_box {
        .el-button {
          // font-weight: bold;
          // background: transparent !important;
          // border: 0 !important;
          // border-radius: 0 !important;
          &:first-child {
            span {
              color: #b8babf !important;
            }
            &:hover {
              cursor: pointer;
              background: #ffffff1a !important;
              border-radius: 0 !important;
            }
          }
          &:last-child {
            span {
              color: #30d158;
            }

            &:hover {
              cursor: pointer;
              background: #ffffff1a !important;
              border-radius: 0 !important;
              // &:hover {
              //   cursor: pointer;
              //   background: #ffffff;
              // }
            }
            i {
              font-weight: bold;
            }
          }
        }
        .input_stop {
          span {
            color: #e60001 !important;
          }
        }
        .is-disabled {
          &:hover {
            cursor: no-drop !important;
          }
          &:last-child {
            span {
              color: #888 !important;
              &:hover {
                cursor: no-drop;
              }
            }
          }
        }
      }
    }
    .editor_out_title {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 8px 16px;
      background: #2d2e2e;

      span {
        color: #fff;
        font-size: 12px;
      }

      .input_box {
        .el-button {
          font-weight: bold;
          &:first-child {
            span {
              color: #b8babf !important;
            }
            &:hover {
              cursor: pointer;
              background: #ffffff1a !important;
            }
          }
          &:last-child {
            span {
              color: #75d6ff !important;
            }

            &:hover {
              &:hover {
                cursor: pointer;
                background: #ffffff1a !important;
              }
            }
            i {
              font-weight: bold;
            }
          }
        }
        .is-disabled {
          &:hover {
            cursor: no-drop !important;
          }
          &:first-child,
          &:last-child {
            span {
              color: #888 !important;
              &:hover {
                cursor: no-drop;
              }
            }
          }
        }
      }
    }
    font-weight: bold;
  }
}
</style>

