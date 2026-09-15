const fs = require('fs');
const path = require('path');
const childProcess = require('child_process');


class VersionInfoPlugin {
  apply(compiler) {
    compiler.hooks.done.tap('VersionInfoPlugin', (stats) => {
      try {
        const pkg = require('../package.json');//定义版本,每个版本更新需要修改,中间版本已后端为主
        const branch = childProcess.execSync('git rev-parse --abbrev-ref HEAD').toString().trim();
        const commitId = childProcess.execSync('git rev-parse HEAD').toString().trim();
        const commitTime = childProcess.execSync('git log -1 --format=%cd').toString().trim();
        const notes = '版本基于后端版本定义';
        const versionInfo = {
          version: pkg.version,
          branch,
          commitId,
          commitTime,
          notes,
          buildTime: new Date().toLocaleString()
        };
        
        // 获取webpack配置的输出目录，默认为dist
        const outputPath = stats.compilation.outputOptions.path || path.join(process.cwd(), 'dist');
        
        // 确保目录存在
        if (!fs.existsSync(outputPath)) {
          fs.mkdirSync(outputPath, { recursive: true });
        }
        
        fs.writeFileSync(
          path.join(outputPath, 'version.json'),
          JSON.stringify(versionInfo, null, 2)
        );
        
        console.log('版本信息文件已生成:', path.join(outputPath, 'version.json'));
      } catch (e) {
        console.error('生成版本信息失败:', e.message);
      }
    });
  }
}

module.exports = VersionInfoPlugin;