# 狄西斯的日月回廊 · Dysis and The Celestial Cloister

一款以行走、观察和空间推理为核心的 3D 解谜游戏：移动的方式决定时间，光本身就是路。

玩家扮演日落女神狄西斯，借日光登上圆殿最高处，用金苹果接住最后一缕阳光；入夜后循着月光穿过水庭，把它送到中心的小亭。

- 设计文档：[docs/game-design.md](docs/game-design.md)
- 美术资产清单（场景、角色、道具、机关）：[docs/systems.md](docs/systems.md)
- 可玩的灰盒原型（日月十关）：[prototype/cloister/index.html](prototype/cloister/index.html)，说明见 [prototype/README.md](prototype/README.md)

## 新圆殿试玩与进度

重构版见 [`prototype/rotunda/`](prototype/rotunda/)；旧版 `prototype/cloister/` 保持原样。可以直接打开 [`prototype/rotunda/play.html`](prototype/rotunda/play.html) 试玩离线单文件，也可以在仓库根目录运行 `npm ci && npm run serve`，访问 `http://localhost:4173/prototype/rotunda/index.html`。

公开预览使用独立地址：[`preview/rotunda/`](https://kaioneill863532-ux.github.io/-Dysis-and-The-Celestial-Cloister/preview/rotunda/index.html)。

这是供关卡、建筑与光路验证的浏览器原型，不是 Unreal Engine 工程。当前验证的证据、局限和操作键位在 [`docs/rotunda-playtest.md`](docs/rotunda-playtest.md)。
