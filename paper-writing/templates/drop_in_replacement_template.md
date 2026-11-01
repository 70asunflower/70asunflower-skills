# IEEE Engineering Paper Writer — Agent Handoff Protocol (多 Agent 协作交接协议)

当用户要求“给出详细修改意见，并输出你觉得好的原句，让我发给其他 Agent 去改”时，本 Skill 规定必须生成标准化、零义项歧义的 **Handoff Patch 格式**。下游改文 Agent 无需任何推理，只需执行精准替换。

---

## 协作交互标准模式

### 1. 上游审查 Agent（Auditor）执行
- 读取初稿，按 `references/iron_rules.md` 进行审查；
- 生成符合 `templates/drop_in_replacement_template.md` 的代码块输出；
- 明确标注所在文件路径、锚点段落、前后上下文匹配词。

### 2. 下游改稿 Agent（Writer / Fixer）执行
- 接收标准化替换指令；
- 使用 `replace_file_content` 工具，匹配 `TargetContent` 并替换为 `ReplacementContent`；
- 执行后回报替换成功状态与字数增减量。

---

## 交付代码块标准格式

```markdown
### Patch [编号]: [修改目标小节名]

- **目标文件**: `[绝对路径]`
- **修改意图**: [简要说明修复了哪条铁律或逻辑硬伤]
- **匹配目标 (Target)**:
```text
[严格摘录待替换的完整段落或连续多句，保留首尾精确字符]
```
- **替换文本 (Replacement)**:
```text
[经过 IEEE 风格与工程白话润色后的终稿文本]
```
```
