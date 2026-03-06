# 技能目录说明

本目录为技能根路径（可在 `app/config/config.yaml` 的 `skill.root_path` 中配置，默认 `./skills`）。

## 默认目录结构

每个技能占一层以技能名命名的子目录，结构如下：

```
skills/
  <技能名>/           # 例如 weather
    SKILL.md          # 技能定义与说明
    scripts/          # 脚本程序
    references/       # 文档
    assets/           # 静态资源
```

| 路径 | 说明 |
|------|------|
| `SKILL.md` | 技能定义与说明，供 Agent 与工具解析 |
| `scripts/` | 脚本程序 |
| `references/` | 文档与参考资料 |
| `assets/` | 静态资源（图片、配置等） |

技能列表由 `skills/skills.json` 维护（路径由配置项 `skill.skill_json_path` 指定），应用会据此加载并暴露给对话与工具使用。
