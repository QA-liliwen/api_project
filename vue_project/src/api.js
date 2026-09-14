import axios from 'axios'

// 后端服务地址，换部署环境只改这一处
export const BASE_URL = 'http://172.16.2.60:8000'

const api = axios.create({
    baseURL: BASE_URL,
    timeout: 30000
})

// 统一处理业务错误，组件内不再重复写 alert
api.interceptors.response.use(
    response => {
        const data = response.data
        if (data && data.code !== undefined && data.code !== 0) {
            alert(data.message || '请求失败')
            return Promise.reject(new Error(data.message || '请求失败'))
        }
        return response
    },
    error => {
        alert('网络请求异常：' + error.message)
        return Promise.reject(error)
    }
)

export default api
