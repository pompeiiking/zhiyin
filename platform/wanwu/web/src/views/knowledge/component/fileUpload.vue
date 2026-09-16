<template>
  <div class="page-wrapper full-content">
    <div class="page-title">
      <span class="el-icon-arrow-left back" @click="goBack"></span>
      新增文件
    </div>
    <div class="table-box">
      <div class="fileUpload">
        <el-steps
          :active="active"
          class="fileStep"
          align-center
        >
          <el-step title="文件上传"></el-step>
          <el-step title="参数设置"></el-step>
        </el-steps>
        <div v-if="active === 1">
          <div class="fileBtn">
            <el-radio-group v-model="fileType" @change="fileTypeChage">
                <el-radio-button label="file">从文件上传</el-radio-button>
                <el-radio-button label="fileUrl">url文件上传</el-radio-button>
                <el-radio-button label="url">url单条上传</el-radio-button>
            </el-radio-group>
        </div>
          <div element-loading-background="rgba(255, 255, 255, 0.5)" v-if="fileType !== 'url'">
            <div class="dialog-body">
              <el-upload
                :class="['upload-box']"
                drag
                action=""
                :show-file-list="false"
                :auto-upload="false"
                :limit="5"
                multiple
                accept=".pdf,.docx,.doc,.txt,.xlsx,.xls,.zip,.tar.gz,.csv,.pptx,.html"
                :file-list="fileList"
                :on-change="uploadOnChange"
              >
              <div>
                <div>
                    <img :src="require('@/assets/imgs/uploadImg.png')" class="upload-img" />
                    <p class="click-text">将文件拖到此处，或<span class="clickUpload">点击上传</span></p>
                </div>
                <div class="tips">
                  <p v-if="fileType === 'file'"><span class="red">*</span>您可单独或者批量上传以下格式的文档：pdf/docx/pptx 文件最大为200MB，xlsx/csv/txt/html文件最大为20MB。zip格式内的文档需符合各自文件格式上传大小限制</p>
                  <p v-if="fileType === 'file'"><span class="red">*</span>非压缩包文件，一次可传5个文件，如文件页数多，文档解析时间较长，平均3秒/页，请您耐心等待</p>
                  <p v-if="fileType === 'fileUrl'"><span class="red">*</span>批量上传支持.xlsx格式，仅可上传1个。文档最多可添加100条url，文件不超过15mb <a class="template_downLoad" href="#" @click.prevent.stop="downloadTemplate">模版下载</a></p>
                  <p v-if="fileType === 'fileUrl'"><span class="red">*</span>当前内容不自动更新</p>
                </div>
              </div>
              </el-upload>
            </div>
          </div>
          <div class="el-upload-url" v-else>
            <div class="upload-url">
              <urlAnalysis 
              :categoryId="knowledgeId" 
              ref="urlUpload"
              @handleLoading="handleLoading"
              @handleSetData="handleSetData"
              />
            </div>
          </div>
        </div>
        <div v-else class="params_form">
          <el-form
            :model="ruleForm"
            ref="ruleForm"
            label-width="140px"
            class="demo-ruleForm"
            @submit.native.prevent
          >
            <el-form-item :label="$t('knowledgeManage.chunkTypeSet')+'：'">
              <el-radio-group v-model="ruleForm.docSegment.segmentType">
                <el-radio label="0">自动分段</el-radio>
                <el-radio label="1">自定义分段</el-radio>
              </el-radio-group>
            </el-form-item>
            <el-form-item
              v-if="ruleForm.docSegment.segmentType == '1'"
              :label="$t('knowledgeManage.punctuationMark')+'：'"
              prop="docSegment.splitter"
              :rules="ruleForm.docSegment.segmentType === '1' 
              ? [{ required: true, message: $t('knowledgeManage.markTips'), trigger: 'blur' }] 
              : []"
            >
              <el-select
                v-model="ruleForm.docSegment.splitter"
                :placeholder="$t('knowledgeManage.please')"
                class="setItem"
                multiple
                clearable
                collapse-tags
              >
                <el-option
                  v-for="item in splitOptions"
                  :key="item.value"
                  :label="item.label"
                  :value="item.value"
                >
                </el-option>
              </el-select>
              <div style="color: #384BF7;">
                {{$t('knowledgeManage.splitOptionsTips')}}
              </div>
            </el-form-item>
            <el-form-item
              v-if="ruleForm.docSegment.segmentType == '1'"
              :label="$t('knowledgeManage.splitMax')+'：'"
              prop="docSegment.maxSplitter"
              :rules="[{ required: true, message: $t('knowledgeManage.splitMax'),trigger:'blur'}]"
            >
              <div :class="[['0','1','3','4'].includes(ruleForm.docSegment.segmentType)?'':'set']">
                <el-input-number
                    v-model="ruleForm.docSegment.maxSplitter"
                    :min="200"
                    :max="3000"
                    :placeholder="$t('knowledgeManage.splitMax')"
                ></el-input-number>
                <p class="tips">
                    {{$t('knowledgeManage.splitMaxTips')}}
                </p>
              </div>
            </el-form-item>
            <el-form-item
              v-if="ruleForm.docSegment.segmentType == '1'"
              :label="$t('knowledgeManage.overLapNum')+'：'"
              prop="docSegment.overlap"
              :rules="[
                        { required: true, message:$t('knowledgeManage.overLapNumTips'),trigger:'blur'}
                    ]"
            >
              <div class="elSliderItem">
                <el-slider
                  :min="0"
                  :max="0.25"
                  :step="0.01"
                  style="width:70%;margin-left:15px;"
                  v-model="ruleForm.docSegment.overlap"
                  show-input
                >
                </el-slider>
              </div>
            </el-form-item>
            <el-form-item
              label="解析方式："
              prop="docAnalyzer"
            >
            <el-checkbox-group v-model="ruleForm.docAnalyzer">
                <el-checkbox label="text" disabled>文本提取</el-checkbox>
                <!-- <el-checkbox label="ocr">启用ocr解析</el-checkbox> -->
            </el-checkbox-group>
            </el-form-item>
          </el-form>
        </div>
        <!-- 上传文件的列表 -->
        <div class="file-list" v-if="fileList.length > 0 && active === 1 ">
            <transition name="el-zoom-in-top">
            <ul class="document_lise">
              <li
                v-for="(file, index) in fileList"
                :key="index"
                class="document_lise_item"
              >
                <div style="padding:8px 0;" class="lise_item_box">
                  <span class="size">
                    <img :src="require('@/assets/imgs/fileicon.png')" />
                    {{ file.name }}
                    <span class="file-size">
                    {{ filterSize(file.size) }}
                    </span>
                  </span>
                  <span class="handleBtn">
                    <span>
                      <span v-if="file.percentage === 100">
                        <i class="el-icon-check check success" v-if="file.progressStatus === 'success'"></i>
                        <i class="el-icon-close close fail" v-else></i>
                      </span>
                      <i class="el-icon-loading" v-else-if="file.percentage !== 100 && index === fileIndex"></i>
                    </span>
                    <span style="margin-left:30px;">
                      <i class="el-icon-error error" @click="handleRemove(file,index)"></i>
                    </span>
                  </span>
                </div>
              </li>
            </ul>
          </transition>
        </div>
        <div class="next">
          <el-button type="primary" size="mini" @click="preStep" v-if="active === 2">上一步</el-button>
          <el-button type="primary" size="mini" @click="nextStep" v-if="active === 1" :loading="urlLoading">下一步</el-button>
          <el-button type="primary" size="mini" @click="submitInfo" v-if="active === 2">确 定</el-button>
        </div>
      </div>
    </div>
  </div>
</template>
<script>
import urlAnalysis from './urlAnalysis.vue';
import uploadChunk from "@/mixins/uploadChunk";
import {docImport} from '@/api/knowledge'
import { delfile } from "@/api/chunkFile";
import { FlagManager } from '@antv/x6/lib/view/flag';
export default {
  components:{urlAnalysis},
  mixins: [uploadChunk],
  data() {
    return {
      urlValidate: false,
      active: 1,
      fileType:'file',
      knowledgeId:this.$route.query.id,
      knowledgeName:this.$route.query.name,
      fileList:[],
      fileUrl:'',
      docInfoList:[],
      ruleForm:{
        docAnalyzer:['text'],
        docSegment:{
          segmentType:'0',
          splitter:["！","。","？","?","!",".","......"],
          maxSplitter:'',
          overlap:0
        },
        docInfoList:[],
        docImportType:0,
        knowledgeId:this.$route.query.id
      },
      splitOptions: [
        {
          label: this.$t('knowledgeManage.zh_exclamationMark'),
          value: "！",
        },
        {
          label: this.$t('knowledgeManage.zh_period'),
          value: "。",
        },
        {
          label: this.$t('knowledgeManage.zh_questionMark'),
          value: "？",
        },
        {
          label: this.$t('knowledgeManage.en_questionMark'),
          value: "?",
        },
        {
          label: this.$t('knowledgeManage.en_exclamationMark'),
          value: "!",
        },
        {
          label: this.$t('knowledgeManage.eh_period'),
          value: ".",
        },
        {
          label: this.$t('knowledgeManage.ellipsis'),
          value: "......",
        }
      ],
      urlLoading:false
    };
  },
  methods:{
  goBack(){
    this.$router.go(-1);
  },
  handleSetData(data){
    this.docInfoList = [];
    data.map(item =>{
      this.docInfoList.push({
        docName:item.fileName,
        docSize:item.fileSize,
        docUrl:item.url,
        docType:'url'
      })
    })
  },
  async downloadTemplate(){
    const url = '/user/api/v1/static/docs/url_import_template.xlsx';
    const fileName = 'url_import_template.xlsx';
    try {
      const response = await fetch(url);
      if (!response.ok) throw new Error('文件不存在或服务器错误');
      
      const blob = await response.blob();
      const blobUrl = URL.createObjectURL(blob);
      
      const a = document.createElement('a');
      a.href = blobUrl;
      a.download = fileName;
      a.click();
      
      URL.revokeObjectURL(blobUrl); // 释放内存
    } catch (error) {
      alert('文件下载失败，请稍后重试！');
    }
  },
   handleLoading(val, result) {
      this.urlLoading = val;
      if (result === "success") {
        this.reset();
      }
    },
    // handleValidate() {
    //   this.$refs["uplodForm"].validate((valid) => {
    //     this.urlValidate = valid; // true/false
    //   });
    // },
    // handleSetDisabled(val) {
    //   this.urlSave = val;
    // },
    reset() {
      if (this.source.length > 0) {
        for (let i = 0; i < this.source.length; i++) {
          this.source[i].cancel();
        }
      }
      let ids = []
      if(this.fileList.length > 0){
        this.fileList.map(item => {
          if(item.id){
            if(item.id.includes(',')){//rag一体机没有此逻辑
              const list = item.id.split(',')
              list.map(item =>{
                ids.push(item)
              })
            }else{
              ids.push(item.id)
            }
          }
        })
        if(ids.length > 0){
          this.deleteData({id:ids})//取消时删除文件
        }
      }
      this.$refs["uplodForm"].resetFields();
      this.uplodForm.knowValue = null;
      this.fileList = [];
      this.resultDisabled = true;
      this.source = [];
      this.fileUuid = '';
      this.$emit("handleSetOpen", {isShow:false,knowValue:null});
      this.uploading = false;
      // this.$refs.urlUpload &&
      // this.$refs.urlUpload.resetForm("dynamicValidateForm");
    },
    // 删除已上传文件
    handleRemove(item,index) {
      this.delfile({fileList:[this.resList[index]['name']],isExpired:true});
      this.fileList = this.fileList.filter((files) => files.name !== item.name);
      if(this.fileList.length === 0){
        this.file = null
      }else{
        this.fileIndex--
      }
      if(this.docInfoList.length > 0){
        this.docInfoList.splice(1,index)
      }
    },
    delfile(data){
      delfile(data).then(res =>{
        if(res.code === 0){
          this.$message.success('删除成功')
        }
      })
    },
    filterSize(size) {
      if (!size) return "";
      var num = 1024.0; //byte
      if (size < num) return size + "B";
      if (size < Math.pow(num, 2)) return (size / num).toFixed(2) + "KB"; //kb
      if (size < Math.pow(num, 3))
        return (size / Math.pow(num, 2)).toFixed(2) + "MB"; //M
      if (size < Math.pow(num, 4))
        return (size / Math.pow(num, 3)).toFixed(2) + "G"; //G
      return (size / Math.pow(num, 4)).toFixed(2) + "T"; //T
    },
    fileTypeChage(){
      this.docInfoList = [];
      this.fileList = []
    },
    submitInfo(){
      const { segmentType, splitter } = this.ruleForm.docSegment;
      if (segmentType === '1' && splitter.length === 0) {
          this.$refs.ruleForm.validate();
          return false;
      }
      this.$refs.ruleForm.clearValidate(['docSegment.splitter']);

      if(this.fileType ==='file'){
        this.ruleForm.docImportType  = 0;
      }else if(this.fileType ==='fileUrl'){
        this.ruleForm.docImportType  = 2;
      }else{
        this.ruleForm.docImportType  = 1
      }
      this.ruleForm.docInfoList = this.docInfoList;
      let data = null
      if(this.ruleForm.docSegment.segmentType == '0'){
        data = this.ruleForm;
        delete data.docSegment.splitter;
        delete data.docSegment.maxSplitter;
        delete data.docSegment.overlap;
      }else{
        data = this.ruleForm
      }
      docImport(data).then(res =>{
          if(res.code === 0){
            this.$router.push({path:`/knowledge/doclist/${this.knowledgeId}?name=${this.knowledgeName}`})
          }
        })
    },
    uploadOnChange(file, fileList){
      if (!fileList.length) return;
      this.fileList = fileList;
      if(
        this.verifyEmpty(file) !== false &&
        this.verifyFormat(file) !== false &&
        this.verifyRepeat(file) !== false
      ){
        setTimeout(() => {
          this.fileList.map((file, index) => {
            if(file.progressStatus && file.progressStatus !=='success'){
              this.$set(file, "progressStatus", "exception");
              this.$set(file, "showRetry", "false");
              this.$set(file, "showResume", "false");
              this.$set(file, "showRemerge", "false");
              if (file.size > this.maxSizeBytes) {
                this.$set(file, "fileType", "maxFile");
              } else {
                this.$set(file, "fileType", "minFile");
              }
            }
          });
        },10)
        //开始切片上传(如果没有文件正在上传)
        if(this.file === null){
          this.startUpload();
        }else{//如果上传当中有新的文件加入
          if(this.file.progressStatus === 'success'){
            this.startUpload(this.fileIndex)
          }
        }
      }
    },
    refreshFile(index){//重新上传文件
      this.fileList[index]['showRetry'] = 'false';
      this.fileList[index]['percentage'] = 0;
      this.startUpload(index)
    },
    resumeFile(index){//续传文件
      this.fileList[index]['showResume'] = 'false';
      this.nextChunkIndex = this.uploadedChunks;
      this.processNextChunk();
    },
    remergeFile(index){//重新上传
      this.mergeChunks()
    },
    uploadFile(fileName,oldName){
      let type = oldName.split(".").pop()
      const docType = type === 'gz' ? '.tar.gz' : '.'+ oldName.split(".").pop()
      this.docInfoList.push({
        docId:fileName,
        docName:oldName,
        docType
      })
      this.fileIndex++;
      if (this.fileIndex < this.fileList.length) {
        this.startUpload(this.fileIndex);
      }
    },
    //  验证文件为空
    verifyEmpty(file) {
      const isLt1GB = file.size / 1024 / 1024 / 1024 < 1;
      if (file.size <= 0) {
        setTimeout(() => {
          this.$message.warning(file.name + this.$t('knowledgeManage.filterFile'));
          this.fileList = this.fileList.filter(
            (files) => files.name !== file.name
          );
        }, 50);
        return false
      }
      return true
    },
    //  验证文件格式
    verifyFormat(file) {
      const nameType = ['pdf','docx','pptx','zip','tar.gz','xlsx','csv','txt','html']
      const fileName = file.name
      const isSupportedFormat = nameType.some(ext => fileName.endsWith(`.${ext}`));
      if (!isSupportedFormat) {
        setTimeout(() => {
          this.$message.warning(file.name + this.$t('knowledgeManage.fileTypeError'));
          this.fileList = this.fileList.filter(
            (files) => files.name !== file.name
          );
        }, 50);
        return false
      }else{
        const fileType = file.name.split(".").pop()
        const limit200 = ['pdf','docx','pptx','zip','tar.gz']
        const limit20 = ['xlsx','csv','txt','html']
        let isLimit200 = file.size / 1024 / 1024 < 200;
        let isLimit20 = file.size / 1024 / 1024 < 20;
        let num = 0;
        if(limit200.includes(fileType)){
            num = 200;
            if(!isLimit200){
              setTimeout(() => {
                this.$message.error(this.$t('knowledgeManage.limitSize')+`${num}MB!`);
                this.fileList = this.fileList.filter(
                  (files) => files.name !== file.name
                );
              }, 50);
              return false
          }
          return true
        }else if(limit20.includes(fileType)){
            num = 20;
            if(!isLimit20){
              setTimeout(() => {
                this.$message.error(this.$t('knowledgeManage.limitSize')+`${num}MB!`);
                this.fileList = this.fileList.filter(
                  (files) => files.name !== file.name
                );
              }, 50);
              return false
          }
          return true
        }
        return  true
      }
    },
    //  验证文件格式
    verifyRepeat(file) {
      let res = true;
      setTimeout(() => {
        this.fileList = this.fileList.reduce((accumulator, current) => {
          const length = accumulator.filter(
            (obj) => obj.name === current.name
          ).length;
          if (length === 0) {
            accumulator.push(current);
          } else {
            this.$message.warning(current.name + this.$t('knowledgeManage.fileExist'));
            res = false
          }
          return accumulator;
        }, []);
        return res;
      }, 50);
    },
    nextStep(){
      //上传文件类型
      if(this.fileType === 'file' || this.fileType === 'fileUrl'){
        if (this.fileIndex < this.fileList.length){
          this.$message.warning('文件上传中...')
          return false
        }
        if(this.fileList.length === 0){
          this.$message.warning('请上传文件!')
          return false
        }
      }
      //url逐条上传
      if(this.fileType === 'url'){
        if(this.docInfoList.length === 0){
          this.$message.warning('请上输入url!')
          return false
        }
      }
      this.active = 2
    },
    preStep(){
      this.active = 1
    }
  }
};
</script>
<style lang="scss" scoped>
.red{color:red;}
.el-input-number {
    line-height: 28px !important;
}
/deep/.el-input-number.is-controls-right .el-input-number__decrease,
/deep/.el-input-number.is-controls-right .el-input-number__increase {
    line-height: 14px !important;
    border: 0;
}
/deep/{
    .el-upload{
        width: 100%;
    }
    .el-upload-dragger{
        width: 100%;
    }
}
.fileUpload {
  width: 80%;
  padding-top: 30px;
  margin: 0 auto;
  .fileStep {
    width: 40%;
    margin: 0 auto;
  }
  .fileBtn{
    padding: 20px 0 15px 0;
    display:flex;
    justify-content: center;
  }
  .dialog-body {
    padding: 0 20px;
    width:100%;
    .upload-title {
      text-align: center;
      font-size: 18px;
      margin-bottom: 20px;
    }
    .upload-box {
      height: auto;
      min-height: 190;
      width: 100% !important;
      .upload-img{
        width:56px;
        height:56px;
        margin-top:30px;
      }
      .click-text{
        margin-top:10px;
          .clickUpload{
          color: #384bf7;
          font-weight:bold;
        }
      }
      .el-upload-dragger {
        .el-icon-upload {
          margin: 46px 0 10px 0 !important;
          font-size: 32px !important;
          line-height: 36px !important;
          color: #384bf7;
        }
        .el-upload__text {
          margin-top: -10px;
        }
      }
      .size{margin-right:10px;}
      .file-size{margin-left: 10px;}
    }

    .echo-img-box {
      background-color: transparent !important;
      .echo-img {
        img,
        video {
          width: auto;
          height: 80px;
          margin: 10px auto;
          border-radius: 4px;
          background-color: transparent;
        }
        audio {
          width: 300px;
          height: 54px;
          margin: 50px auto;
        }
      }
      .docFile {
        img {
          margin: 0;
          width: 60px;
          height: 100px;
        }
      }
    }
    .tips {
      padding:20px 20px;
      p {
        color: #9d8d8d !important;
        .template_downLoad{
          color: #384bf7;
          cursor: pointer;
        }
      }
    }
  }
  .el-upload-url{
    width:100%;
    padding:0 20px;
    .upload-url{
      background-color: #fff;
      border: 1px solid #D4D6D9;
      border-radius: 6px;
      height:100%;
      box-sizing: border-box;
      text-align: center;
      cursor: pointer;
      overflow: hidden;
      padding:20px;
    }
    .upload-url:hover{
      border-color:#384BF7;
    }
  }
}
.next{
  padding:20px;
  display: flex;
  justify-content:flex-end;
}
.params_form{
  margin-top:10px;
  background:#fff;
  border: 1px solid #D4D6D9;
  border-radius:6px;
  .el-form{
    padding:10px;
  }
}
.page-title{
  .back{
    font-size:18px;
    margin-right: 10px;
    cursor: pointer;
  }
}
.file-list{
  padding: 20px;
  .document_lise_item{
    cursor: pointer;
    padding:5px 10px;
    list-style: none;
    background: #fff;
    border-radius:4px;
    box-shadow: 1px 2px 2px #ddd;
    display:flex;
    align-items:center;
    margin-bottom:10px;
    .lise_item_box{
      width:100%;
      display:flex;
      align-items:center;
      justify-content:space-between;
      .size{
          img{
            width: 18px;
            height:18px;
            margin-bottom:-3px;
          }
          .file-size{
            margin-left:10px;
          }
      }
    }
  }
  .document_lise_item:hover{
    background: #ECEEFE;
  }
}
</style>