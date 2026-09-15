<template>
    <div>
        <el-dialog
            title="联网检索配置"
            :visible.sync="dialogVisible"
            width="50%"
            :before-close="handleClose">
            <el-form ref="form" :model="form" label-width="100px">
                <el-form-item 
                label="Url"
                prop="searchUrl"
                :rules="[{ required: true, message: '请输入Url', trigger: 'blur' }]"
                >
                    <el-input v-model="form.searchUrl"></el-input>
                </el-form-item>
                <el-form-item 
                prop="searchKey"
                label="Key"
                :rules="[{ required: true, message: '请输入Key', trigger: 'blur' }]"
                >
                    <el-input v-model="form.searchKey"></el-input>
                </el-form-item>
                <el-form-item 
                label="Rerank模型"
                prop="searchRerankId"
                :rules="[{ required: true, message: '请输入Url', trigger: 'blur' }]"
                >
                    <el-select
                        v-model="form.searchRerankId"
                        placeholder="请选择模型"
                        @visible-change="rerankVisible"
                        loading-text="模型加载中..."
                        class="cover-input-icon"
                        style="width:100%;"
                    >
                        <el-option
                        v-for="(item,index) in rerankOptions"
                        :key="item.modelId"
                        :label="item.displayName"
                        :value="item.modelId"
                        >
                        </el-option>
                    </el-select>
                </el-form-item>
            </el-form>
            <span slot="footer" class="dialog-footer">
                <el-button @click="dialogVisible = false">取 消</el-button>
                <el-button type="primary" @click="handleSubmit('form')">确定</el-button>
            </span>
        </el-dialog>
    </div>
</template>
<script>
import { getRerankList} from "@/api/modelAccess";
export default {
    props:{
        linkform:{
            type:Object,
            default:null
        }
    },
    data(){
        return{
            rerankOptions:[],
            dialogVisible:false,
            form:{
                searchUrl:'',
                searchKey:'',
                searchRerankId:''
            }
        }
    },
    methods:{
        rerankVisible(val){
            if(val){
                this.getRerankData();
            }
        },
         getRerankData(){
            getRerankList().then(res =>{
                if(res.code === 0){
                this.rerankOptions = res.data.list || []
                }
            })
         },
        handleClose(){
            this.dialogVisible = false
        },
        handleSubmit(formName){
            this.$refs[formName].validate((valid) => {
                if (valid) {
                    this.dialogVisible = false
                    this.$emit('setLinkSet',this.form)
                } else {
                    console.log('error submit!!');
                    return false;
                }
            });
            
        },
        showDialog(){
            this.dialogVisible = true
             if(this.linkform !== null){
                this.form.searchUrl = this.linkform.searchUrl;
                this.form.searchKey = this.linkform.searchKey;
                this.form.searchRerankId = this.linkform.searchRerankId;
            }
        }
    }
}
</script>