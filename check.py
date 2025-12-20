#!/usr/bin/env python3
import json
import logging
import os
import re
import requests
from concurrent.futures import ThreadPoolExecutor, wait


# 全局配置变量
CONFIG = {
    "data_dir": "data",
    "thread": 5,
    "dry_run": False,
    "ref": "main",
    "workflow": "trigger_build.yaml",
    "github_pat": "",  # 从环境读取 token
}

# 日志等级，若需要展示每次请求结果请使用 INFO 等级
logging.basicConfig(level=logging.INFO)


# 获取最新标签
def latest_releases_tag(repo: str) -> str:
    url = os.path.join("https://github.com", repo, "releases/latest")
    try:
        location = requests.head(url).headers.get("Location", "")
        match = re.search(r".*releases/tag/([^/]+)", location)
        return match.group(1) if match else ""
    except requests.RequestException as e:
        logging.error(e)
        return ""


def repo_exists(repo: str) -> bool:
    url = os.path.join("https://github.com", repo)
    try:
        r = requests.head(url, allow_redirects=True)
        return r.status_code == 200
    except requests.RequestException as e:
        logging.error(e)
        return False


def trigger_workflow(repo: str, workflow: str, ref: str) -> bool:
    """
    调用 GitHub Actions workflow_dispatch 触发器。
    返回 True 表示触发成功（HTTP 204/201/202），否则 False。
    """
    if CONFIG["dry_run"]:
        logging.info(f"Dry-run dispatch to {repo} workflow {workflow} ref {ref}")
        return True
    api = f"https://api.github.com/repos/{repo}/actions/workflows/{workflow}/dispatches"
    payload = {"ref": ref}
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {CONFIG["github_pat"]}",
    }
    try:
        r = requests.post(api, json=payload, headers=headers)
        if r.status_code == 204:
            logging.info(f"Triggered workflow for {repo} ({workflow})")
            return True
        else:
            logging.error(
                f"Failed to trigger workflow for {repo}: {r.status_code} {r.text}"
            )
            return False
    except requests.RequestException as e:
        logging.error(e)
        return False


def check_and_trigger(name: str, repo: str) -> None:
    build_repo = f"wcbing-build/{name}-debs"
    # 检查目标 build 仓库是否存在
    if not repo_exists(build_repo):
        logging.error(f"Build repo not found: {build_repo}")
        return

    releases_tag = latest_releases_tag(repo)
    if not releases_tag:
        logging.error(f"Can't get latest releases tag of {name}")
        return

    local_tag = latest_releases_tag(build_repo)
    if not local_tag:
        logging.error(f"Can't get latest releases tag of {name}")
    logging.info(f"{repo} = {releases_tag}, {build_repo} = {local_tag}")

    # 判断是否需要更新
    if local_tag == releases_tag:
        return
    logging.info(f"Dispatching build for {name} -> {build_repo}")
    if trigger_workflow(build_repo, CONFIG["workflow"], CONFIG["ref"]):
        if local_tag == "":
            print(f"AddNew: {name} -> {releases_tag}")
        else:
            print(f"Update: {name} ({local_tag} -> {releases_tag})")
    else:
        logging.error(f"Failed to dispatch build for {name}")


if __name__ == "__main__":
    CONFIG["github_pat"] = os.environ.get("GITHUB_PAT", "")
    if not CONFIG["github_pat"] and not CONFIG["dry_run"]:
        logging.error(f"No GitHub token found in env GITHUB_PAT.")
        exit(1)

    try:
        with open(os.path.join(CONFIG["data_dir"], "git-repo.json"), "r") as f:
            git_repo_list = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logging.error(e)
        exit(1)

    with ThreadPoolExecutor(max_workers=CONFIG["thread"]) as executor:
        tasks = [
            executor.submit(check_and_trigger, name, repo)
            for name, repo in git_repo_list.items()
        ]
        wait(tasks)
