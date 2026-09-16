<template>
  <div class="model_box">

    <!--输入-->
    <div class="node-params">
      <div class="params-type">
        <i class="el-icon-caret-bottom"></i>
        <span class="params-type-span">输入</span>
      </div>
      <!--form-->
      <div class="params-form">
        <div class="form-item">
          <div class="item">参数名</div>
          <div class="item">类型</div>
          <div class="item last-item">值</div>
        </div>
        <div
          class="form-item"
          v-for="(n, i) in nodeData.data.inputs"
          :key="`${i}ipt`"
        >
          <el-input class="item" size="mini" v-text="n.name"></el-input>
          <el-select
            class="item"
            size="mini"
            popper-class="workflow-select"
            v-model="n.value.type"
            @change="(val) => selectTypeChange(val, i, n)"
          >
            <el-option value="generated" label="String"></el-option>
            <el-option value="ref" label="引用"></el-option>
          </el-select>
          <!--非引用-->
          <el-input
            class="item last-item"
            size="mini"
            style="width: 190px"
            :placeholder="n.desc"
            v-if="n.value.type == 'generated'"
            v-model="n.value.content"
          ></el-input>

           <el-popover placement="bottom" width="260" trigger="click">
            <div>
              <div
                class="popover-select-item"
                v-for="(m, j) in preAllNode"
                :key="`${j}pn`"
              >
                <p class="node-name">
                  <i class="el-icon-caret-bottom"></i>{{ m.name }}
                </p>
                <div
                  class="node-content"
                  v-for="(p, l) in m.data.data.outputs"
                  :key="`${l}opt`"
                  @click="refValueClick(n, i, m, p, l)"
                >
                  <span class="name">{{ p.name }}</span>
                  <span class="type">{{ p.type }}</span>
                </div>
              </div>
            </div>
            <div
              slot="reference"
              v-show="n.value.type === 'ref'"
              class="item last-item popover-select"
            >
              {{ n.newRefContent }}
            </div>
          </el-popover>
          
        </div>
      </div>
      <p v-if="nodeData.validate && JSON.parse(nodeData.validate).inputValidate === false" class="workflow-errormsg">{{JSON.parse(nodeData.validate).message}}</p>
    </div>



    <!--输出-->
    <div class="node-params">
      <div class="params-type">
        <i class="el-icon-caret-bottom"></i>
        <span class="params-type-span">输出</span>
        <!-- <i class="el-icon-plus add-icon" @click="preAddOutputParams"></i>-->
      </div>
      <div class="params-form">
        <div class="form-item">
          <div class="item">参数名</div>
          <div class="item">类型</div>
        </div>
        <div
          class="form-item"
          v-for="(n, i) in nodeData.data.outputs"
          :key="`${i}opts`"
        >
          <el-input
            class="item"
            size="mini"
            v-model="n.name"
            disabled
          ></el-input>
          <el-select class="item" size="mini" v-model="n.type" disabled>
            <el-option value="string" label="String"></el-option>
          </el-select>
         
        </div>
        <el-collapse v-model="activeName">
          <el-collapse-item title="result展开说明" name="1">
                <codeEditor
                  style="height: 150px;overflow: hidden"
                  :value="JSON.stringify(nodeData.data.outputs[0].value.content)"
                  :language="'json'"
                  :readOnly="true"
                  :theme="'vs'"
              ></codeEditor>
          </el-collapse-item>
        </el-collapse>
       
      </div>
      
      <p v-if="nodeData.validate && JSON.parse(nodeData.validate).outputValidate === false" class="workflow-errormsg">{{JSON.parse(nodeData.validate).message}}</p>
    </div>
  </div>
</template>

<script>
import { mapState } from "vuex";
import nodeMethod from "@/views/workflow/mixins/nodeMethod";
import codeEditor from "@/views/ArrayEditor/index.vue";

export default {
  components: {codeEditor},
  props: ["graph", "node"],
  data() {
    return {
      placeholder:"",
      settings: {},
      nodeData: {},
      preNode: {},
      preNodeOutputs: [],
      preAllNode: [],
      models:[],
      activeName:1,
    };
  },
  computed: {
    ...mapState({
      nodeIdMap: (state) => state.workflow.nodeIdMap,
    }),
  },
  mixins: [nodeMethod],
  created() {
    //this.nodeData = this.node.data;
  },
  methods: {
    selectTypeChange(val, i, n) {
      switch (val) {
        case "ref":
          this.preAllNode = [];
          this.getPreNode(this.nodeData.id);
          break;
        case "generated":
          let newItem = {
            desc: n.desc||"",
            extra: {
              location: "body",
            },
            list_schema: null,
            name: this.nodeData.data.inputs[i].name,
            object_schema: null,
            required: false,
            type: "string",
            value: {
              content: "",
              type: "generated",
            },
            newRefContent: "",
          };
          this.$nextTick(() => {
            this.$set(this.nodeData.data.inputs, i, newItem);
          });

          break;
      }
    },
  },
};
</script>

<style lang="scss" scoped>
.item{
  /deep/.el-popover__reference-wrapper{
    width: 100%;
  }
  /deep/.popover-select{
    width: 100%;
  }
}

/deep/.el-collapse .el-collapse-item__header{
  height: 30px !important;
  line-height:  30px !important;
  position: relative;
  .el-icon-arrow-right{
    top: 9px !important;
  }
}
</style>
