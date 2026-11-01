---
name: find-cited-papers-by-venue
description: "按\"特定期刊/会议 + 主题\"查找高被引、已发表论文（带 DOI 与引文数），用于找范本、做文献调研或选刊参考。触发：找某刊好论文、找高被引 letter、查某会议代表作、按 venue 拉文献。"
---

# 按期刊/会议查高被引论文（OpenAlex）

当用户要"找某本刊里写得好/高被引的论文""找某会议的范本""按 venue 拉文献清单"时使用本技能。

## 为什么用 OpenAlex 而不是 Semantic Scholar
- Semantic Scholar 免费 API（`api.semanticscholar.org/graph/v1/paper/search`）**共享 IP 限流极严**，实测连发 4 个请求即 429，退避 55s 仍 429，基本不可用。
- **OpenAlex**（`api.openalex.org`）免费、无需 key、额度宽松，引文数据（`cited_by_count`）完整，足够排序与筛选。

## 工作流

### 第 1 步：解析 source id（关键！）
OpenAlex **不能用 `primary_location.source.display_name` 做 filter**（会 400 "not a valid field"）。必须先用 display name 解析出 source id：

```
GET https://api.openalex.org/sources?search=<刊名>&per-page=5
```
在 `results` 里按 `display_name` 精确匹配（大小写不敏感），取 `id`（形如 `https://openalex.org/S4210234060`，只要末尾 `S...` 段）。

常见 IEEE letter 刊 source id（备查，可能变动，以实时查询为准）：
- IEEE Networking Letters: S4210234060
- IEEE Sensors Letters: S4210220808
- IEEE Wireless Communications Letters: S2500830676
- IEEE Communications Letters: S147316732

### 第 2 步：按 source + 主题查论文
```
GET https://api.openalex.org/works?search=<主题词>&filter=primary_location.source.id:<SID>&sort=cited_by_count:desc&per-page=10&mailto=<你的邮箱>
```
- `search` 是相关性检索（命中 title/abstract），可填 "Internet of Things" / "federated learning" 等。
- `sort=cited_by_count:desc` 按被引数降序。
- **读取 `results` 字段（不是 `works`）**，每条取 `title` / `publication_year` / `cited_by_count` / `doi`（去 `https://doi.org/` 前缀）。

### 实现提示（Python）
用 `urllib.request` + `urllib.parse.urlencode`；`mailto` 参数让 OpenAlex 视为礼貌请求。一次循环跑多个 venue 即可横向对比。

## 输出建议
给用户时列出：标题 / 年份 / 被引数 / DOI 直链，并**标注"该学它哪一点"**（结构、系统模型、评估方式等），比单纯罗列更有用。
注：OpenAlex 引文数通常低于 Google Scholar，用作排序参考即可。
