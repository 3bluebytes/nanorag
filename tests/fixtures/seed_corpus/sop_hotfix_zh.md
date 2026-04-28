---
category: ops
data_type: sop
---

# SOP：生产环境热修复流程

## 步骤

1. 收到告警后先确认影响范围。
2. 在 staging 环境复现问题。
3. 编写最小化修复 patch。
4. 代码审查（至少一名 senior）。
5. 灰度发布到 5% 流量。
6. 观察 15 分钟无异常后全量推送。
7. 记录 incident timeline。
