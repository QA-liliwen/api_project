// 角色英文值 → 中文显示（数据库与脚本统一存英文值，前端仅做展示映射）
export const ROLE_LABELS = {
    zhihui: '智慧',
    exam: 'exam',
    content: 'content',
    org: '机构',
    student: '学生',
    afterschool: '托管',
};

export function roleLabel(role) {
    return ROLE_LABELS[role] || role;
}
