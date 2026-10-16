# 异世界公会长 / Isekai Guild Master

Godot 客户端发布包与最新 Python 服务端源码。

## 下载

在本仓库的 [Releases](https://github.com/shuiwen879867/isekai-guild-master/releases) 下载：

- `GuildMaster-Godot-Windows-20261015-A077Fix.zip`：Windows Godot 完整修复包，解压后运行 `GuildMaster.exe`。
- `guild-server.zip`：独立服务端部署包。

当前版本为 **3.2.0**，修订号 `20261015-3.2.0-fireworks-replacement`。源码位于 `server/`，与服务端部署包中的运行模块一致。

## A-077 修复

「極彩爆裂砲彈」第一效果按照卡面选择与自己支配区域相邻的非魔王迷宫，不再错误要求邻接据点。替换不要求或消耗可用冒险者；后续探索为可选步骤，仍需满足正常探索条件。Godot 离线模式已内置修复，联机对局需要更新服务端。

此版本同时包含此前的大厅连接、断线房间清理与自定义开局文明/瘴气修复。

## 启动服务端

安装 Python 3.9 或更高版本，然后运行：

```sh
cd server
python server.py --host 0.0.0.0 --port 6677
```

默认游戏端口为 6677，回放网站为 6767，对战器网站为 6680。设置见 `server/server_config.json`，详细部署说明见 [服务端说明](server/README.md)。更新部署时保留已有的 `replays/` 和自定义配置。

## 验证

```sh
cd server
python -m unittest discover -s tests -p test_fireworks_effect.py
python -m unittest discover -s tests -p test_card_audit_fixes.py
```

发布前已通过 76 项相关测试，并验证 Windows 成品包文件清单、包内 Python 规则及服务端部署包启动。发布文件的 SHA-256 见 [release-files.json](release-files.json)。Godot 使用说明见 [docs/GODOT.md](docs/GODOT.md)。
