/*根据finish为1或2时，判断是否打印结束*/
import workerTimer from './worker'
import {parseSub, isSub} from "@/utils/util.js"

const Print = function (opt) {
    this.sentenceArr = []
    this.sIndexMap={}
    this.timer = opt.timer || 10; //打印速度
    this.t = null;
    this.sIndex = 0
    this.printStatus = 0
    this.fullWord = ''
    this.searchList = []
    this.onPrintEnd = (opt.onPrintEnd && (typeof opt.onPrintEnd === 'function')) ? opt.onPrintEnd : () => {
    };
    this.looper = null
}
Print.prototype = {
    print(sentence,privateData, printingCB, endCB) {
        if(privateData.searchList  && privateData.searchList.length){
            this.searchList = privateData.searchList
        }
        this.sentenceArr.push(sentence)
        this.loop(printingCB, endCB, "truely")
    },
    stop() {
        this.sentenceArr = []
        this.sIndexMap = {}
        this.sIndex = 0
        this.looper && this.looper.stop()
    },
    loop(printingCB, endCB) {

        //如果正在打印或者打印结束
        if (this.printStatus) {
            return
        }

        let curSentence = this.sentenceArr[this.sIndex]
        this.printStatus = 1
        if(!curSentence){
            console.log(this.sIndex, this.sentenceArr)
        }
        this.looper = new Looper(this.sIndex, curSentence, this.timer, (world) => {
            this.printStatus = 1
            let isEnd = this.sIndex === this.sentenceArr.length -1
            printingCB({world,finish:curSentence.finish, isEnd},this.searchList)
        }, (data) => {
            this.printStatus = 0
            this.sIndex++;
            if (this.sentenceArr[this.sIndex]) {
                this.loop(printingCB, endCB)
            } else {
                this.onPrintEnd()
            }
        },this.sIndexMap)
    },
    getAllworld(){
        let str = ''
        this.sentenceArr.forEach((n,i)=>{
            str += n.response
        })
        return str
    }
}

const Looper = function (sIndex, sentence, timer, printCB, endCB,sIndexMap) {
    this.sIndex = sIndex
    this.sIndexMap=sIndexMap
    this.sentence = sentence ? sentence.response : ""
    // this.sentence = sentence.response
    this.timer = timer
    this.t = null
    this.index = 0
    this.printCB = printCB
    this.endCB = endCB
    this.start()
}
Looper.prototype = {
    start() {
        if(this.sentence === ''){
            this.printCB('')
            this.stop()
            this.index++;
            return
        }
        // 处理索引引文标签
        if(isSub(this.sentence)){
            this.printCB(parseSub(this.sentence))
            this.stop()
            this.index++;
            return
        }

        // this.printFn();

        let sentenceArr = this.sentence.split('')
        if(sentenceArr.length>100){
            sentenceArr = this.sentence.split(',')
        }
        this.t = workerTimer.setInterval(() => {
            if (this.index === sentenceArr.length) {
                this.stop()
                return
            }
            this.printCB(sentenceArr[this.index])
            this.index++;
        }, this.timer,this)
    },
    printFn(){
        let sentenceArr = this.sentence.split('')
        this.printCB(sentenceArr[this.index])
        this.index++;
        if(this.index !== sentenceArr.length){
            this.t = workerTimer.setTimeout(()=>{
                this.printFn()
            },this.timer,this)
        }else{
            this.stop()
        }
    },
    stop() {
        // console.log('关闭定时器',this.sIndexMap)
        if(!this.sIndexMap[`${this.sIndex}`]){
            this.sIndexMap[`${this.sIndex}`]=true
            this.endCB({msg: 'end', index: this.sIndex})
        }else{
            console.log(this.sIndex, this.t, this.sentence)
        }
        // this.t && workerTimer.clearTimeout(this.t)
        this.t && workerTimer.clearInterval(this.t)
    }
}

export default Print
