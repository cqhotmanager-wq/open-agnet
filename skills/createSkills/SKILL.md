---
name: 创建SKILL
description: 该文档描述了如何通过智能体创建SKILL
---

## 使用场景
用户调用LLM需要创建新的智能体SKILL时使用

## 执行步骤
1:调用CreateDirectoryTool工具在skills目录下创建目录，目录名称必须是英文驼峰命名方式
2:调用CreateDirectoryTool工具在创建的skills技能目录下面将创建以下目录：
   - `scripts/`：存放 Python 脚本和工具。
   - `references/`：存放与天气相关的参考文档。
   - `assets/`：存放静态资源，如图标、配置文件等。
3.在目录下面写入SKILL.md文档，文档格式如下案例
```markdown
---
name: {技能的名称}
description: {技能的功能描述}
---


## 使用场景
{详细说明智能体的使用场景}

## 执行步骤
{描述执行步骤,需要调用的脚本,执行的命令,调用的tool}

## 输出数据
{描述输出,json,调用的tool}

## 注意事项
{执行期间需要注意的事项}
```
4.新创建的智能体信息加入到skills.json,json格式如下
```json
{
  "skills": [
    {
      "name": "查询天气", 
      "description": "查询指定城市的当前天气情况",
      "location": "./skills/weather/SKILL.md"
    }
  ]
}
```
name:SKILL.MD中的名字
description:SKILL.MD中的描述说明
location:./skills/创建的目录/SKILL.md文件的路径

## 输出数据
1.LLM返回的markdown数据写入到SKILL.md中
2.LLM返回的脚本sh.py写入到scripts目录中

## 注意
1.检查创建的目录是否规范可以调用ListDirectoryTool检查目录结构
2.检查是否有SKILL.md文件
3.检查SKILL.md文件是否规范ReadMarkdownTool工具可以读取