import MarkdownIt from 'markdown-it'
var hljs = require('highlight.js');
hljs.configure({
    lineNumbers: true
});
//import 'highlight.js/styles/atom-one-dark.css';

export const md = MarkdownIt({
    // 在源码中启用 HTML 标签
    html: true,
    // 如果结果以 <pre ... 开头，内部包装器则会跳过。
    highlight: function(str, lang) {
        // if (lang && hljs.getLanguage(lang)) {
        //  console.error('lang', lang)
        //  try {
        //   return '<pre class="hljs" style="padding: 5px 8px;margin: 5px 0;overflow: auto;display: block;"><code>' +
        //    hljs.highlight('lang', str, true).value +
        //    '</code></pre>';
        //  } catch (__) {}
        // }
        // 经过highlight.js处理后的html
        let preCode = ""
        try {
            preCode = hljs.highlightAuto(str).value
        } catch (err) {
            // console.log('err',err);
            preCode = markdownIt.utils.escapeHtml(str);
        }


        // 以换行进行分割
        const lines = preCode.split(/\n/).slice(0, -1)

        // 去掉空行
        let _lines = lines.filter((it,i)=>{ return it!==''})

        // 添加自定义行号
        let html = _lines.map((item, index) => {
            return '<li class="line-li"><span class="line-numbers-rows"></span>' + item +
                '</li>'
        }).join('')
        html = '<ol style="padding: 0px 30px;">' + html + '</ol>'

        // 代码复制功能
        let htmlCode =
            `<div style="color: #888;border-radius: 0 0 5px 5px;">`

        htmlCode += `<div class="code-header">`
        htmlCode +=
            `${lang}<a class="copy-btn mk-copy-btn" style="cursor: pointer;">复制 </a>`
        htmlCode += `</div>`

        htmlCode +=
            `<pre class="hljs" style="padding:0 10px!important;margin-bottom:5px;overflow: auto;display: block;border-radius: 5px;"><code>${html}</code></pre>`;
        htmlCode += '</div>'
        return htmlCode
    }
})


/*
* const markdownIt = MarkdownIt({
  // 在源码中启用 HTML 标签
  html: true,
  // 如果结果以 <pre ... 开头，内部包装器则会跳过。
  highlight: function(str, lang) {
   // if (lang && hljs.getLanguage(lang)) {
   //  console.error('lang', lang)
   //  try {
   //   return '<pre class="hljs" style="padding: 5px 8px;margin: 5px 0;overflow: auto;display: block;"><code>' +
   //    hljs.highlight('lang', str, true).value +
   //    '</code></pre>';
   //  } catch (__) {}
   // }
   // 经过highlight.js处理后的html
   let preCode = ""
   try {
    preCode = hljs.highlightAuto(str).value
   } catch (err) {
    // console.log('err',err);
    preCode = markdownIt.utils.escapeHtml(str);
   }


   // 以换行进行分割
   const lines = preCode.split(/\n/).slice(0, -1)
   // 添加自定义行号
   let html = lines.map((item, index) => {
    // 去掉空行
    if (item == '') {
     return ''
    }
    return '<li><span class="line-num" data-line="' + (index + 1) + '"></span>' + item +
     '</li>'
   }).join('')
   html = '<ol style="padding: 0px 30px;">' + html + '</ol>'

   // 代码复制功能
   codeDataList.push(str)
   let htmlCode =
    `<div style="background:#0d1117;margin-top: 5px;color: #888;padding:5px 0;border-radius: 5px;">`

   htmlCode += `<div style="text-align: end;font-size: 12px;">`
   htmlCode +=
    `${lang}<a class="copy-btn" code-data-index="${codeDataList.length - 1}" style="cursor: pointer;"> 复制代码 </ a>`
   htmlCode += `</div>`

   htmlCode +=
    `<pre class="hljs" style="padding:0 8px;margin-bottom:5px;overflow: auto;display: block;border-radius: 5px;"><code>${html}</code></pre>`;
   htmlCode += '</div>'
   return htmlCode
  }
 })
* */
