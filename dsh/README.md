# DS Harness 集成

`dsh/manager/` 是 AIHelms 侧的控制面，负责用户 DSH 容器的创建、复用、代理和回收。

`dsh/Dockerfile` 只构建 `dsh-manager`，不是 DeepSeek DSH runtime 的 Dockerfile。DSH runtime 源码在独立的 DSH 定制项目中维护。

开发、构建和人工验收流程见 `docs/INTERNAL.md` 的“DS Harness 开发流程”。
