// tool_key -> 工具组件 映射表
// 新增工具时在此追加一行，值用异步组件实现按需加载
// 表里查不到的 key 由 ToolsView 渲染「开发中」占位，允许前后端上线不同步
export default {
    user_info: () => import('./UserInfoTool.vue'),
    json_format: () => import('./JsonFormatTool.vue'),
    timestamp_convert: () => import('./TimestampConvertTool.vue')
}
