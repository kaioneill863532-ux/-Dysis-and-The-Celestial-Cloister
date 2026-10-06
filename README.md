# 狄西斯的日落回廊 · Dysis and The Celestial Cloister

一款以行走、观察和空间推理为核心的 3D 解谜游戏：移动的方式决定时间，光本身就是路。

玩家扮演日落女神狄西斯，借日光登上圆殿最高处，用金苹果接住最后一缕阳光；入夜后循着月光穿过水庭，把它送到中心的小亭。

- 设计文档：[docs/game-design.md](docs/game-design.md)
- 重构方案 v0.4（待确认）：[docs/proposal-v0.4.html](docs/proposal-v0.4.html)
- **系统文档 v0.12**（Word，黑字原文、红字补充；给美术和程序）：[docs/系统文档-狄西斯的日落回廊_v0.12.docx](docs/系统文档-狄西斯的日落回廊_v0.12.docx)（旧版：[docs/systems.md](docs/systems.md)）
- **施工图 v0.12**（Blender 建模、UE 搭场景、程序用的尺寸、位置、光路和太阳月亮角度）：[docs/施工图-v0.12.html](docs/施工图-v0.12.html)，PDF：[docs/日落回廊_施工图_v0.12.pdf](docs/日落回廊_施工图_v0.12.pdf)
- **建筑和机关模型 v0.12**（Blender .blend、给 UE 的 FBX、UE 导入并核对的脚本、机关清单、数值核对报告）：[models/temple-v0.12/](models/temple-v0.12/README.md)
- **音效（第一到第四梯队）**：265 个 WAV（48 kHz、16 位，给 UE 直接用），每条怎么做的、UE 里怎么触发，都在 [audio/README.md](audio/README.md)；用浏览器打开 [audio/index.html](audio/index.html) 试听（可以切殿内混响）。真实的 CC0 录音加工而成，`audio/tools/` 里的脚本能全部重新生成
- **UE 交接：日月轨道 + 站在哪里决定几点**（给新开的 Claude Code 会话照做的说明、标准答案、参考实现、UE 里的核对脚本）：[docs/ue-handoff/](docs/ue-handoff/README.md)
- **v0.12 灰盒（神殿）**：[prototype/temple/index.html](prototype/temple/index.html)，说明见 [prototype/README.md](prototype/README.md)
- v0.11 灰盒（对照）：[prototype/temple-v0.11/index.html](prototype/temple-v0.11/index.html)
- v0.10 灰盒（对照）：[prototype/temple-v0.10/index.html](prototype/temple-v0.10/index.html)
- v0.9 灰盒（对照）：[prototype/temple-v0.9/index.html](prototype/temple-v0.9/index.html)
- v0.8 灰盒（对照）：[prototype/temple-v0.8/index.html](prototype/temple-v0.8/index.html)
- v0.7 灰盒（对照）：[prototype/temple-v0.7/index.html](prototype/temple-v0.7/index.html)
- v0.6 灰盒（对照）：[prototype/temple-v0.6/index.html](prototype/temple-v0.6/index.html)
- v0.5 灰盒（对照）：[prototype/temple-v0.5/index.html](prototype/temple-v0.5/index.html)
- v0.4 灰盒（对照）：[prototype/temple-v0.4/index.html](prototype/temple-v0.4/index.html)
- UE 数据册（v0.4 的旧数据，已被上面的施工图 v0.12 取代）：[docs/ue-spec.html](docs/ue-spec.html)，原始数据 [docs/ue-spec.json](docs/ue-spec.json)
- 旧版灰盒（v0.3，日月十关）：[prototype/cloister/index.html](prototype/cloister/index.html)
