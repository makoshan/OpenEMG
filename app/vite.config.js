import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// base './'：App 用 file:// 读 dist/index.html，网页部署也放根目录，两边同一份产物
export default defineConfig({ plugins: [react()], base: './' });
