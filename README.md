# Check and trigger github build action

一个用于监控上游 GitHub 仓库发布并触发构建 workflow 的轻量脚本和定时 workflow。

---

## 功能概述

- 定期（由 GitHub Actions 定时触发）检查 `data/git-repo.json` 中列出的上游仓库的最新 release tag。  
- 对比 `wcbing-build/<package>-debs` 仓库的最新 release tag；若不一致则通过 `workflow_dispatch` API 触发 `wcbing-build` 中对应仓库的 workflow。


## 文件结构

- `.github/workflows/check.yaml`  
定时运行 `check.py` 的 Workflow（每日一次，支持手动触发）。
- `check.py`  
主脚本，负责检查并在需要时触发构建。
- `data/git-repo.json`  
待监控的仓库列表（JSON）。

### git-repo.json 示例

脚本期望 `data/git-repo.json` 是一个从 `name` 到仓库字符串 (`owner/repo`) 的映射，例如：

```json
{
    "dufs": "sigoden/dufs",
    "filebrowser": "filebrowser/filebrowser",
    "otherpkg": "someuser/otherpkg"
}
```

脚本会把 `name` 作为包名，并检查 `wcbing-build/<name>-debs` 的最新发布标签，以决定是否触发构建。


## Secrets 与权限

- workflow 会把 `GITHUB_PAT` 从 Secrets 注入到环境（在 `scheduled-check.yaml` 中使用 `${{ secrets.github_pat }}`）。
- 请在仓库 Secrets 中添加一个个人访问令牌（PAT），命名为 `github_pat`，并确保该 PAT 拥有触发 workflow 所需的权限（`workflow` 权限或 repo 访问）。


## 本地运行

```bash
export GITHUB_PAT=github_pat_xxx
python3 check.py
```
