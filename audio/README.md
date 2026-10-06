# 音效 · 第一到第四梯队

日落回廊的音效：第一梯队里除了 1、2、7、12、13（时间和声、接光主题、主界面音乐、结局音乐，之后单独做）以外的全部，第二梯队全部（14–30），第三、四梯队除了 34（岛影逼近）、51（碎片放入凹槽：现在结局自动检测）和 58（对话配音）以外的全部。
共 50 条、267 个文件。**试听：用浏览器打开 [index.html](index.html)**（按编号分组，可以切“殿内混响”听放进圆殿以后的样子）。

## 怎么做的

**要真实**，所以能用真实录音的地方都用真实录音：56 段 Freesound 上的 CC0 录音（凉鞋、石地面、石板门、铁链、铜钵、水晶杯、瀑布、海浪……，出处在最后），切、降调、叠层、滤波、对齐响度。
光、月光这些“现实里不发声”的东西，也用真实的材料来发声：

- **日光 = 玻璃**：摩擦的水晶杯（有真实的颤动）、玻璃轻碰的闪光、被照亮的水雾（瀑布录音里最高的那一段）。
- **月光 = 铜钵**：敲击、摩擦的颂钵，比日光低、冷；月石显形混一点石头的细砂，隐去混真实的流沙。
- **石头机关 = 真实的石板门摩擦**，降几个半音（越重降得越多），底下垫一层很低的隆隆声；落定用真实的石头重击。
- **会“发音”的石头和青铜**（升起的台阶、桥门、铜托）用模态合成：按真实物体的振动比例（两端自由的石条 1 : 2.76 : 5.40 : 8.93、厚铜盘）合成，再用真实的碰撞声去激发，所以起音还是真的。

**音高**：所有有音高的声音都在 d 小调五声（D F G A C）里，这几个音都在灰盒现有的时间和弦里（`CHORDS`），以后做时间和声时不会打架。
日光的音在 D5–D6，月光在 A3–A4，屋顶 16 级台阶从 D3 一级级升到 D6。

## 格式和用法（UE）

- 48 kHz、16 位 WAV，直接拖进 UE。**干声**（没有混响）：殿内的空间感交给 Audio Volume 的混响，或者用 [ir/IR_Temple_Rotunda.wav](ir/IR_Temple_Rotunda.wav)
  建一个 Convolution Reverb（合成的石头圆殿脉冲响应：早期反射按半径约 15 m 的圆墙，低频 4.2 s、高频 1.6 s 的尾巴）。
- 点声源（脚步、机关、月石……）是**单声道**，开 Spatialization；环境床（海浪、瀑布）、界面、几条要有宽度的（光路显形、光圈、月桥……）是**立体声**。
- **响度已经对齐过**，彼此之间的大小就是想要的混音比例，UE 里音量都先放 1.0 再微调：
  脚步 −28 LUFS（快走 −26），光路显形 −25，机关 −18 到 −21，界面 −25 到 −32；循环按整段响度：瀑布近 −21、海浪近 −22、远的更低。峰值都在 −1 dBFS 以下。
- 名字里带 `_Loop` 的是首尾无缝的循环，在 Sound Wave 上勾 Looping。
- 同一组有好几个文件的（`_01`、`_02`……）用 Sound Cue 的 Random 节点（勾“不重复”）。

## 每一条


### 3. 脚步：石头/大理石（第一梯队）

**怎么做的**：皮凉鞋踩在大理石上。领头的是真实的大理石地面上脚掌落地的那一下（ragamuffin 的录音，软、圆），4 毫秒后是凉鞋轻轻一拍（Vrymaa、ftpalad 的录音里只挑不尖、不刺的），最下面垫一点真实的石地面脚步的“实”（SecureSubset，去掉最低的一截、很短）。第二版按试听反馈改轻、改软：比第一版刺耳的 2.5–6 kHz 少 3.6 dB、起音软了约 10 dB、250 Hz 以下少 4 dB。走 10 个、快走 8 个、蹭地 4 个，响度都对齐。

**UE 里怎么用**：Sound Cue：Random（不重复）→ Modulator（音高 0.96–1.04，音量 0.9–1.0）。每次脚落地（动画通知或按步长）触发；Shift 快走用 Run 那一组。干声交付，殿内的混响交给 Audio Volume / 卷积混响（见 ir/）。

| 用途 | 文件 | 时长 | 声道 |
|---|---|---|---|
| 走 | `SFX_Footstep_Stone_Walk_01` … `10`（10 个） | 0.19–0.20 s | 单 |
| 快走 | `SFX_Footstep_Stone_Run_01` … `08`（8 个） | 0.19–0.20 s | 单 |
| 蹭地 | `SFX_Footstep_Stone_Scuff_01` … `04`（4 个） | 0.41–0.48 s | 单 |

文件夹：[sfx/03_Footstep_Stone/](sfx/03_Footstep_Stone/)

### 4. 脚步：光路（第一梯队）

**怎么做的**：脚下是光：和石头脚步同一个“接触”（脚掌落地 + 轻轻的凉鞋，第二版一起改软了），去掉石头的“实”（低频全拿掉，光没有分量），每一步激起一点水晶的余振——模态合成负责干净的起音，真实的摩擦水晶杯录音（PappaBert）负责有颤动的身体，音高在 d 小调五声里随机取（D5–D6），很轻、半秒就收住，走很久也不吵。

**UE 里怎么用**：和石头脚步同一套触发；脚下是光路（Zone 以 beam: 开头、月石、虹桥、影桥另有材质）时换这一组。Random 不重复，音高不要再随机（已经按音阶取好）。

| 用途 | 文件 | 时长 | 声道 |
|---|---|---|---|
| 走 | `SFX_Footstep_Light_Walk_01` … `10`（10 个） | 0.35–0.40 s | 单 |
| 快走 | `SFX_Footstep_Light_Run_01` … `06`（6 个） | 0.29–0.33 s | 单 |

文件夹：[sfx/04_Footstep_LightPath/](sfx/04_Footstep_LightPath/)

### 5. 光路显形（第一梯队）

**怎么做的**：一束光出现、可以走了。两只真实的摩擦水晶杯（变到 d 小调五声的四度、五度）慢慢起来，一点被照亮的水雾（瀑布录音最高的那一段），几颗很轻的玻璃闪光（jhumbucker 的玻璃轻碰）。没有敲击、没有尖的起音，2.4 秒左右收住；六个音高组合轮着用，听几十次也不腻。

**UE 里怎么用**：光路的可走状态从 false 变 true 时，在光束的中点（或玩家能看到的那一头）播放；6 个文件 Random 不重复。同一时间多束光一起出现只播一个。立体声，Spatialization 开、Spread 适中。

| 用途 | 文件 | 时长 | 声道 |
|---|---|---|---|
| 显形 | `SFX_LightPath_Reveal_01` … `06`（6 个） | 2.50–2.50 s | 立体 |

文件夹：[sfx/05_LightPath_Reveal/](sfx/05_LightPath_Reveal/)

### 6. 月石显形、隐去（第一梯队）

**怎么做的**：月光照到的石头：显形是一只真实颂钵（Coleco 的敲击录音）把木槌的硬起音抹软，变到月光的低音区，下面垫同一音高的摩擦颂钵（ryancacophony）和一点石头的细砂；隐去是摩擦颂钵的长音一边淡出一边往下沉一点点，混着真实的沙子流下的细声（nicoproson），像石头化成月光的尘。另有一个大号的“墙隐去”（月亮浮雕、双子厚墙、月之龛那几块大月石共用）。

**UE 里怎么用**：Appear：月石的 k 从 0 往 1 走时触发（只在开始那一下）；Vanish：从 1 往 0 走时触发。音高已经分开，Random 不重复即可。Wall_Vanish 给一次性隐去的大块月石。单声道，放在月石的中心。

| 用途 | 文件 | 时长 | 声道 |
|---|---|---|---|
| 显形 | `SFX_Moonstone_Appear_01` … `04`（4 个） | 1.60–1.63 s | 单 |
| 隐去 | `SFX_Moonstone_Vanish_01` … `03`（3 个） | 2.20–2.20 s | 单 |
| 大块隐去 | [`SFX_Moonstone_Wall_Vanish`](sfx/06_Moonstone/SFX_Moonstone_Wall_Vanish.wav) | 3.65 s | 单 |

文件夹：[sfx/06_Moonstone/](sfx/06_Moonstone/)

### 8. 跳跃、落地（第一梯队）

**怎么做的**：起跳：凉鞋在石面上一蹬（真实的蹭地脚步）+ 长袍带起的一下衣料风声（saturdaysoundguy、Nox_Sound 的衣服挥动录音）。落地：两只脚前后差 15–30 毫秒落下，石地面的“实”比走路重一点，最后衣料落定一下。另有落在光上的版本：没有石头的重量，脚下一声水晶。第二版跟着脚步一起改轻、改软，起跳里刺耳的那一段也收了一点。

**UE 里怎么用**：Jump：起跳那一帧；Land_Stone：落到石头/青铜上（青铜落地见 28）；Land_Light：落到光路、月石上。下落时间长于 0.6 秒的落地可以把音量提高 2–3 dB。

| 用途 | 文件 | 时长 | 声道 |
|---|---|---|---|
| 起跳 | `SFX_Jump_01` … `04`（4 个） | 0.47–0.52 s | 单 |
| 落地·石头 | `SFX_Land_Stone_01` … `04`（4 个） | 0.21–0.48 s | 单 |
| 落地·光 | `SFX_Land_Light_01` … `03`（3 个） | 0.51–0.57 s | 单 |

文件夹：[sfx/08_Jump_Land/](sfx/08_Jump_Land/)

### 9. 掉落、回到落脚点（第一梯队）

**怎么做的**：掉落：耳边的风越来越大（粉噪做的湍流风，中心频率和响度一直在抖），加上长袍被风吹着抖动；有一个起头（1.6 秒，风从无到大）和一个可以一直循环的风。回到落脚点：不惩罚——光像吸一口气一样聚回来（水晶杯音倒着长出来），落在一个温暖的五度上，最后一声很轻的落脚。日、夜各一个。

**UE 里怎么用**：Fall_Start：离开地面、下落速度超过阈值时播；接着播 Fall_Loop（Looping），回到落脚点时 0.15 秒淡出。Respawn_Day / Respawn_Night：人重新出现在落脚点的那一刻（白天用日光的，入夜以后用月光的）。

| 用途 | 文件 | 时长 | 声道 |
|---|---|---|---|
| 掉落 | [`SFX_Fall_Start`](sfx/09_Fall_Respawn/SFX_Fall_Start.wav) | 1.80 s | 立体 |
| 掉落·循环 | [`SFX_Fall_Loop`](sfx/09_Fall_Respawn/SFX_Fall_Loop.wav)（循环） | 5.50 s | 立体 |
| 回到落脚点 | [`SFX_Respawn_Day`](sfx/09_Fall_Respawn/SFX_Respawn_Day.wav) | 2.10 s | 立体 |
| 回到落脚点 | [`SFX_Respawn_Night`](sfx/09_Fall_Respawn/SFX_Respawn_Night.wav) | 2.10 s | 立体 |

文件夹：[sfx/09_Fall_Respawn/](sfx/09_Fall_Respawn/)

### 10. 瀑布（第一梯队）

**怎么做的**：从天花板一直泻进水庭的厚瀑布。近处：一段很稳的真实大瀑布（saralana，258 秒的录音里挑最匀的一段）打底，叠一层真实的小瀑布近距离的水花（Nox_Sound），低频稍微加厚（落差 30 米）；远处：同一瀑布滤到只剩低沉的轰鸣，窄一点，给殿里别的楼层。都是无缝循环。

**UE 里怎么用**：两层都 Looping，放在瀑布中心：Near 的衰减半径约 6–25 m，Far 约 15–60 m，两层叠着用。水闸打开以前两层都停；开闸时先播 14 的 Waterfall_Start，它的结尾直接接上这两条循环。

| 用途 | 文件 | 时长 | 声道 |
|---|---|---|---|
| 近 | [`SFX_Waterfall_Near_Loop`](sfx/10_Waterfall/SFX_Waterfall_Near_Loop.wav)（循环） | 12.00 s | 立体 |
| 远 | [`SFX_Waterfall_Far_Loop`](sfx/10_Waterfall/SFX_Waterfall_Far_Loop.wav)（循环） | 12.00 s | 立体 |

文件夹：[sfx/10_Waterfall/](sfx/10_Waterfall/)

### 11. 海浪（第一梯队）

**怎么做的**：开场第一声。近处（岛上、海面高度）：真实的浪拍礁石（dan.pugsley，一个个浪的起落很清楚）；远处（台地、殿外回廊、殿里）：真实的“从崖上听海”（bruno.auzet），本来就是在悬崖上录的，再滤掉一点高频。都是无缝循环。

**UE 里怎么用**：Close：放在岛的外沿和崖脚，衰减半径约 10–40 m；Far：2D 或者放大半径（80 m 以上），殿外一直在，进殿以后用 Audio Volume 压低 8–12 dB、再低通到 800 Hz 左右。

| 用途 | 文件 | 时长 | 声道 |
|---|---|---|---|
| 近 | [`SFX_Sea_Waves_Close_Loop`](sfx/11_Sea_Waves/SFX_Sea_Waves_Close_Loop.wav)（循环） | 30.00 s | 立体 |
| 远 | [`SFX_Sea_Waves_Far_Loop`](sfx/11_Sea_Waves/SFX_Sea_Waves_Far_Loop.wav)（循环） | 30.00 s | 立体 |

文件夹：[sfx/11_Sea_Waves/](sfx/11_Sea_Waves/)

### 14. 水闸轮转动、瀑布开始流（第二梯队）

**怎么做的**：第一个机关。闸轮：真实的木轮转动（KVV_Audio）降调成大轮子，加上绞盘棘爪一格一格的咔哒（kyles 的滑轮绞盘），轴上很低的一声呻吟，最后石闸被拉开时“咚”地到位。瀑布开始流：先是一股水冲出来（HonorHunter 的水涌），再是从 30 米高处稀稀拉拉砸进水池的水（Breviceps 的倒水），然后真正的瀑布从低沉的闷响打开成整片的轰鸣（低通一路扫开），最后一秒和 10 的 Near 循环开头完全一样，能直接接上。另附一个关水闸、瀑布停下的版本。

**UE 里怎么用**：玩家按 E 开水闸：播 Sluice_Wheel_Turn（2.6 s）；它播到 2.2 s 左右（闸到位那一下）开始播 Waterfall_Start，Waterfall_Start 的最后 1 秒是等功率淡出：它播到 4.0 s 时启动 10 的 Near/Far 两条循环，Fade In 1 s、曲线选 Sin（Equal Power）。关水闸：Waterfall_Stop 开头 1 秒是等功率淡入，播它的同时让两条循环 Fade Out 1 s（同样的曲线）。

| 用途 | 文件 | 时长 | 声道 |
|---|---|---|---|
| 闸轮 | [`SFX_Sluice_Wheel_Turn`](sfx/14_Sluice_Waterfall_Start/SFX_Sluice_Wheel_Turn.wav) | 2.90 s | 单 |
| 瀑布开始流 | [`SFX_Waterfall_Start`](sfx/14_Sluice_Waterfall_Start/SFX_Waterfall_Start.wav) | 5.00 s | 立体 |
| 瀑布停下 | [`SFX_Waterfall_Stop`](sfx/14_Sluice_Waterfall_Start/SFX_Waterfall_Stop.wav) | 4.00 s | 立体 |

文件夹：[sfx/14_Sluice_Waterfall_Start/](sfx/14_Sluice_Waterfall_Start/)

### 15. 台阶升起、落平（第二梯队）

**怎么做的**：屋顶环道的 16 级踏步。每一级到位时是一声“石磬”：调过音的石条（两端自由的石条的真实振动比例 1 : 2.76 : 5.40 : 8.93），用真实的石头碰撞激发，16 级按 d 小调五声从 D3 一路升到 D6——音高逐级变高，本身就是“快到了”的反馈；每级还带一点铜叶片擦过的亮声（光圈叶片跟着升起来）。落平是同一个音低八度、更闷、更轻。另有一条踏步移动时的石头摩擦循环。

**UE 里怎么用**：Rise_XX：第 XX 级升到顶（停住）那一刻播，单声道放在那一级上。Settle_XX：入夜后第 XX 级落平到底时播。Move_Loop：只要有踏步在动就循环播放，音量跟踏步的移动速度走（0 → 停）。

| 用途 | 文件 | 时长 | 声道 |
|---|---|---|---|
| 升起 | `SFX_Steps_Rise_01` … `16`（16 个） | 0.89–0.93 s | 单 |
| 落平 | `SFX_Steps_Settle_01` … `16`（16 个） | 0.89–0.96 s | 单 |
| 移动·循环 | [`SFX_Steps_Move_Loop`](sfx/15_Steps_Rise_Settle/SFX_Steps_Move_Loop.wav)（循环） | 5.50 s | 单 |

文件夹：[sfx/15_Steps_Rise_Settle/](sfx/15_Steps_Rise_Settle/)

### 16. 拉机关 A/B、石板滑动（第二梯队）

**怎么做的**：拉杆：手握铜把手、轴上一声短的呻吟、铜链“一紧”（LePainMaudit 的重铁链）、扳到底“咔”地卡住（Alexbuk 的门闩）。拉下和推回用不同的素材段和顺序。石板滑动：一块大石板贴着外墙在滑轨上滑开 1.6 秒（真实的墓门石头摩擦，降调），起步一顿、到位一声闷响；两个版本给两块石板。

**UE 里怎么用**：A、B 两个机关现在合成了同一个拉杆：拉下播 Lever_Pull，推回播 Lever_Push，放在拉杆上。Slab_Slide_01/02：两块石板各自开始滑的时候在石板上播（离得远，靠 UE 的衰减和混响就有“远处传来”的感觉）。

| 用途 | 文件 | 时长 | 声道 |
|---|---|---|---|
| 拉杆 | [`SFX_Lever_Pull`](sfx/16_Lever_StoneSlab/SFX_Lever_Pull.wav) | 1.70 s | 单 |
| 拉杆 | [`SFX_Lever_Push`](sfx/16_Lever_StoneSlab/SFX_Lever_Push.wav) | 1.70 s | 单 |
| 石板滑动 | [`SFX_Slab_Slide_01`](sfx/16_Lever_StoneSlab/SFX_Slab_Slide_01.wav) | 2.40 s | 单 |
| 石板滑动 | [`SFX_Slab_Slide_02`](sfx/16_Lever_StoneSlab/SFX_Slab_Slide_02.wav) | 2.40 s | 单 |

文件夹：[sfx/16_Lever_StoneSlab/](sfx/16_Lever_StoneSlab/)

### 17. 光圈叶片旋开（第二梯队）

**怎么做的**：天花板上的光圈一片片旋开。第二版按试听反馈（第一版的金属叶片太像磨刀）整个换成 16 的石板滑动：几块石板一样的叶片先后滑开，每块都是真实的墓门石头摩擦（降调）、起步轻轻一顿，前面几片落定得轻，最后一片“咚”地到位；声像在头顶走半圈。合拢是反方向走、最后一声更沉。还有一条只有摩擦、没有落定的循环，给开合时间不固定的时候用。不再有任何金属摩擦和铜的和弦。

**UE 里怎么用**：Iris_Open / Iris_Close：开、合的完整版（约 4 s，最后一片在 3.4 s 左右落定）。光圈半径跟着玩家的位置慢慢变时（日4 走圆眼光柱），改用 Iris_Move_Loop，音量跟半径的变化速度走，停下时停循环（要的话补一个 16 的 Slab_Slide 的最后 0.8 秒当落定）。立体声，放在圆眼中心（头顶）。

| 用途 | 文件 | 时长 | 声道 |
|---|---|---|---|
| 开合 | [`SFX_Iris_Open`](sfx/17_Iris_Blades/SFX_Iris_Open.wav) | 4.20 s | 立体 |
| 开合 | [`SFX_Iris_Close`](sfx/17_Iris_Blades/SFX_Iris_Close.wav) | 4.20 s | 立体 |
| 滑动·循环 | [`SFX_Iris_Move_Loop`](sfx/17_Iris_Blades/SFX_Iris_Move_Loop.wav)（循环） | 4.70 s | 立体 |

文件夹：[sfx/17_Iris_Blades/](sfx/17_Iris_Blades/)

### 18. 桥门开、关（第二梯队）

**怎么做的**：屋顶细桥尽头的桥门绕门柱转 1.4 秒。第二版按试听反馈（桥门以后不一定是青铜）改用 16 的拉杆声音：开门是“拉下”那一套、关门是“推回”那一套，轴上的呻吟拉长到门转的时间，扳到底“咔”地卡住那一下挪到门转完的时刻（1.37 s）。去掉了第一版里青铜门的共振和铁门的撞击。

**UE 里怎么用**：Gate_Open：人走近桥尾、门开始转时播；Gate_Close：接住最后一缕光、门开始转回去时播。卡住那一下都在 1.37 s。单声道，放在门轴上。

| 用途 | 文件 | 时长 | 声道 |
|---|---|---|---|
| 开 | [`SFX_Gate_Open`](sfx/18_Bridge_Gate/SFX_Gate_Open.wav) | 2.10 s | 单 |
| 关 | [`SFX_Gate_Close`](sfx/18_Bridge_Gate/SFX_Gate_Close.wav) | 2.10 s | 单 |

文件夹：[sfx/18_Bridge_Gate/](sfx/18_Bridge_Gate/)

### 19. 转动雕像底座（第二梯队）

**怎么做的**：转一格：石像在石台座上转（真实的石板门摩擦，降调），旁边的绞盘咔哒咔哒（轮子转像的两倍：kyles 的绞盘棘爪），到格时石头卡位“咔”一声（xtra1 的石头碰石头，降调）。4 个版本轮着用。三相像（54° 一格，0.6 s）和天鹅（45° 一格，0.5 s）都用它。

**UE 里怎么用**：玩家按一次 E、像开始转向下一格时播；Random 不重复，音高 0.97–1.03。单声道，放在台座上。卡位那一下在 0.6 s；天鹅转得快一点，可以把音高调到 1.08。

| 用途 | 文件 | 时长 | 声道 |
|---|---|---|---|
| 转一格 | `SFX_Statue_Turn_01` … `04`（4 个） | 1.17–1.17 s | 单 |

文件夹：[sfx/19_Statue_Turn/](sfx/19_Statue_Turn/)

### 20. 塞勒涅怀里的月相持续音（第二梯队）

**怎么做的**：月5 唯一“找位置”的反馈。两层可以无缝循环的长音：Low 是一只真实的摩擦颂钵（hollandm 127 秒的长录音，变到 D4，下面叠低五度的 G3），一直都在、很轻；High 是两只摩擦水晶杯（A5、D6）加一点闪光，月光罩住月亮越多它越响。站满 1 秒时播 Lock：一声软的颂钵 + 往上收的水晶，接 25 的“亮起来”。

**UE 里怎么用**：人在月桥上、夜里时，Low、High 两条循环都在播（放在女神怀里的月亮上）：Low 音量 = 0.25 + 0.5 × sweep（被月光扫到的比例），High 音量 = lit（月光罩住月亮的比例，0–1），可以再把 High 的音高随 lit 从 0.985 推到 1.0（“对准”的感觉）。dwell 到 1 秒时播 Lock，两条循环 1 秒淡出。

| 用途 | 文件 | 时长 | 声道 |
|---|---|---|---|
| 低层·循环 | [`SFX_Selene_MoonDrone_Low_Loop`](sfx/20_Selene_MoonPhase/SFX_Selene_MoonDrone_Low_Loop.wav)（循环） | 7.00 s | 立体 |
| 高层·循环 | [`SFX_Selene_MoonDrone_High_Loop`](sfx/20_Selene_MoonPhase/SFX_Selene_MoonDrone_High_Loop.wav)（循环） | 7.00 s | 立体 |
| 对准 | [`SFX_Selene_MoonDrone_Lock`](sfx/20_Selene_MoonPhase/SFX_Selene_MoonDrone_Lock.wav) | 2.60 s | 立体 |

文件夹：[sfx/20_Selene_MoonPhase/](sfx/20_Selene_MoonPhase/)

### 21. 推动、拉出雕像（第二梯队）

**怎么做的**：拉出波吕丢刻斯：石像先“咔”地松动（石头碰撞降调），再从龛里被拖出来 1.6 秒（真实的重石板门摩擦，降 4 个半音），到位一声闷响。推：一条可以无缝循环的重石头拖地声（两段真实的石头摩擦叠起来，降 5 个半音，加一层隆隆声），配一个起步和一个停下。

**UE 里怎么用**：PullOut：拉出来时播（1.6 s 的动画）。推的时候：玩家推得动（v > 0.3）就播 Push_Start 再接 Push_Loop（Looping），音量和音高跟推的速度走（音高 0.9–1.05）；停下或推到卡斯托耳身边时停循环、播 Push_Stop。单声道，跟着雕像走。

| 用途 | 文件 | 时长 | 声道 |
|---|---|---|---|
| 拉出 | [`SFX_Statue_PullOut`](sfx/21_Statue_Push_Pull/SFX_Statue_PullOut.wav) | 2.50 s | 单 |
| 推·循环 | [`SFX_Statue_Push_Loop`](sfx/21_Statue_Push_Pull/SFX_Statue_Push_Loop.wav)（循环） | 5.00 s | 单 |
| 推·起步 | [`SFX_Statue_Push_Start`](sfx/21_Statue_Push_Pull/SFX_Statue_Push_Start.wav) | 0.62 s | 单 |
| 推·停下 | [`SFX_Statue_Push_Stop`](sfx/21_Statue_Push_Pull/SFX_Statue_Push_Stop.wav) | 0.77 s | 单 |

文件夹：[sfx/21_Statue_Push_Pull/](sfx/21_Statue_Push_Pull/)

### 22. 双子亮起、月桥伸出（第二梯队）

**怎么做的**：双子并肩、一起亮：两只真实颂钵各一声（D4 和 A4，一人一个音，合起来是五度），木槌的硬起音抹掉，再各自长出摩擦颂钵的长音，像两尊像一起“醒”。月桥伸出：一道圆弧的月石从他们脚下铺到水庭东边——一串月石显形音沿着弧线从左铺到右、音一级级往上，下面是摩擦颂钵的长音和一点石头的细砂，最后落在 D 上。

**UE 里怎么用**：Twins_Light：两尊像同时亮起的那一刻，放在两尊像中间。MoonBridge_Extend：紧接着播，立体声，放在月桥中点（或者跟着桥头的显形前沿移动）。

| 用途 | 文件 | 时长 | 声道 |
|---|---|---|---|
| 双子亮起 | [`SFX_Twins_Light`](sfx/22_Twins_MoonBridge/SFX_Twins_Light.wav) | 3.29 s | 立体 |
| 月桥伸出 | [`SFX_MoonBridge_Extend`](sfx/22_Twins_MoonBridge/SFX_MoonBridge_Extend.wav) | 4.00 s | 立体 |

文件夹：[sfx/22_Twins_MoonBridge/](sfx/22_Twins_MoonBridge/)

### 23. 天鹅浮雕下沉（第二梯队）

**怎么做的**：整面浮雕连同后面的墙往下沉 3 米、2.6 秒：真实的重石板门摩擦降 6 个半音（墙很重），再叠一层真实的重石门打开的摩擦，底下隆隆的振动，缝里落下的细沙（nicoproson 的沙子），2.6 秒时沉到底“咚”地落定（大石门合上的低频），最后一点尘土。

**UE 里怎么用**：天鹅解开、浮雕开始下沉时播，单声道，放在浮雕中心。

| 用途 | 文件 | 时长 | 声道 |
|---|---|---|---|
| 下沉 | [`SFX_SwanRelief_Sink`](sfx/23_SwanRelief_Sink/SFX_SwanRelief_Sink.wav) | 4.20 s | 单 |

文件夹：[sfx/23_SwanRelief_Sink/](sfx/23_SwanRelief_Sink/)

### 24. 楼梯降下（第二梯队）

**怎么做的**：接住最后一缕光、回到桥头以后，另外半圈踏步一级接一级降成楼梯：12 块石头先后往下一沉、各自“咚”地落定（vestibule-door 的石面重击和石头落地，降调），从桥头沿着弧线一路过去（声像从右到左），间隔先快后慢，底下是整段的隆隆声。按试听反馈，单级的版本去掉了，只用整段；另外用同一套做法给墙里的两段楼梯显现各做了一段：窗里堵着的石块从上往下一块块被推出去，接着下门的封石沉下去、最后落定，比屋顶那段短、闷一点（在墙里面）。

**UE 里怎么用**：Stairs_Lower：楼梯开始降的那一刻播一次，立体声，放在楼梯中段。WallStairs_Reveal_TS：月2 天鹅解开、TS 楼梯上门打开时播（3 扇窗）；WallStairs_Reveal_TR：月3 月亮浮雕隐去、TR 楼梯上门打开时播（2 扇窗）。都放在那段楼梯的中段。

| 用途 | 文件 | 时长 | 声道 |
|---|---|---|---|
| 整段 | [`SFX_Stairs_Lower`](sfx/24_Stairs_Lower/SFX_Stairs_Lower.wav) | 5.00 s | 立体 |
| 墙里楼梯显现 | [`SFX_WallStairs_Reveal_TS`](sfx/24_Stairs_Lower/SFX_WallStairs_Reveal_TS.wav) | 3.40 s | 立体 |
| 墙里楼梯显现 | [`SFX_WallStairs_Reveal_TR`](sfx/24_Stairs_Lower/SFX_WallStairs_Reveal_TR.wav) | 3.40 s | 立体 |

文件夹：[sfx/24_Stairs_Lower/](sfx/24_Stairs_Lower/)

### 25. 塞勒涅神像亮起、半桥伸出（第二梯队）

**怎么做的**：月光整个落进她怀里的月亮：低音区一声很深的颂钵（D3），20 的长音在这里“解决”——摩擦颂钵 D4、A4 一起长起来，最上面是水晶杯的 D6，像整座雕像慢慢亮透。半桥：一段石桥从池沿沿半径伸向水亭（2 秒，比雕像轻的石头摩擦），桥头搅动水面（真实的浪拍礁石里最轻的一段），到头轻轻一顿；按试听反馈比第一版轻了 4 dB、最低的隆隆声也去掉了一点。

**UE 里怎么用**：Selene_Awaken：dwell 满 1 秒、她亮起来时播（接在 20 的 Lock 后面），放在雕像上。HalfBridge_Extend：半桥开始伸出时播，放在池沿的桥头。

| 用途 | 文件 | 时长 | 声道 |
|---|---|---|---|
| 神像亮起 | [`SFX_Selene_Awaken`](sfx/25_Selene_Awaken_HalfBridge/SFX_Selene_Awaken.wav) | 4.90 s | 立体 |
| 半桥伸出 | [`SFX_HalfBridge_Extend`](sfx/25_Selene_Awaken_HalfBridge/SFX_HalfBridge_Extend.wav) | 3.00 s | 单 |

文件夹：[sfx/25_Selene_Awaken_HalfBridge/](sfx/25_Selene_Awaken_HalfBridge/)

### 26. 影桥接上（第二梯队）

**怎么做的**：屋顶细桥的月影在水面上挪过来，正好接上半桥的尽头、亮起来。水面轻轻的波光声（真实的浪拍礁石里最轻的一段，只留中高频），一对摩擦颂钵和水晶杯从差一点点（低 30 音分）滑到正好对上——“对齐了”——然后一起亮开。

**UE 里怎么用**：影桥 on 从 0 往 1 走时播一次（1.4 s 内接上），立体声，放在影桥中点。

| 用途 | 文件 | 时长 | 声道 |
|---|---|---|---|
| 接上 | [`SFX_ShadowBridge_Join`](sfx/26_ShadowBridge_Join/SFX_ShadowBridge_Join.wav) | 3.60 s | 立体 |

文件夹：[sfx/26_ShadowBridge_Join/](sfx/26_ShadowBridge_Join/)

### 27. 放上金苹果、取下金苹果（第二梯队）

**怎么做的**：放上（结局动作）：金苹果轻轻落进浑天仪的铜托：一声软的金属碰金属（HenKonen 的金属轻碰，低通抹软），铜托本身“嗡”一下（铜盘的真实振动比例）；接着苹果从金色变成月白、光一点点亮起来（0.5–3 秒）：颂钵 D4、水晶杯 A5 和 D6 慢慢长起来，最后停在一个很安静的 D 上。取下（第二版新加）：在屋顶的浑天仪上把发光的金苹果拿起来、接住最后一缕阳光。是“放上”的反面：同一下金属轻碰更轻、更低（金苹果离开铜托），铜托空了“嗡”一下，然后是暖的日光——水晶杯 D5、A5 很快亮起来再慢慢收住，几颗闪光；不到 3 秒，给以后的接光主题（7）留出位置。

**UE 里怎么用**：Apple_Place：放上苹果那一刻播，放在小亭的浑天仪上；结局音乐（13）最好在 3 秒以后进来。Apple_Take：在屋顶浑天仪前按 E“取下金苹果”（灰盒 catchLight）那一刻播，放在浑天仪上；接光主题（7）做好以后可以在 0.3 s 左右叠进来。

| 用途 | 文件 | 时长 | 声道 |
|---|---|---|---|
| 放上 | [`SFX_Apple_Place`](sfx/27_Apple_Place/SFX_Apple_Place.wav) | 6.00 s | 立体 |
| 取下 | [`SFX_Apple_Take`](sfx/27_Apple_Place/SFX_Apple_Take.wav) | 2.90 s | 立体 |

文件夹：[sfx/27_Apple_Place/](sfx/27_Apple_Place/)

### 28. 脚步：青铜（第二梯队）

**怎么做的**：凉鞋踩在厚青铜板上（环道、细桥、半桥）：和石头脚步同一个“接触”，下面的“实”换成青铜——厚铜板的真实振动比例做的短共振（不是薄铁皮那种空响），叠一点真实的金属地面脚步（nate_asdfg、gristi 的录音，低通）。第二版跟着脚步改软，铜板的音往上挪、最低的一截拿掉（250 Hz 以下少 7 dB）。走 8 个、快走 6 个、落地 2 个。

**UE 里怎么用**：和石头脚步同一套触发，脚下是青铜（Physical Material = Bronze）时换这一组。

| 用途 | 文件 | 时长 | 声道 |
|---|---|---|---|
| 走 | `SFX_Footstep_Bronze_Walk_01` … `08`（8 个） | 0.32–0.34 s | 单 |
| 快走 | `SFX_Footstep_Bronze_Run_01` … `06`（6 个） | 0.26–0.33 s | 单 |
| 落地 | [`SFX_Land_Bronze_01`](sfx/28_Footstep_Bronze/SFX_Land_Bronze_01.wav) | 0.33 s | 单 |
| 落地 | [`SFX_Land_Bronze_02`](sfx/28_Footstep_Bronze/SFX_Land_Bronze_02.wav) | 0.34 s | 单 |

文件夹：[sfx/28_Footstep_Bronze/](sfx/28_Footstep_Bronze/)

### 29. 界面：按钮悬停、确认、返回，开始游戏（第二梯队）

**怎么做的**：界面也用游戏里的材料：悬停是一把小锤在石头上轻轻一点（Shamewap 的录音，很短、很轻）；确认是一只小铜钵敲一下（FOSSarts），0.8 秒收住；返回是同一只钵、更低更闷、更短；开始游戏的第一声就是“确认”那一下（让它多响一会儿），接着水晶杯 D、A 慢慢亮起来，像走进光里（3.5 秒）。

**UE 里怎么用**：2D（不空间化），放到 UI 的 Sound Class。Hover 两个 Random；Confirm / Back 各一个；StartGame 在点“开始”时播，可以和第一声海浪（11）重叠。

| 用途 | 文件 | 时长 | 声道 |
|---|---|---|---|
| 悬停 | [`SFX_UI_Hover_01`](sfx/29_UI/SFX_UI_Hover_01.wav) | 0.08 s | 立体 |
| 悬停 | [`SFX_UI_Hover_02`](sfx/29_UI/SFX_UI_Hover_02.wav) | 0.08 s | 立体 |
| 确认 | [`SFX_UI_Confirm`](sfx/29_UI/SFX_UI_Confirm.wav) | 0.80 s | 立体 |
| 返回 | [`SFX_UI_Back`](sfx/29_UI/SFX_UI_Back.wav) | 0.50 s | 立体 |
| 开始游戏 | [`SFX_UI_StartGame`](sfx/29_UI/SFX_UI_StartGame.wav) | 3.60 s | 立体 |

文件夹：[sfx/29_UI/](sfx/29_UI/)

### 30. 开场光路显形（第二梯队）

**怎么做的**：开场第一个“光”的声音：和 5 是同一套素材（摩擦水晶杯、被照亮的水雾、玻璃闪光），拉长到 4.5 秒，跟着光从门廊上方的窗一点点伸到岛上（约 3 秒）——低通一路打开，声像从远处（正前）慢慢铺开，闪光越来越多；光伸到岛上那一刻落在 D、A 上。

**UE 里怎么用**：开场往神殿迈第一步、光开始伸出来时播一次（灰盒 updateIsleGrow）。立体声；2D 播放也可以（这是开场的“标题音”）。

| 用途 | 文件 | 时长 | 声道 |
|---|---|---|---|
| 开场 | [`SFX_LightPath_Reveal_Opening`](sfx/30_LightPath_Reveal_Opening/SFX_LightPath_Reveal_Opening.wav) | 4.60 s | 立体 |

文件夹：[sfx/30_LightPath_Reveal_Opening/](sfx/30_LightPath_Reveal_Opening/)

### 31. 捧着金苹果（第三梯队）

**怎么做的**：整个夜里捧在手里的那点暖：摩擦颂钵的低音（F4）垫底，上面一只摩擦水晶杯（A5 或 C6，一阵换一只）——F、A、C 是一个大三和弦，比月光那一套暖。像海浪一样一阵一阵：每一阵慢慢涌上来（约 3.5 秒）、再慢慢退下去，退到很轻以后下一阵才来；四阵的间隔、大小都不一样，30 秒无缝循环，听久了也不吵。颂钵只取录音里摩擦得最稳的中段，颂钵和水晶杯都只留下稳定的分音：摩擦棒的沙沙声、偶尔的碰撞声，和颂钵本身那个不在 F、A、C 上的泛音（约 980 Hz，正好卡在 A5 和 C6 中间）都去掉了。

**UE 里怎么用**：接住最后一缕光以后一直循环到放下苹果（Looping），2D 跟着玩家，音量很低；放上苹果时 2 秒淡出，接 27 的 Apple_Place。

| 用途 | 文件 | 时长 | 声道 |
|---|---|---|---|
| 捧着·循环 | [`SFX_Apple_Hold_Loop`](sfx/31_Apple_Hold/SFX_Apple_Hold_Loop.wav)（循环） | 30.00 s | 立体 |

文件夹：[sfx/31_Apple_Hold/](sfx/31_Apple_Hold/)

### 32. 脚步：月石、月桥、影桥（第三梯队）

**怎么做的**：夜里的两种特殊路面。月石（月桥也是月石做的）：和石头脚步同一个“接触”，脚下激起一点颂钵的余振（模态合成的钵 + 真实的颂钵敲击，月光的低音区 A3–A4），比光路的水晶低、冷。影桥（水面上的月影）：同一个接触，脚下是一小下真实的水波拍岸（TheyLook_Here），上面一点很轻的高音颂钵。

**UE 里怎么用**：和石头脚步同一套触发：脚下是月石、月桥时用 Moonstone，影桥（Zone shadowbr）用ShadowBridge。Random 不重复。

| 用途 | 文件 | 时长 | 声道 |
|---|---|---|---|
| 月石·走 | `SFX_Footstep_Moonstone_Walk_01` … `08`（8 个） | 0.40–0.46 s | 单 |
| 月石·快走 | `SFX_Footstep_Moonstone_Run_01` … `06`（6 个） | 0.26–0.34 s | 单 |
| 影桥·走 | `SFX_Footstep_ShadowBridge_Walk_01` … `08`（8 个） | 0.59–0.60 s | 单 |
| 影桥·快走 | `SFX_Footstep_ShadowBridge_Run_01` … `06`（6 个） | 0.51–0.52 s | 单 |

文件夹：[sfx/32_Footstep_Moon_Shadow/](sfx/32_Footstep_Moon_Shadow/)

### 33. 拾取碎片 ×3（第三梯队）

**怎么做的**：三片碎片各有自己的材料：日之碎片（正四面体，火）是小铜钵一声（和“确认”同一只）接着三只水晶杯很快往上走（D5、A5、D6），暖、亮；月之碎片（正二十面体，水）是两声颂钵（D4、A4）和几滴往下落的玻璃水珠；虹之碎片（正八面体，气）是七只水晶杯一口气从低到高（七种颜色），带一点被照亮的水雾。都在 3 秒以内，最后落在一个长一点的音上，给“获得感”。

**UE 里怎么用**：拿到碎片的那一刻播，2D（不空间化）。三片各用各的。

| 用途 | 文件 | 时长 | 声道 |
|---|---|---|---|
| 日之碎片 | [`SFX_Shard_Pickup_Sun`](sfx/33_Shard_Pickup/SFX_Shard_Pickup_Sun.wav) | 3.30 s | 立体 |
| 月之碎片 | [`SFX_Shard_Pickup_Moon`](sfx/33_Shard_Pickup/SFX_Shard_Pickup_Moon.wav) | 3.35 s | 立体 |
| 虹之碎片 | [`SFX_Shard_Pickup_Rainbow`](sfx/33_Shard_Pickup/SFX_Shard_Pickup_Rainbow.wav) | 3.40 s | 立体 |

文件夹：[sfx/33_Shard_Pickup/](sfx/33_Shard_Pickup/)

### 35. 关卡标题短乐句（第三梯队）

**怎么做的**：每关标题出现时的一句短乐句（2–4 秒），用游戏里已有的“乐器”：白天是石磬（屋顶台阶那种调过音的石头）一级级往上、最后落在一只水晶杯上；夜里是颂钵一声声往下。白天一关比一关结束得高（日1 落在 A5，日5 落在铜钵和 D6），夜里一关比一关结束得低（月1 落在 D4，月5 落到 D3）——跟着太阳往上爬、跟着月亮往下走。序是两只水晶杯的空五度；“日落之后 · 入夜”是水晶往下交给颂钵。全部在 d 小调五声里。

**UE 里怎么用**：关卡标题出现时播（灰盒 showTitle），2D。文件名对应：Prologue=序，Day1–5=日1–日5，Dusk=日落之后·入夜，Night1–5=月1–月5。

| 用途 | 文件 | 时长 | 声道 |
|---|---|---|---|
| 标题 | `SFX_Title_Prologue` … `t5`（12 个） | 3.80–4.40 s | 立体 |

文件夹：[sfx/35_Level_Title/](sfx/35_Level_Title/)

### 36. 互动提示出现、提示文字出现（第三梯队）

**怎么做的**：提示出现：一颗很小的玻璃闪光（真实的玻璃轻碰）加一点很短的高音水晶，很轻；提示文字出现：一口很轻的“气”（被照亮的水雾那一段）托着一只很远的水晶杯，像一行字从光里浮出来。两样都轻到不打扰，但不看屏幕也能听见“有东西可以按了”。

**UE 里怎么用**：Prompt_Appear：互动提示（按 E）从无到有的那一刻；Text_Appear：提示文字（toast）出现时。2D，各两个 Random。同一秒里只播一个。

| 用途 | 文件 | 时长 | 声道 |
|---|---|---|---|
| 提示出现 | [`SFX_UI_Prompt_Appear_01`](sfx/36_UI_Prompt/SFX_UI_Prompt_Appear_01.wav) | 0.51 s | 立体 |
| 提示出现 | [`SFX_UI_Prompt_Appear_02`](sfx/36_UI_Prompt/SFX_UI_Prompt_Appear_02.wav) | 0.51 s | 立体 |
| 文字出现 | [`SFX_UI_Text_Appear_01`](sfx/36_UI_Prompt/SFX_UI_Text_Appear_01.wav) | 0.73 s | 立体 |
| 文字出现 | [`SFX_UI_Text_Appear_02`](sfx/36_UI_Prompt/SFX_UI_Text_Appear_02.wav) | 0.73 s | 立体 |

文件夹：[sfx/36_UI_Prompt/](sfx/36_UI_Prompt/)

### 37. 对话推进音（第三梯队）

**怎么做的**：翻到下一句：一把小锤在石头上轻轻一点（Shamewap 的录音，比“悬停”低、更圆），后面跟一点很短的颂钵余音。三个版本轮着用，听很多次也不烦。

**UE 里怎么用**：对话框翻页/下一句时播，2D，Random 不重复。

| 用途 | 文件 | 时长 | 声道 |
|---|---|---|---|
| 下一句 | `SFX_UI_Dialogue_Next_01` … `03`（3 个） | 0.41–0.50 s | 立体 |

文件夹：[sfx/37_UI_Dialogue_Advance/](sfx/37_UI_Dialogue_Advance/)

### 38. 海风（第三梯队）

**怎么做的**：屋顶的高度感：真实的海边悬崖小路上的强风（bruno.auzet），有一阵一阵的起伏，去掉最低的隆隆声，22 秒无缝循环。

**UE 里怎么用**：屋顶（和四层外沿）循环播放，2D 或很大的衰减半径；越高越响，进殿以后用 Audio Volume 压低 10–15 dB、低通到 600 Hz。和 11 的远处海浪叠着用。

| 用途 | 文件 | 时长 | 声道 |
|---|---|---|---|
| 海风·循环 | [`SFX_Roof_Wind_Loop`](sfx/38_Roof_Wind/SFX_Roof_Wind_Loop.wav)（循环） | 19.00 s | 立体 |

文件夹：[sfx/38_Roof_Wind/](sfx/38_Roof_Wind/)

### 39. 殿内空间底噪（第三梯队）

**怎么做的**：殿里“安静”的声音：不是真的没声音，而是一座大石头圆殿里的空气——很轻的粉噪声经过圆殿的脉冲响应（和 ir/ 里给 UE 的是同一个），墙外的海隔着石墙只剩最低的一层（bruno.auzet 的崖上听海，低通到 350 Hz），殿里的瀑布在远处只剩闷闷的一点（低通到 250 Hz）。20 秒无缝循环，很轻。

**UE 里怎么用**：殿内的 Audio Volume 里一直循环（2D）；出殿 2 秒淡出、换成 11 的海浪。瀑布没开的时候（日1 开闸前）也可以用，瀑布那一层很低。

| 用途 | 文件 | 时长 | 声道 |
|---|---|---|---|
| 殿内·循环 | [`SFX_Interior_RoomTone_Loop`](sfx/39_Interior_RoomTone/SFX_Interior_RoomTone_Loop.wav)（循环） | 19.00 s | 立体 |

文件夹：[sfx/39_Interior_RoomTone/](sfx/39_Interior_RoomTone/)

### 40. 水池水面（第三梯队）

**怎么做的**：水庭的黑石镜池：真实的轻轻拍着岩岸的水（TheyLook_Here），一下一下、很稀，20 秒无缝循环。原录音里有几下水泡的“咕噜”带着音高、会滑音，听起来像猫叫、像人说话——把这些有音高的细线从频谱里压掉了，水声本身不动。

**UE 里怎么用**：放在水池边几处（或池心，衰减半径约 3–15 m），Looping。夜里潮水涨起来时可以把音量提高 3 dB。

| 用途 | 文件 | 时长 | 声道 |
|---|---|---|---|
| 水面·循环 | [`SFX_Pool_Water_Loop`](sfx/40_Pool_Water/SFX_Pool_Water_Loop.wav)（循环） | 20.00 s | 立体 |

文件夹：[sfx/40_Pool_Water/](sfx/40_Pool_Water/)

### 41. 女神像变天鹅（第三梯队）

**怎么做的**：月光照满女神像，她变成天鹅：月光的颂钵长音（D4）和水晶杯（A5）慢慢亮起来，中间一对大翅膀展开、扇了几下（Lsoundaccount 的真实扇翅声），羽毛落定。另有反过来的一条：月光离开，天鹅收起翅膀、变回女神像。

**UE 里怎么用**：Swan_Transform：天鹅形态从 0 往 1 走时播（SWAN.form），放在女神像上；Swan_Revert：从 1 往 0 走时播。

| 用途 | 文件 | 时长 | 声道 |
|---|---|---|---|
| 变天鹅 | [`SFX_Swan_Transform`](sfx/41_Swan_Transform/SFX_Swan_Transform.wav) | 4.20 s | 立体 |
| 变回女神像 | [`SFX_Swan_Revert`](sfx/41_Swan_Transform/SFX_Swan_Revert.wav) | 2.80 s | 立体 |

文件夹：[sfx/41_Swan_Transform/](sfx/41_Swan_Transform/)

### 42. 浑天仪开始自转（第三梯队）

**怎么做的**：结局里浑天仪自己转起来——“时间交出去了”：一开始是轴承一格一格的轻响（HenKonen 的真实金属轻碰，很小），越来越快，最后连成一片平滑的转动声（KVV_Audio 的真实木轮转动，降调，转得比较慢，速度一路往上滑）。之后接一条一直慢慢转下去的循环。没有颂钵、水晶杯，也没有金属刮擦。

**UE 里怎么用**：Armillary_Start：浑天仪开始自转时播（单声道，放在小亭的浑天仪上，约 6.5 s）；它的最后 1 秒和 Armillary_Spin_Loop 交叉接上（Loop Fade In 1 s），一直转到结局画面。

| 用途 | 文件 | 时长 | 声道 |
|---|---|---|---|
| 开始自转 | [`SFX_Armillary_Start`](sfx/42_Armillary_Spin/SFX_Armillary_Start.wav) | 6.50 s | 单 |
| 持续转动·循环 | [`SFX_Armillary_Spin_Loop`](sfx/42_Armillary_Spin/SFX_Armillary_Spin_Loop.wav)（循环） | 13.50 s | 单 |

文件夹：[sfx/42_Armillary_Spin/](sfx/42_Armillary_Spin/)

### 43. 白天鸟鸣（第三梯队）

**怎么做的**：海中央的白天：没有成片的鸟叫，只是隔一阵远处有一只海鸥叫几声（Ambientsoundapp），偶尔一只燕子掠过（SamuelGremaud）。32 秒里只有四声，中间是空的（下面垫着 11 的海浪），低频去掉（和海浪不打架）。

**UE 里怎么用**：开场的岛上和殿外的白天循环（2D 或大衰减半径），和 11 的海浪叠着用；日5 太阳落下去时 5–10 秒淡出。

| 用途 | 文件 | 时长 | 声道 |
|---|---|---|---|
| 鸟鸣·循环 | [`SFX_Day_Birds_Loop`](sfx/43_Day_Birds/SFX_Day_Birds_Loop.wav)（循环） | 32.00 s | 立体 |

文件夹：[sfx/43_Day_Birds/](sfx/43_Day_Birds/)

### 44. 脚步：浅水、湿石（第三梯队）

**怎么做的**：浅水：真实的踩水脚步（aglinder、ChristopherJngs 的录音），一步一步切出来，只留一次水花。湿石：和石头脚步同一个“接触”，下面叠一层真实的赤脚踩湿瓷砖（SpliceSound）的“湿”声，石头的“实”换成更软的一点。

**UE 里怎么用**：和石头脚步同一套触发：脚下是浅水（潮沟、水庭边的浅水）用 Water，湿的石面（瀑布、水闸石台附近）用 WetStone。Random 不重复。

| 用途 | 文件 | 时长 | 声道 |
|---|---|---|---|
| 浅水·走 | `SFX_Footstep_Water_Walk_01` … `08`（8 个） | 0.32–0.39 s | 单 |
| 浅水·快走 | `SFX_Footstep_Water_Run_01` … `04`（4 个） | 0.31–0.38 s | 单 |
| 湿石·走 | `SFX_Footstep_WetStone_Walk_01` … `08`（8 个） | 0.21–0.23 s | 单 |

文件夹：[sfx/44_Footstep_Water_Wet/](sfx/44_Footstep_Water_Wet/)

### 45. 瀑布水帘透开（第三梯队）

**怎么做的**：镜子反射的月光打到瀑布上，那一块水帘透开：瀑布那一块的轰鸣变薄（低频一路被抽掉，只剩细的水声），上面是月光的颂钵（A4）和水晶（D6）轻轻亮起来、几颗水珠的闪光。另有合上的一条（月光离开，那一块又变回厚水帘）。

**UE 里怎么用**：Hole_Open：瀑布上透开那一块从 0 往 1 走时（FALLHOLE.k），放在透开处；Hole_Close：从 1 往 0 走时。瀑布的循环照常播，这两条叠在上面。

| 用途 | 文件 | 时长 | 声道 |
|---|---|---|---|
| 透开 | [`SFX_Waterfall_Hole_Open`](sfx/45_Waterfall_Hole/SFX_Waterfall_Hole_Open.wav) | 2.80 s | 立体 |
| 合上 | [`SFX_Waterfall_Hole_Close`](sfx/45_Waterfall_Hole/SFX_Waterfall_Hole_Close.wav) | 1.80 s | 立体 |

文件夹：[sfx/45_Waterfall_Hole/](sfx/45_Waterfall_Hole/)

### 46. 彩虹桥出现、伊莉丝浮雕醒来（第四梯队）

**怎么做的**：伊莉丝浮雕醒来：浮雕上沿的铜唇里流下一层细水帘（真实的小水流，kyles），刻在浮雕上的那圈虹亮起来——三只水晶杯（D5、A5、D6）慢慢长起来。彩虹桥出现：七只水晶杯从低到高（红到紫），声像从浮雕这边一路拱到对面窗台（左到右），下面是被照亮的水雾和闪光，最后七色一起停在一个长音上。

**UE 里怎么用**：IrisRelief_Awaken：影子的头落进人形、虹醒过来时，放在浮雕上；RainbowBridge_Appear：虹桥开始从浮雕上走下来时播，立体声，放在虹桥中点。

| 用途 | 文件 | 时长 | 声道 |
|---|---|---|---|
| 浮雕醒来 | [`SFX_IrisRelief_Awaken`](sfx/46_Rainbow_Bridge_IrisRelief/SFX_IrisRelief_Awaken.wav) | 3.20 s | 立体 |
| 彩虹桥出现 | [`SFX_RainbowBridge_Appear`](sfx/46_Rainbow_Bridge_IrisRelief/SFX_RainbowBridge_Appear.wav) | 4.20 s | 立体 |

文件夹：[sfx/46_Rainbow_Bridge_IrisRelief/](sfx/46_Rainbow_Bridge_IrisRelief/)

### 47. 棱镜转台转一格（7 个音高）（第四梯队）

**怎么做的**：转棱镜的铜轮转一格：轮子“咔”一声（真实的石头碰撞 + 金属轻碰，很小），接着一只水晶杯响一下——七格七个音，从红（D5）到紫（F6），颜色的频率越高音越高。第六格是靛色（D6），也就是落进塞勒涅眼睛的那一色。

**UE 里怎么用**：转到第几格播第几个（_1_Red … _7_Violet）。棱镜在窗下石沿上，单声道放在棱镜上。

| 用途 | 文件 | 时长 | 声道 |
|---|---|---|---|
| 转一格 | `SFX_Prism_Turn_1_Red` … `et`（7 个） | 1.43–1.43 s | 单 |

文件夹：[sfx/47_Prism_Turn/](sfx/47_Prism_Turn/)

### 48. 塞勒涅眼睛点亮（第四梯队）

**怎么做的**：靛色的光落进塞勒涅浮雕的青金石眼睛：先是一声很亮的水晶“叮”（D6，像宝石里点着了光），接着月亮的颂钵（D4）低低地应一声，摩擦颂钵 A4 慢慢亮起来，几颗闪光。

**UE 里怎么用**：眼睛亮起来那一刻播，放在浮雕的眼睛上；对话在这条播到 2 秒左右以后再开始。

| 用途 | 文件 | 时长 | 声道 |
|---|---|---|---|
| 眼睛点亮 | [`SFX_Selene_Eyes_Light`](sfx/48_Selene_Eyes/SFX_Selene_Eyes_Light.wav) | 3.80 s | 立体 |

文件夹：[sfx/48_Selene_Eyes/](sfx/48_Selene_Eyes/)

### 49. 窗下石沿伸出、虹之龛铜门、棱镜铜柱升起（第四梯队）

**怎么做的**：彩虹支线的三个小机关：窗下石沿伸出（16 的石板滑动，更短、更轻：0.9 m 的石沿从墙里滑出来）；虹之龛的两扇小铜门（两声小的门轴吱呀，一前一后，最后轻轻一靠）；托着棱镜的铜柱从石沿里升起来（轻的石头摩擦，升到顶一声小的铜响）。

**UE 里怎么用**：Sill_Ledge_Extend：虹桥快落到对岸、石沿开始伸出时；Niche_Doors_Open：打开虹之龛；Prism_Column_Rise：铜柱开始升起时。都放在机关上，单声道。

| 用途 | 文件 | 时长 | 声道 |
|---|---|---|---|
| 石沿伸出 | [`SFX_Sill_Ledge_Extend`](sfx/49_Rainbow_Small_Mechs/SFX_Sill_Ledge_Extend.wav) | 1.50 s | 单 |
| 虹之龛铜门 | [`SFX_Niche_Doors_Open`](sfx/49_Rainbow_Small_Mechs/SFX_Niche_Doors_Open.wav) | 1.20 s | 单 |
| 铜柱升起 | [`SFX_Prism_Column_Rise`](sfx/49_Rainbow_Small_Mechs/SFX_Prism_Column_Rise.wav) | 2.00 s | 单 |

文件夹：[sfx/49_Rainbow_Small_Mechs/](sfx/49_Rainbow_Small_Mechs/)

### 50. 三相像镜子醒来、日之龛开盖（第四梯队）

**怎么做的**：三相像醒来（日相）：石像在台座上轻轻一动（短的石头摩擦），铜镜迎着太阳亮起来——两只水晶杯（D5、A5）很快亮起来，铜镜本身轻轻一声共振。日之龛开盖：铜匣的盖子绕后沿翻开（一声短的门轴吱呀、盖子靠住的一下），里面的光一下透出来（水晶杯 A5），碎片升起时几颗闪光往上走。

**UE 里怎么用**：Mirror_Awaken：三相像变成日相时（灰盒 updateMirrors 里 form 变成 sun），放在像上；SunNiche_Open：打开日之龛时，放在铜匣上。

| 用途 | 文件 | 时长 | 声道 |
|---|---|---|---|
| 镜子醒来 | [`SFX_Mirror_Awaken`](sfx/50_Mirror_SunNiche/SFX_Mirror_Awaken.wav) | 2.80 s | 立体 |
| 日之龛开盖 | [`SFX_SunNiche_Open`](sfx/50_Mirror_SunNiche/SFX_SunNiche_Open.wav) | 2.90 s | 立体 |

文件夹：[sfx/50_Mirror_SunNiche/](sfx/50_Mirror_SunNiche/)

### 52. 正十二面体与星座亮起（第四梯队）

**怎么做的**：三片碎片合成正十二面体（柏拉图说它是宇宙的形状）：很深的一声颂钵（D3）托底，水晶杯 D5、A5、D6、F6 一层层长上去；星座一颗一颗亮起来——三十多颗玻璃闪光从中间往两边散开，越来越多。6.5 秒。

**UE 里怎么用**：正十二面体合成、星座开始亮时播，2D 或放在合成的位置（立体声）。

| 用途 | 文件 | 时长 | 声道 |
|---|---|---|---|
| 亮起 | [`SFX_Dodecahedron_Stars`](sfx/52_Dodecahedron_Stars/SFX_Dodecahedron_Stars.wav) | 6.50 s | 立体 |

文件夹：[sfx/52_Dodecahedron_Stars/](sfx/52_Dodecahedron_Stars/)

### 53. 虹门彩虹（第四梯队）

**怎么做的**：屋顶虹门里的那道小彩虹：背对夕阳穿过虹门时，三只水晶杯（F5、A5、C6）很轻地亮一下，带一点被照亮的水雾——比 46 的彩虹桥小得多，只是一个细节。

**UE 里怎么用**：穿过虹门、彩虹出现时播（每次经过最多播一次），放在虹门上，很轻。

| 用途 | 文件 | 时长 | 声道 |
|---|---|---|---|
| 虹门彩虹 | [`SFX_RainbowGate_Rainbow`](sfx/53_RainbowGate_Rainbow/SFX_RainbowGate_Rainbow.wav) | 3.20 s | 立体 |

文件夹：[sfx/53_RainbowGate_Rainbow/](sfx/53_RainbowGate_Rainbow/)

### 54. 墙里楼梯的窗打开（第四梯队）

**怎么做的**：墙里楼梯朝外的小窗里堵着的石块，一块一块被推出去：每块是 24 里墙里楼梯显现用的同一种石块（短的摩擦 + 落定），一样闷一点（在墙里面）。三个版本。

**UE 里怎么用**：要逐扇同步的话（灰盒 TUNWIN：从上往下 0.25 s 一块），每块开始动时播一个，Random；已经用了 24 的 WallStairs_Reveal 就不用再播这个。

| 用途 | 文件 | 时长 | 声道 |
|---|---|---|---|
| 一扇窗 | `SFX_WallStairs_Window_01` … `03`（3 个） | 0.91–0.93 s | 单 |

文件夹：[sfx/54_WallStairs_Windows/](sfx/54_WallStairs_Windows/)

### 55. 氛围层：水雾（第四梯队）

**怎么做的**：水雾：瀑布录音里最高的那一段细嘶声（开闸以后中庭里的雾），很轻地起伏，无缝循环。

**UE 里怎么用**：Mist_Loop：开闸以后中庭里一直在（和雾的浓度一起淡入淡出）。

| 用途 | 文件 | 时长 | 声道 |
|---|---|---|---|
| 水雾·循环 | [`SFX_Mist_Loop`](sfx/55_Ambience_Layers/SFX_Mist_Loop.wav)（循环） | 16.00 s | 立体 |

文件夹：[sfx/55_Ambience_Layers/](sfx/55_Ambience_Layers/)

### 56. 塞勒涅梦话（第四梯队）

**怎么做的**：塞勒涅在梦里说话：她的“声音”是一只摩擦颂钵（月神，低、慢、柔），很慢、很含糊——几个音节拖长、音高往下滑，中间停很久，最后一声很轻的叹气（一小口带通的气声）。两段。

**UE 里怎么用**：彩虹支线里靠近她的浮雕、她还没醒的时候，隔一会儿随机播一段（放在浮雕上，很轻）。

| 用途 | 文件 | 时长 | 声道 |
|---|---|---|---|
| 梦话 | [`SFX_Selene_SleepTalk_01`](sfx/56_Selene_SleepTalk/SFX_Selene_SleepTalk_01.wav) | 4.06 s | 立体 |
| 梦话 | [`SFX_Selene_SleepTalk_02`](sfx/56_Selene_SleepTalk/SFX_Selene_SleepTalk_02.wav) | 3.62 s | 立体 |

文件夹：[sfx/56_Selene_SleepTalk/](sfx/56_Selene_SleepTalk/)

### 57. 界面：碰到已获得的日月虹碎片（第四梯队）

**怎么做的**：鼠标碰到界面里已经拿到的碎片时，那片碎片轻轻响一下，和 33 拾取时同一种材料，只是小得多：日是一只很短的水晶杯（D6），月是一声很短的颂钵（A5），虹是三只水晶杯一闪（D6、F6、A6）。

**UE 里怎么用**：2D，放到 UI 的 Sound Class；同一片碎片 0.3 秒内只播一次。

| 用途 | 文件 | 时长 | 声道 |
|---|---|---|---|
| 悬停 | `SFX_UI_Shard_Hover_Sun` … `ow`（3 个） | 0.45–0.50 s | 立体 |

文件夹：[sfx/57_UI_Shard_Hover/](sfx/57_UI_Shard_Hover/)


## 重新生成

```
pip install numpy scipy soundfile
python audio/tools/fetch_sources.py   # 下载素材到 audio/_src（不进仓库；需要 curl、ffmpeg）
python audio/tools/build.py           # 全部重新生成；build.py 5 15 只生成这几条
```

`tools/dsp.py` 是小工具箱（滤波、模态合成、切脚步、无缝循环、响度），`tools/build.py` 里一条音效一个函数，参数都在里面（音高、长短、各层的比例），要改哪条就改哪个函数再跑一遍。
随机数都固定了种子，同样的素材生成的结果一样。这个文件（README）和 `manifest.json` 也是 build.py 生成的。

## 还没做

- 第一梯队的 1、2（时间和声）、7（接光主题）、12（主界面音乐）、13（结局音乐）。
- 第三梯队的 34（岛影逼近）。
- 这些声音是按频谱、波形、响度一条条检查过的，但还需要真人戴耳机在游戏里听一遍：哪条太响、太长、太“假”，告诉我改哪个函数的哪几个参数。

## 素材出处

全部是 Freesound 上的 CC0（公有领域）录音：可以商用、可以改，不需要署名。还是列出来，方便以后找回原始录音、换更高质量的版本（这里用的是 Freesound 的高质量试听版，约 192 kbps）。

| 编号 | 作者 | 名字 |
|---|---|---|

| [59159](https://freesound.org/people/Coleco/sounds/59159/) | Coleco | singingbowlstruck2.wav |
| [107589](https://freesound.org/people/Qat/sounds/107589/) | Qat | unsheath_sword.wav |
| [118985](https://freesound.org/people/ragamuffin/sounds/118985/) | ragamuffin | male-foot-walk-marble-stereo.aif |
| [119911](https://freesound.org/people/ftpalad/sounds/119911/) | ftpalad | Footsteps Sandals Going Up Concrete Steps.aif |
| [119912](https://freesound.org/people/ftpalad/sounds/119912/) | ftpalad | Footsteps Sandals on Concrete.aif |
| [193823](https://freesound.org/people/jhumbucker/sounds/193823/) | jhumbucker | Wine glass tinkles |
| [197404](https://freesound.org/people/SpliceSound/sounds/197404/) | SpliceSound | 01-14 Footsteps, Tile, Male Barefoot, Scuffs.wav |
| [198403](https://freesound.org/people/ani_music/sounds/198403/) | ani_music | ANI - Wine glass - Rubbing 1a |
| [202004](https://freesound.org/people/ryancacophony/sounds/202004/) | ryancacophony | singing bowl sing.wav |
| [255762](https://freesound.org/people/Squidocto/sounds/255762/) | Squidocto | bell-bowl G-ish.wav |
| [256251](https://freesound.org/people/spectral9/sounds/256251/) | spectral9 | Wine Glass Sustained Note F#6 |
| [265582](https://freesound.org/people/aglinder/sounds/265582/) | aglinder | Footsteps Water 01 |
| [271668](https://freesound.org/people/HonorHunter/sounds/271668/) | HonorHunter | Water gush; full.wav |
| [338106](https://freesound.org/people/SpliceSound/sounds/338106/) | SpliceSound | Footsteps, barefoot on wet tile.wav |
| [352829](https://freesound.org/people/Kinoton/sounds/352829/) | Kinoton | Tomb Door Open, Stone Scrape |
| [389692](https://freesound.org/people/Shamewap/sounds/389692/) | Shamewap | Tiny Hammer on Stone.wav |
| [391448](https://freesound.org/people/saturdaysoundguy/sounds/391448/) | saturdaysoundguy | Shirt Whoosh 1.wav |
| [391794](https://freesound.org/people/Alexbuk/sounds/391794/) | Alexbuk | METAL SFX & FOLEY, Metal slide, clunk and clink (door bolt).wav |
| [418150](https://freesound.org/people/PappaBert/sounds/418150/) | PappaBert | Ringing sound from crystal glass in H (Bb). |
| [419146](https://freesound.org/people/PappaBert/sounds/419146/) | PappaBert | Ringing sound from crystal glass. Tune: C |
| [419147](https://freesound.org/people/PappaBert/sounds/419147/) | PappaBert | Ringing sound from crystal glass. Tune: G |
| [448418](https://freesound.org/people/LordForklift/sounds/448418/) | LordForklift | Metal Slide 2 |
| [454148](https://freesound.org/people/kyles/sounds/454148/) | kyles | ratchet pulley winch pull metal plastic junk slide rattle.flac |
| [454340](https://freesound.org/people/kyles/sounds/454340/) | kyles | waterfall small or water fountain splashy close stream into water.flac |
| [457956](https://freesound.org/people/dan.pugsley/sounds/457956/) | dan.pugsley | Waves lapping on rocks |
| [463811](https://freesound.org/people/nate_asdfg/sounds/463811/) | nate_asdfg | Footsteps on Metal Floor |
| [465807](https://freesound.org/people/PaceHeart/sounds/465807/) | PaceHeart | big stone door suddenly slamming shut |
| [495390](https://freesound.org/people/Nox_Sound/sounds/495390/) | Nox_Sound | Foley_Whoosh_Clothes.wav |
| [508178](https://freesound.org/people/Breviceps/sounds/508178/) | Breviceps | Water Pouring Out of Bucket |
| [525029](https://freesound.org/people/bruno.auzet/sounds/525029/) | bruno.auzet | sea from cliff.wav |
| [530987](https://freesound.org/people/patchytherat/sounds/530987/) | patchytherat | stone door close.wav |
| [537854](https://freesound.org/people/Ambientsoundapp/sounds/537854/) | Ambientsoundapp | Seagulls distant.wav |
| [543683](https://freesound.org/people/SamuelGremaud/sounds/543683/) | SamuelGremaud | SWALLOWS |
| [559203](https://freesound.org/people/saralana/sounds/559203/) | saralana | Waterfall |
| [562195](https://freesound.org/people/gristi/sounds/562195/) | gristi | snd_footsteps_metal_floor_inside.wav |
| [573805](https://freesound.org/people/hollandm/sounds/573805/) | hollandm | Singing Bowl, long without reverb |
| [578491](https://freesound.org/people/PostProdDog/sounds/578491/) | PostProdDog | Heavy stone door opens 2 |
| [627070](https://freesound.org/people/nicoproson/sounds/627070/) | nicoproson | SAND POUR.wav |
| [637583](https://freesound.org/people/kyles/sounds/637583/) | kyles | gate big rusty metal door garage open heavy creak rattle.flac |
| [669719](https://freesound.org/people/vestibule-door/sounds/669719/) | vestibule-door | heavy thumps on stone.wav |
| [682154](https://freesound.org/people/HenKonen/sounds/682154/) | HenKonen | Metallic Clink 3.wav |
| [682776](https://freesound.org/people/thomasanthony321/sounds/682776/) | thomasanthony321 | Metal gate opening.WAV |
| [696746](https://freesound.org/people/Krokulator/sounds/696746/) | Krokulator | lever.wav |
| [698306](https://freesound.org/people/Nox_Sound/sounds/698306/) | Nox_Sound | Ambiance_Waterfall_Small_Close_Loop_Stereo.wav |
| [698697](https://freesound.org/people/IENBA/sounds/698697/) | IENBA | Footsteps on Metal |
| [706471](https://freesound.org/people/bruno.auzet/sounds/706471/) | bruno.auzet | strong wind on coastal path.wav |
| [715478](https://freesound.org/people/KVV_Audio/sounds/715478/) | KVV_Audio | MECHRolr_Turning A Wooden Wheel 01_KVV_FREE |
| [734632](https://freesound.org/people/Vrymaa/sounds/734632/) | Vrymaa | Footsteps Sandals - Walk & run |
| [753219](https://freesound.org/people/Lsoundaccount/sounds/753219/) | Lsoundaccount | 1. Wings Flapping |
| [762646](https://freesound.org/people/FOSSarts/sounds/762646/) | FOSSarts | small brass sound bowl strike and ring - 3 |
| [791907](https://freesound.org/people/LePainMaudit/sounds/791907/) | LePainMaudit | Heavy chain |
| [813622](https://freesound.org/people/SecureSubset/sounds/813622/) | SecureSubset | Footsteps - Stone, Rock, Concrete, Cement |
| [844329](https://freesound.org/people/NahuelMartinez/sounds/844329/) | NahuelMartinez | Stone Slab Door Grinding - Heavy Rock Scrape (Mono) |
| [858891](https://freesound.org/people/xtra1/sounds/858891/) | xtra1 | Stone on Stone Hit |
| [861369](https://freesound.org/people/ChristopherJngs/sounds/861369/) | ChristopherJngs | Splashing Footsteps Shallow Water |
| [866205](https://freesound.org/people/TheyLook_Here/sounds/866205/) | TheyLook_Here | Gentle water ripples lapping against a rocky shore. |
