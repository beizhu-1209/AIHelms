# dsh-aihelms-web

AIHelms 的 DSH Web 部署 Bundle。它只负责 AIHelms 适配配置，不修改 DeepSeek Harness 官方源码。

`cordis.patch.yml` 配置 Web server 的监听地址、端口和 trusted host。`Dockerfile` 是固定的 runtime 构建模板。

发布时把插件打包为固定文件：

```text
deepseek-harness/deploy/aihelms/dsh-home/profiles/web/dsh-aihelms-web.tgz
```

Web profile 必须使用 `file:dsh-aihelms-web.tgz`，不能出现构建服务器的 `link:/...` 或 `file:/...` 绝对路径。Dockerfile 会检查这个约束，路径错误时直接停止构建。

完整操作见 `docs/INTERNAL.md` 的“DS Harness 开发流程”。
