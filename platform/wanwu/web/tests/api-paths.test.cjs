const assert = require('assert')
const fs = require('fs')
const path = require('path')
const vm = require('vm')

const source = fs.readFileSync(path.join(__dirname, '..', 'src/api/chunkFile.js'), 'utf8')
const calls = []
const context = {
  module: { exports: {} },
  request: config => {
    calls.push(config)
    return config
  }
}

vm.runInNewContext(
  source
    .replace(/^import request from "@\/utils\/request";\s*$/m, '')
    .replace(/^export const /gm, 'const ')
    .concat('\nmodule.exports = { continueChunks }'),
  context
)

const params = { fileId: '99', fileName: 'chunk.bin' }
context.module.exports.continueChunks(params)

assert.strictEqual(calls.length, 1, 'continueChunks must make one request')
const config = calls[0]
assert.deepStrictEqual(Object.keys(config).sort(), ['method', 'params', 'url'])
assert.strictEqual(config.url, '/service/api/v1/file/check/list')
assert.strictEqual(config.method, 'get')
assert.strictEqual(config.params, params)

console.log('Chunk check API path test passed.')
