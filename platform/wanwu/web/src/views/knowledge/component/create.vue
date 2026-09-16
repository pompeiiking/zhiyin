<template>
    <div>
        <el-dialog
        top="10vh"
        :title="this.isEdit ? $t('knowledgeManage.editInfo') : $t('knowledgeManage.createKnowledge')"
        :close-on-click-modal="false"
        :visible.sync="dialogVisible"
        width="40%"
        :before-close="handleClose"
        >
        <el-form
            :model="ruleForm"
            ref="ruleForm"
            label-width="140px"
            class="demo-ruleForm"
            :rules="rules"
            @submit.native.prevent
        >
            <el-form-item
            :label="$t('knowledgeManage.knowledgeName')+'：'"
            prop="name"
            >
            <el-input
                v-model="ruleForm.name"
                :placeholder="$t('knowledgeManage.categoryNameRules')"
                maxlength="50"
                show-word-limit
            ></el-input>
            </el-form-item>
            <el-form-item
            :label="$t('knowledgeManage.desc')+':'"
            prop="description"
            >
            <el-input v-model="ruleForm.description" :placeholder="$t('common.input.inputDesc')"></el-input>
            </el-form-item>
            <el-form-item label="Embedding" prop="embeddingModelInfo.modelId">
                <el-select v-model="ruleForm.embeddingModelInfo.modelId" :placeholder="$t('common.select.placeholder')" value-key="modelId" :disabled="isEdit">
                    <el-option
                        v-for="item in EmbeddingOptions"
                        :key="item.modelId"
                        :label="item.displayName"
                        :value="item.modelId">
                    </el-option>
                </el-select>
            </el-form-item>
        </el-form>
        <span
            slot="footer"
            class="dialog-footer"
        >
            <el-button @click="handleClose()">{{$t('common.confirm.cancel')}}</el-button>
            <el-button
            type="primary"
            @click="submitForm('ruleForm')"
            >{{$t('common.confirm.confirm')}}</el-button>
        </span>
        </el-dialog>
    </div>
</template>
<script>
import {mapActions, mapGetters} from 'vuex'
import { createKnowledgeItem,editKnowledgeItem } from "@/api/knowledge";
export default {
    data(){
        var checkName = (rule, value, callback) => {
        const reg = /^[\u4E00-\u9FA5a-z0-9_-]+$/;
        if (!reg.test(value)) {
            callback(
            new Error(
                this.$t('knowledgeManage.inputErrorTips')
            )
            );
        } else {
            return callback();
        }
        };
        return{
            dialogVisible:false,
            ruleForm:{
                name:'',
                description:'',
                embeddingModelInfo:{
                    modelId:''
                }
            },
            EmbeddingOptions:[],
            rules: {
                name: [
                { required: true, message: this.$t('knowledgeManage.knowledgeNameRules'), trigger: "blur" },
                { validator: checkName, trigger: "blur" },
                ],
                description:[{ required: true, message: this.$t('knowledgeManage.inputDesc'), trigger: "blur" }],
                'embeddingModelInfo.modelId':[{ required: true, message:this.$t('common.select.placeholder'), trigger: "blur" }]
            },
            isEdit: false,
            knowledgeId:''
        }
    },
    watch: {
        embeddingList:{
        handler(val){
            if(val){
            this.EmbeddingOptions = val;
            }
          }
        }
    },
    computed: {
        ...mapGetters('app', ['embeddingList'])
    },
    created(){
      this.getEmbeddingList();
    },
    methods:{
        ...mapActions('app', ['getEmbeddingList']),
        handleClose(){
            this.dialogVisible = false;
            this.clearform()
        },
        clearform(){
            this.isEdit = false,
            this.knowledgeId = ''
            this.$refs.ruleForm.resetFields()
            this.$refs.ruleForm.clearValidate()
        },
        submitForm(formName){
            this.$refs[formName].validate((valid) =>{
                if(valid){
                    if(this.isEdit){
                      this.editKnowledge()
                    }else{
                      this.createKnowledge()
                    }
                    this.$parent.clearIptValue();
                }else{
                    return false;
                }
            })
        },
        createKnowledge(){
            createKnowledgeItem(this.ruleForm).then(res =>{
                if(res.code === 0){
                    this.$message.success('创建成功');
                    this.$emit('reloadData')
                    this.dialogVisible = false;
                }
            }).catch((error) =>{
                this.$message.error(error)
            })
        },
        editKnowledge(){
            const data = {
                ...this.ruleForm,
                'knowledgeId':this.knowledgeId
            }
            editKnowledgeItem(data).then(res =>{
                if(res.code === 0){
                    this.$message.success('编辑成功');
                    this.$emit('reloadData')
                    this.clearform();
                    this.dialogVisible = false;
                }
            }).catch((error) =>{
                this.$message.error(error)
            })
        },
        showDialog(row){
            this.dialogVisible = true;
            this.isEdit = Boolean(row)
            if (row) {
                this.knowledgeId = row.knowledgeId;
                this.ruleForm = {
                    name:row.name,
                    description:row.description,
                    embeddingModelInfo:{
                        modelId:row.embeddingModelInfo.modelId
                    }
                }
            }else{
                this.ruleForm = {
                    name:'',
                    description:'',
                    embeddingModelInfo:{
                        modelId:''
                    }
                }
            }
        }
    }
}
</script>