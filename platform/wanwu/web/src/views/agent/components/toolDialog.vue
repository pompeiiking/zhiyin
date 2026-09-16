<template>
    <div>
        <el-dialog
            title="新增变量"
            :visible.sync="dialogVisible"
            width="35%"
            :before-close="handleClose">
            <div class="tool-typ">
                <div v-for="(item,index) in toolList" :key="index" @click="clickTool(item,index)" :class="{'active':toolIndex === index}">
                    {{item.name}}
                </div>
            </div>
            <span slot="footer" class="dialog-footer">
                <el-button type="primary" @click="submit">确 定</el-button>
            </span>
        </el-dialog>
    </div>
</template>
<script>
export default {
    data(){
        return {
            dialogVisible:false,
            toolIndex:-1,
            activeValue:'',
            toolList:[
                {
                    value:'action',
                    name:'action API'
                },
                {
                    value:'workflow',
                    name:'工作流'
                }
            ]
        }
    },
    methods:{
        showDialog(){
            this.dialogVisible = true;
        },
        handleClose(){
            this.toolIndex = -1;
            this.activeValue = '';
            this.dialogVisible = false;
        },
        clickTool(item,i){
            this.toolIndex = i;
            this.activeValue = item.value;
        },
        submit(){
            this.$emit('selectTool',this.activeValue);
            this.dialogVisible = false;
        }
    }
}
</script>
<style lang="scss" scoped>
.tool-typ{
    display:flex;
    justify-content:space-around;
    div{
        width:200px;
        text-align: center;
        padding:15px 40px;
        border-radius:6px;
        border:1px solid #ddd;
        cursor: pointer;
    }
}
.active{
    border:1px solid #384BF7 !important;
    color: #384BF7;
}
</style>