// onnxruntime-web WASM файлдарын public/ort/-ке көшіру (интернетсіз режим үшін, тек біреуі керек).
import { copyFileSync, mkdirSync } from 'node:fs'
const src = 'node_modules/onnxruntime-web/dist/'
mkdirSync('public/ort', { recursive: true })
for (const f of ['ort-wasm-simd-threaded.wasm', 'ort-wasm-simd-threaded.mjs']) copyFileSync(src + f, 'public/ort/' + f)
console.log('ort wasm → public/ort/')
