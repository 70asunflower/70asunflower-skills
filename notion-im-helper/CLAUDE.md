# Notion IM Helper — Agent Definition

**所有触发规则、路由规则、格式规则的唯一真相源是 [SKILL.md](SKILL.md)。** 本文件只做入口指引，不再复制规则（历史上复制过，已发生漂移——caption 规则曾两边矛盾）。

调用前必读 SKILL.md 的三件事：

1. **OS vs Page 互斥路由**（SKILL.md「Trigger Rules」§）：消息以 `os ` 开头 → OS 管道；否则 → 页面管道。绝不串线。
2. **caption 只有一种用法**：与图片/链接同消息时作分隔符（`--caption` 落到图/书签上）。`record.py caption` 独立追加路径已废弃，不要用。
3. **内容传参**：一律写 `scripts/.pending_content.txt`（脚本所在目录），不走命令行参数。

执行与输出协议（`OK|` / `ERROR|` 前缀处理、安全规则）同样见 SKILL.md。
