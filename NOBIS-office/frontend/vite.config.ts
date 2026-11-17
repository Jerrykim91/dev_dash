import {defineConfig} from 'vite';
const target=process.env.API_TARGET||'http://127.0.0.1:18000';
export default defineConfig({server:{port:15173,proxy:{'/api':{target},'/health':{target},'/ws':{target,ws:true}}},build:{chunkSizeWarningLimit:1600}});
