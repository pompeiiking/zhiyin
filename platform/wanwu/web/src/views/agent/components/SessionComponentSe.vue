<template>
  <div class="session rl">
    <!-- <div class="session-setting">
      <el-dropdown class="right-setting" @command="gropdownClick">
        <i class="el-icon-more more"  trigger="click" ></i>
        <el-dropdown-menu :append-to-body="false" placement="bottom-end" slot="dropdown">
          <el-dropdown-item command="clear">{{$t('agent.clearHistory')}}</el-dropdown-item>
        </el-dropdown-menu>
      </el-dropdown>
    </div> -->

    <div class="history-box showScroll" id="timeScroll" v-loading="loading" ref="timeScroll">
      <div  v-for="(n,i) in session_data.history"  :key="`${i}sdhs`">
        <!--问题-->
        <div v-if="n.query" class="session-question">
          <div :class="['session-item','rl']">
            <img class="logo" :src="require('@/assets/imgs/robot-icon.png')"/>
            <div class="answer-content" >
                <div class="answer-content-query">
                  <span class="session-setting-id" v-if="$route.params && $route.params.id">智能体ID: {{$route.params.id}}</span>
                  <div class="echo-doc-box" v-if="n.fileName && n.fileName !== ''">
                    <img :src="require('@/assets/imgs/fileicon.png')"  class="docIcon" />
                    <div class="docInfo">
                      <p class="docInfo_name">文件名称：{{n.fileName||'...'}}</p>
                      <p class="docInfo_size">文件大小:{{getFileSizeDisplay(n.fileSize)}}</p>
                    </div>
                  </div>
                  <el-popover
                          placement="bottom-start"
                          trigger="hover"
                          :visible-arrow="false"
                          popper-class="query-copy-popover"
                          content="">
                    <p class="query-copy" @click="queryCopy(n.query)" style="cursor: pointer"><i class="el-icon-s-order"></i>&nbsp;{{$t('agent.copyToInput')}}</p>
                    <span slot="reference" class="answer-text">{{n.query}}</span>
                  </el-popover>
                </div>

              <!-- <div v-if="n.requestFileUrls && n.requestFileUrls.length" class="file-path query-file">
                <el-image :src='n.requestFileUrls[0]' :preview-src-list="[n.requestFileUrls[0]]"></el-image>
              </div> -->
            </div>
          </div>
        </div>
        <!--loading-->
        <div v-if="n.responseLoading"  class="session-answer">
          <div :class="['session-item','rl']">
            <img class="logo" :src="'/user/api/'+ defaultUrl" />
            <div class="answer-content"><i class="el-icon-loading"></i></div>
          </div>
        </div>
        <!--pending-->
        <div v-if="n.pendingResponse"  class="session-answer">
          <div :class="['session-item','rl']">
            <img class="logo" :src="'/user/api/'+ defaultUrl" />
            <div class="answer-content" style="padding:0 10px;color:#E6A23C;">{{n.pendingResponse}}</div>
          </div>
        </div>
        
        <!-- 回答故障  code:7-->
        <div class="session-error" v-if="n.error"><i class="el-icon-warning"></i>&nbsp;{{n.response}}</div>

        <!--回答 文字+图片-->
        <div v-if="(n.response && !n.error)" class="session-answer">
          <div  v-if="[0,1,2,3,4,6,20,21,10].includes(n.qa_type)" :class="['session-item','rl']">
             <img class="logo" :src="'/user/api/'+ defaultUrl" />
            <div class="session-wrap" style="width:calc(100% - 30px);">
              <div v-if="showDSBtn(n.response)" class="deepseek" @click="toggle($event,i)">
                <template v-if="n.qa_type === 20">
                  <img :src="require('@/assets/imgs/tool-icon.png')" class="think_icon"/>{{n.toolText}}
                </template>
                 <template v-else>
                    <img :src="require('@/assets/imgs/think-icon.png')" class="think_icon"/>{{n.thinkText}}
                </template>
                <i v-bind:class="{'el-icon-arrow-down': !n.isOpen,'el-icon-arrow-up': n.isOpen}"></i>
              </div>
              <div class="answer-content" v-bind:class="{'ds-res':showDSBtn(n.response)}" v-html="showDSBtn(n.response)?replaceHTML(n.response,n):n.response"></div>
            </div>
          </div>
          <div v-else :class="['session-item','rl']">
            <img class="logo" :src="'/user/api/'+ defaultUrl"/>
            <div v-if="n.code === 7"  class="answer-content session-error"><i class="el-icon-warning"></i> &nbsp;{{n.response}}</div>
            <div v-else  class="answer-content" v-html="(n.response)"></div>
          </div>
          <!--文件-->
          <div v-if="n.gen_file_url_list && n.gen_file_url_list.length" class="file-path response-file">
            <el-image v-for="(g,k) in n.gen_file_url_list" :key="k" :src='g' :preview-src-list="[g]"></el-image>
          </div>
          <!--出处-->
          <div v-if="n.searchList && n.searchList.length" class="search-list">
            <div v-for="(m,j) in n.searchList" :key="`${j}sdsl`" class="search-list-item">
              <div>
                <span @click="collapseClick(n,m,j)"><i :class="['',m.collapse?'el-icon-caret-bottom':'el-icon-caret-right']"></i>出处：</span>
                <a v-if="m.link" :href="m.link" target="_blank">{{m.link}}</a>
                <span v-if="m.title" style="margin-left: 10px" v-html="m.title"></span>
              </div>
              <el-collapse-transition>
                <div v-show="m.collapse?true:false"  class="snippet">
                  <p v-html="m.snippet"></p>
                </div>
              </el-collapse-transition>
            </div>
          </div>
          <!--停止生成 重新生成 点赞   session code 是0时不可操作-->
          <div class="answer-operation">
            <div class="opera-left">
              <span v-if="i===(session_data.history.length-1)" class="restart" @click="refresh">
                <!-- <i class="el-icon-refresh" @click="refresh">&nbsp;{{$t('agent.refresh')}}</i> -->
                <img :src="require('@/assets/imgs/refresh-icon.png')"/>
                <!-- &nbsp;{{$t('agent.refresh')}} -->
              </span>
            </div>
            <div class="opera-right" style="flex:0;" @click="()=>{copy(n.oriResponse) && copycb()}" >
              <img :src="require('@/assets/imgs/copy-icon.png')"/>
              <!-- <i class="el-icon-copy-document copy-icon" style="padding: 0 6px;margin: 0;" :title="$t('agent.clickCopy')" @click="()=>{copy(n.oriResponse) && copycb()}"></i> -->
            </div>
          </div>
        </div>
        <!-- 回答 仅图片-->
        <div v-if="!n.response && n.gen_file_url_list && n.gen_file_url_list.length" class="session-answer">
          <div :class="['session-item','rl']">
            <img class="logo" :src="'/user/api/'+defaultUrl || basePath + '/img/b.png'"/>
            <div class="answer-content">
              <div v-if="n.gen_file_url_list && n.gen_file_url_list.length" class="file-path response-file no-response">
                <el-image v-for="(g,k) in n.gen_file_url_list" :key="k" :src='g' :preview-src-list="[g]"></el-image>
              </div>
            </div>
          </div>
          <!--仅图片时只有 重新生成-->
          <div class="answer-operation">
            <div class="opera-left">
              <span v-if="i===(session_data.history.length-1)" class="restart"><i class="el-icon-refresh" @click="refresh">&nbsp;{{$t('agent.refresh')}}</i></span>
            </div>
          </div>
        </div>
    </div>
    </div>
  </div>
</template>

<script>
import {marked} from 'marked'
var highlight = require('highlight.js');
import 'highlight.js/styles/atom-one-dark.css';

marked.setOptions({
    renderer: new marked.Renderer(),
    gfm: true,
    tables: true,
    breaks: false,
    pedantic: false,
    sanitize: false,
    smartLists: true,
    smartypants: false,
    highlight: function (code) {
        return highlight.highlightAuto(code).value;
    }
});

export default {
  props: ['sessionStatus','defaultUrl'],
  data(){
      return{
          autoScroll:true,
          scrollTimeout:null,
          isDs:['txt2txt-002-001','txt2txt-002-002','txt2txt-002-004','txt2txt-002-005','txt2txt-002-006','txt2txt-002-007','txt2txt-002-008'].indexOf(this.$route.params.id) !=-1,
          loading:false,
          marked:marked,
          session_data:{
              "tool":"",
              "searchList": [],
              "history":[],
              "response":""
          },
          basePath: this.$basePath,
          current_data:[],
          //标注相关
          c:null,
          ctx:null,
          canvasShow:false,
          cv:null,
          currImg: {
              url: '',
              width: 0, // 原始宽高
              height: 0,
              w: 0, // 压缩后的宽高
              h: 358,
              roteX: 0, // 压缩后的比例
              roteY: 0
          },
          imgConfig:["jpeg", "PNG", "png", "JPG", "jpg",'bmp','webp'],
          audioConfig:["mp3", "wav"],
      }
  },
    watch: {
        sessionStatus:{
            handler(val,oldVal) {

            },
            immediate: true
        }
    },
    mounted(){
      this.setupScrollListener();
    },
    beforeDestroy(){
      const container = document.getElementById('timeScroll');
      if (container) {
        container.removeEventListener('scroll', this.handleScroll);
      }
      clearTimeout(this.scrollTimeout);
    },
    methods:{
          setupScrollListener() {
            const container = document.getElementById('timeScroll');
            container.addEventListener('scroll', this.handleScroll);
          },
          handleScroll(e){
            const container = document.getElementById('timeScroll');
            const { scrollTop, clientHeight, scrollHeight } = container;
            // 检测是否接近底部（5px容差）
            const nearBottom = scrollHeight - (scrollTop + clientHeight) < 5;
             // 用户手动滚动时取消自动置底
            if (!nearBottom) {
                this.autoScroll = false;
            }
            // 清除之前的定时器
            clearTimeout(this.scrollTimeout);
            // 设置新的定时器检测滚动停止
            this.scrollTimeout = setTimeout(() => {
                // 如果停止时接近底部，恢复自动置底
                if (nearBottom) {
                  this.autoScroll = true;
                  this.scrollBottom();
                }
              }, 500); // 500ms内没有新滚动视为停止
          },
          replaceHTML(data,n){
            let _data = data
            // var a = new RegExp('<think>')
            // var b = new RegExp('</think>')
            // if(b.test(data)){
            //   n.thinkText = this.$t('agent.alreadyThink')
            // }
            // // 如果没有返回前缀，则补上
            // if(b.test(data) && !a.test(data)){
            //   _data = '<think>\n'+data
            // }
            // return _data.replace(/think>/g,'section>')
            const thinkStart = /<think>/i;
            const thinkEnd = /<\/think>/i;
            const toolStart = /<tool>/i;
            const toolEnd = /<\/tool>/i;

            // 处理 think 标签
            if(thinkEnd.test(data)) {
              n.thinkText = '已深度思考';
              if(!thinkStart.test(data)) {
                data = '<think>\n' + data;
              }
            }

            // 新增处理 tool 标签
            if(toolEnd.test(data)) {
              n.toolText = '已使用工具'; // 需要添加对应的翻译
              if(!toolStart.test(data)) {
                data = '<tool>\n' + data;
              }
            }

            // 统一替换为 section 标签
            return data.replace(/think>/gi, 'section>').replace(/tool>/gi, 'section>');
          },
          showDSBtn(data){
            // const pattern = /<\/?think>/;
            const pattern = /<(think|tool)(\s[^>]*)?>|<\/(think|tool)>/;
            const matches = data.match(pattern);
            if(!matches){
              return false
            }
            return true
          },
          toggle(event,index){
            const name = event.target.className;
            if (
              name === "deepseek" ||
              name === "el-icon-arrow-up" ||
              name === "el-icon-arrow-down"
            ) {
              this.session_data.history[index].isOpen =
                !this.session_data.history[index].isOpen;
              this.$set(
                this.session_data.history,
                index,
                this.session_data.history[index]
              );
              let elm = null;
              if (name === "el-icon-arrow-up" || name === "el-icon-arrow-down") {
                elm = event.target.parentNode.parentNode
                  .getElementsByClassName("answer-content")[0]
                  .getElementsByTagName("section")[0];
              } else {
                elm = event.target.parentNode
                  .getElementsByClassName("answer-content")[0]
                  .getElementsByTagName("section")[0];
              }
              if (!Boolean(this.session_data.history[index].isOpen)) {
                elm.className = "hideDs";
              } else {
                elm.className = "";
              }
            }
          },
        queryCopy(text){
            this.$emit('queryCopy',text)
        },
        copy(text){
            text = text.replaceAll('<br/>','\n')
            var textareaEl = document.createElement('textarea');
            textareaEl.setAttribute('readonly', 'readonly'); // 防止手机上弹出软键盘
            textareaEl.value = text;
            document.body.appendChild(textareaEl);
            textareaEl.select();
            var res = document.execCommand('copy');
            document.body.removeChild(textareaEl);
            return res;
        },
        copycb(){
            this.$message.success(this.$t('agent.copyTips'))
        },
        collapseClick(n,m,j){
            if(!m.collapse){
                this.$set(n.searchList,j, {...m,collapse:true})
            }else{
                this.$set(n.searchList,j, {...m,collapse:false})
            }
            //this.scrollBottom()
        },
        doLoading(){
          this.loading = true
        },
        scrollBottom () {
          if (!this.autoScroll) return;
            this.$nextTick(() => {
                this.loading = false
                document.getElementById('timeScroll').scrollTop = document.getElementById('timeScroll').scrollHeight;
            });
        },
        pushHistory(data){
            this.session_data.history.push(data)
            this.scrollBottom()
        },
        replaceLastData(index,data){
          this.$set(this.session_data.history,index,data)
          this.scrollBottom()
        },
        getFileSizeDisplay(fileSize){
            if (!fileSize || typeof fileSize !== 'number' || isNaN(fileSize)) {
              return '...';
            }
            return fileSize > 1024
                  ? `${(fileSize / (1024 * 1024)).toFixed(2)} MB`
                  : `${fileSize} bytes`;
        },
        //websocket 替换全部数据
        replaceData(data){
            this.session_data = data
            this.scrollBottom()
        },
        //http 只替换history
        replaceHistory(data){
            this.session_data.history = data
            this.scrollBottom()
            //this.loadAllImg()
        },
        replaceHistoryWithImg(data){
            this.session_data.history = data
            this.$nextTick(()=>{
                this.preTagging(data[0].annotation)
            })
        },
        clearData(){
            this.session_data = {
                "tool":"",
                "searchList": [],
                "history":[],
                "response":""
            }
        },
        loadAllImg(){
            this.session_data.history.forEach((n,i)=>{
                n.gen_file_url_list.forEach((m,j)=>{
                    setTimeout(()=>{
                        this.$set(this.session_data.history[i].gen_file_url_list, j, {...m,loadedUrl:m.url,loading:false})
                    },2000)
                })
            })
        },
        gropdownClick(){
            this.$emit('clearHistory')
        },
        getList(){
          return JSON.parse(JSON.stringify(this.session_data.history.filter((item)=>{ delete item.operation ; return item})))
            // return JSON.parse(JSON.stringify(this.session_data.history.filter((item)=>{ delete item.operation ; return !item.pending})))
        },
        getAllList(){
            return JSON.parse(JSON.stringify(this.session_data.history))
        },
        stopLoading(){
            this.session_data.history = this.session_data.history.filter((item)=>{ return !item.pending});
        },
        stopPending(){
            this.session_data.history = this.session_data.history.filter(item =>{
              if(item.pending){
                item.responseLoading = false
                item.pendingResponse = '本次回答已被终止'
              }
              return item;
            })
        },
        refresh(){
            if(this.sessionStatus === 0){return}
            this.$emit('refresh')
        },
        preZan(index,item){
            if(this.sessionStatus === 0){return}
            this.$set(this.session_data.history,index,{...item,evaluate:1})
        },
        preCai(index,item){
            if(this.sessionStatus === 0){return}
            this.$set(this.session_data.history,index,{...item,evaluate:2})
        },
        doScore(index,evaluate){

        },
        //=================标注相关===============
        initCanvasUtil () {
            this.canvasShow = true
            this.$nextTick(()=>{
                // 开始画图 canvas, 2d, 宽高，形状
                this.cv && this.cv.destroy() && this.cv.clearPre() && this.cv.clearLabels() && (this.cv = null)
                this.cv = new CanvasUtil(this)
            })
        },
        preTagging (response) {
            // canvas大小重置
            this.currImg = {
                url: '',
                width: 0,
                height: 0,
                w: 0,
                h: 358,
                roteX: 0,
                roteY: 0,
                dx: 0,
                dy: 0
            }
            // 图片原始宽高
            var image = new Image()
            image.src = response.annotationImg
            image.onload = () => {
                this.currImg.width = image.width
                this.currImg.height = image.height
                //if (!this.c) {
                    this.c = document.getElementById('mycanvas')
                    this.ctx = this.c.getContext('2d')
                //}
                this.resizeCanvas()
                this.initCanvasUtil()

                this.$nextTick(() => {
                    this.echoLabels(response)
                })
            }
        },
        echoLabels (response) {
            this.cv.echoLabels(response)
        },
        resizeCanvas () {
            this.currImg.w = 0
            this.currImg.h = 358
            this.currImg.dx = 0
            this.currImg.dy = 0
            this.currImg.roteX = 0
            this.currImg.roteY = 0

            let currImg = this.currImg
            let contain = document.getElementById('mycantain')
            if (currImg.width > contain.offsetWidth) {
                // 宽度大于容器
                this.currImg.roteX = currImg.width / contain.offsetWidth
                currImg.w = contain.offsetWidth
                currImg.h = currImg.height * contain.offsetWidth / currImg.width
                // 压缩后高度大于cantain
                if (currImg.h > contain.offsetHeight) {
                    currImg.h = contain.offsetHeight
                    currImg.w = currImg.width * currImg.h / currImg.height
                    currImg.roteX = currImg.width / currImg.w
                    currImg.dx = (contain.offsetWidth - currImg.w) / 2
                } else {
                    currImg.roteY = currImg.height / currImg.h
                    currImg.dy = (contain.offsetHeight - currImg.h) / 2
                }
            } else {
                // 高度压缩比例
                currImg.roteY = currImg.height / currImg.h
                // 压缩后宽度
                currImg.w = currImg.width * currImg.h / currImg.height
                currImg.roteX = currImg.width / currImg.w
                currImg.dx = (contain.offsetWidth - currImg.w) / 2
            }

            this.canvasShow = true
            this.c.width = currImg.w
            this.c.height = currImg.h
            this.$nextTick(() => {
                this.cv && this.cv.resizeCurrImg(currImg)
            })
        },
    }
}
</script>

<style scoped lang="scss">
/deep/{
  pre{
     white-space: pre-wrap !important;
     min-height: 50px;
     word-wrap: break-word;
     resize: vertical;
     scroll-snap-type: y mandatory;/* 垂直方向强制吸附 */
     .hljs{
        max-height:300px!important;
        white-space: pre-wrap !important;
        min-height: 50px;
        word-wrap: break-word;
        resize: vertical;
        scroll-snap-align: end; /* 最后一条消息吸附到底部 */
     }
  }
  .el-loading-mask{
    background:none !important;
  }
  .answer-content{
    img{
        width: 80% !important;
      }
  }
  .search-list{
    img{
      width: 80% !important;
    }
  }
}
.more{
  color: #384BF7;
}
.session{
  word-break: break-all;
  height: 100%;
  overflow-y: auto;
  .session-item{
    min-height: 80px;
    display: flex;
    // justify-content:flex-end;
    padding: 20px;
    line-height: 28px;
      img{
        width: 30px;
        height: 30px;
        object-fit: cover;
      }
      .logo{
        border-radius: 6px;
      }
      .answer-content{
        // width: calc(100% - 30px);
        padding:10px 15px;
        position: relative;
        color: #333;
        .answer-content-query{
          display: flex;
          flex-wrap: wrap;
          flex-direction: column;
          align-items: flex-start;
          .answer-text{
            background:#7288FA ;
            color:#fff;
            padding:10px 20px 10px 10px;
            border-radius: 0 10px 10px 10px;
          }
          .session-setting-id{
            color: rgba(98, 98, 98, 0.5);
            font-size: 12px;
            margin-top: -8px;
          }
          .echo-doc-box{
            margin-bottom:10px;
            background:#fff;
            width: auto;
            border:1px solid #DCDFE6;
            border-radius:5px;
            display:flex;
            justify-content: space-between;
            align-items: center;
            padding:2px 20px 5px 5px;
            .docIcon{
                width:30px;
                height:30px;
                margin-right:10px;
            }
            .docInfo{
               .docInfo_name{
                  color:#333;
                }
                .docInfo_size{
                  color:#bbbbbb;
                }
            }
          }
        }
        li{
          display: revert!important;
        }
      }
  }
  .session-answer{
    background-color: #ECEEFE;
    border-radius:10px;
    .answer-annotation{
      line-height: 0!important;
      .annotation-img{
        width: 460px;
        object-fit: contain;
        height: 358px;
      }
      .tagging-canvas{
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        margin: auto;
      }
    }

    .no-response{
      margin: 15px 0;
    }
    /*出处*/
    .search-list{
      padding: 0 20px 3px 54px;
      .search-list-item{
        margin-bottom: 5px;
        line-height: 22px;
        p:nth-child(1){
          white-space: normal;
        }
        a,span{
          color: #666;
          cursor: pointer;
          white-space: normal;
          overflow-wrap: break-word;
        }
        a{
          text-decoration:underline;
        }
        a:hover{
          color: deepskyblue;
        }
        .snippet{
          padding: 5px 14px;
        }
      }
    }
    /*操作*/
    .answer-operation{
      display: flex;
      // justify-content: space-between;
      align-items:center;
      padding: 15px 20px 15px 53px;
      color: #777;
      .opera-left{
        // flex: 8;
        .restart{
          cursor: pointer;
          img{
            width: 20px;
            height: 20px;
            padding: 2px;
          }
        }
      }
      .opera-right{
        // flex: 1;
        cursor: pointer;
        display: inline-flex;
        padding-left:10px;
        img{
          width: 20px;
          height: 20px;
          padding: 2px;
        }
        .split-icon{
          background: rgba(195,197,217,.65);
          height: 22px;
          margin: 0 10px;
          width: 1px;
        }
        .copy-icon{
          font-size: 17px;
          padding: 3px 6px;
          margin: 0 15px;
          cursor: pointer;
        }
        .copy-icon:hover{
          color: #33a4df;
        }
      }
    }
  }

  /*图片*/
  .file-path{
    .el-image{
      height: 200px!important;
      background-color: #f9f9f9;
      /deep/.el-image__inner,img{
        width: 100%;
        height: 100%;
        object-fit: contain;
      }
    }
    audio{
      width: 300px!important;
    }
  }
  .query-file{
    padding: 10px 0;
  }
  .response-file{
    margin: 0 0 0 66px;
    width: 400px;
    font-size: 0;
    .img{
      display: inline-block;
      width: 200px;
      height: 200px;
      img{
        width: 100%;
        height: 100%;
      }
    }
  }

  .session-error{
    background-color: #fef0f0;
    border-color: #fde2e2;
    color: #f56c6c!important;
    margin-top: 10px;
    padding: 10px;
    border-radius: 4px;
    .el-icon-warning{
      font-size: 16px;
    }
  }


  .history-box{
    height: calc(100% - 46px);
    overflow-y: auto;
    padding: 20px;
  }
  /*删除历史...*/
  .session-setting{
    position: relative;
    height: 36px;
    .right-setting{
      position: absolute;
      right: 10px;
      top: -5px;
      color: #ff2324;
      font-size: 16px;
      cursor: pointer;
      /deep/{
        .el-dropdown-menu{
          width: 100px;
        }
        .el-dropdown-menu__item{
          padding: 0 15px!important;
        }
      }
    }
  }

  .think_icon{
    width: 12px!important;
    height: 12px !important;
    margin-right:3px;
  }
  .ds-res{
  /deep/ section {
    color: #8b8b8b;
    position:relative;
    font-size:12px;
    *{
      font-size:12px;
    }
  }
  /deep/ section::before{
      content: '';
      position:absolute;
      height:100%;
      width:1px;
      background: #ddd;
      left: -8px;
    }
  /deep/.hideDs{
    display:none;
  }
}

.deepseek{
  font-size: 13px;
  color: #8b8b8b;
  font-weight:bold;
  margin-left:6px;
  cursor:pointer;
}

}

</style>
