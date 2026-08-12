# 黑盒 UI 自动化执行器

这是可迁移的 PC / Android 黑盒自动化执行器：用 YAML 描述用例，负责步骤执行、截图留档、JSON/JUnit 报告和失败后的可配置产物收集。

它不依赖 UE 插件，也不包含任何项目的角色、关卡、UI 图或路径；因此可作为新项目的 UI 冒烟测试起点。

## 支持范围

| 平台 | 定位方式 | 输入方式 | 备注 |
| --- | --- | --- | --- |
| Windows | OpenCV 模板图 | 点击、拖拽、按键、滚轮 | 需要在测试机安装 Windows 可选依赖 |
| Android | `resourceId` / 文本选择器 | 点击、滑动、按键 | 基于 `uiautomator2` 和 adb |

`mouse_down`、`move_pos`、`mouse_up` 是 Windows 专用的低级操作。跨平台用例优先使用 `drag`。

## 快速开始

在 `05_执行与调度_参考实现` 目录执行：

```powershell
python -m pip install -r blackbox_runner/requirements.txt
python -m blackbox_runner.main --help
python -m blackbox_runner.main --platform win --case examples/smoke-template.yaml --assets assets --title "你的游戏窗口标题"
```

把项目截图模板放到 `assets/`，并把示例中的占位符改为真实路径。报告默认写入 `results/<run-id>/`。

如果需要收集项目日志、崩溃目录或录屏缓存，显式提供来源，避免框架猜测任何项目目录：

```powershell
python -m blackbox_runner.main --platform win --case examples/smoke-template.yaml --artifact-source "D:\\Game\\Saved\\Logs" --artifact-source "D:\\Game\\Saved\\Crashes"
```

## 用例规则

- `click` / `tap`：点击一个锚点；Windows 用 `image`，Android 用 `android_uia`。
- `wait_anchor`：等待目标出现，是界面状态断言的基本方式。
- `click_pos`：绝对坐标点击，仅在无法稳定定位时使用。
- `drag`、`scroll`、`press`、`sleep`、`screenshot`：通用操作。
- 每一步都可设置 `retries` 与 `retry_interval_sec`；失败后会保留步骤前后的截图。

项目接入前请先阅读 [`../../docs/黑盒执行器接入说明.md`](../../docs/黑盒执行器接入说明.md)。
