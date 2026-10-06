# 音效 · 第一、第二梯队

日落回廊的音效：第一梯队里除了 1、2、7、12、13（时间和声、接光主题、主界面音乐、结局音乐，之后单独做）以外的全部，加上第二梯队全部（14–30）。
共 25 条、161 个文件。**试听：用浏览器打开 [index.html](index.html)**（按编号分组，可以切“殿内混响”听放进圆殿以后的样子）。

## 怎么做的

**要真实**，所以能用真实录音的地方都用真实录音：47 段 Freesound 上的 CC0 录音（凉鞋、石地面、石板门、铁链、铜钵、水晶杯、瀑布、海浪……，出处在最后），切、降调、叠层、滤波、对齐响度。
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

**怎么做的**：皮凉鞋踩在大理石上。真实的凉鞋脚步（Vrymaa、ftpalad 的录音）一步一步切出来，下面垫一层真实的石地面脚步的“实”（SecureSubset），峰对齐后叠在一起；去掉 400 Hz 的闷、收一点刺耳的高频。走 10 个、快走 8 个、蹭地 4 个，响度都对齐。

**UE 里怎么用**：Sound Cue：Random（不重复）→ Modulator（音高 0.96–1.04，音量 0.9–1.0）。每次脚落地（动画通知或按步长）触发；Shift 快走用 Run 那一组。干声交付，殿内的混响交给 Audio Volume / 卷积混响（见 ir/）。

| 用途 | 文件 | 时长 | 声道 |
|---|---|---|---|
| 走 | `SFX_Footstep_Stone_Walk_01` … `10`（10 个） | 0.18–0.22 s | 单 |
| 快走 | `SFX_Footstep_Stone_Run_01` … `08`（8 个） | 0.15–0.21 s | 单 |
| 蹭地 | `SFX_Footstep_Stone_Scuff_01` … `04`（4 个） | 0.41–0.48 s | 单 |

文件夹：[sfx/03_Footstep_Stone/](sfx/03_Footstep_Stone/)

### 4. 脚步：光路（第一梯队）

**怎么做的**：脚下是光：同一双凉鞋的脚步，去掉石头的“实”（低频全拿掉，光没有分量），每一步激起一点水晶的余振——模态合成负责干净的起音，真实的摩擦水晶杯录音（PappaBert）负责有颤动的身体，音高在 d 小调五声里随机取（D5–D6），很轻、半秒就收住，走很久也不吵。

**UE 里怎么用**：和石头脚步同一套触发；脚下是光路（Zone 以 beam: 开头、月石、虹桥、影桥另有材质）时换这一组。Random 不重复，音高不要再随机（已经按音阶取好）。

| 用途 | 文件 | 时长 | 声道 |
|---|---|---|---|
| 走 | `SFX_Footstep_Light_Walk_01` … `10`（10 个） | 0.36–0.57 s | 单 |
| 快走 | `SFX_Footstep_Light_Run_01` … `06`（6 个） | 0.30–0.39 s | 单 |

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

**怎么做的**：起跳：凉鞋在石面上一蹬（真实的蹭地脚步）+ 长袍带起的一下衣料风声（saturdaysoundguy、Nox_Sound 的衣服挥动录音）。落地：两只脚前后差 15–30 毫秒落下，石地面的“实”比走路重，最后衣料落定一下。另有落在光上的版本：没有石头的重量，脚下一声水晶。

**UE 里怎么用**：Jump：起跳那一帧；Land_Stone：落到石头/青铜上（青铜落地见 28）；Land_Light：落到光路、月石上。下落时间长于 0.6 秒的落地可以把音量提高 2–3 dB。

| 用途 | 文件 | 时长 | 声道 |
|---|---|---|---|
| 起跳 | `SFX_Jump_01` … `04`（4 个） | 0.47–0.52 s | 单 |
| 落地·石头 | `SFX_Land_Stone_01` … `04`（4 个） | 0.22–0.50 s | 单 |
| 落地·光 | `SFX_Land_Light_01` … `03`（3 个） | 0.59–0.65 s | 单 |

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

**怎么做的**：拉杆：手握铜把手、轴上一声短的呻吟、铜链“一紧”（LePainMaudit 的重铁链）、扳到底“咔”地卡住（Alexbuk 的门闩）。A 是拉下，B 是推回，用不同的素材段和顺序。石板滑动：一块大石板贴着外墙在滑轨上滑开 1.6 秒（真实的墓门石头摩擦，降调），起步一顿、到位一声闷响；两个版本给两块石板。

**UE 里怎么用**：Lever_Pull：拉 A；Lever_Push：推 B，放在拉杆上。Slab_Slide_01/02：两块石板各自开始滑的时候在石板上播（离得远，靠 UE 的衰减和混响就有“远处传来”的感觉）。

| 用途 | 文件 | 时长 | 声道 |
|---|---|---|---|
| 拉杆 | [`SFX_Lever_Pull`](sfx/16_Lever_StoneSlab/SFX_Lever_Pull.wav) | 1.70 s | 单 |
| 拉杆 | [`SFX_Lever_Push`](sfx/16_Lever_StoneSlab/SFX_Lever_Push.wav) | 1.70 s | 单 |
| 石板滑动 | [`SFX_Slab_Slide_01`](sfx/16_Lever_StoneSlab/SFX_Slab_Slide_01.wav) | 2.40 s | 单 |
| 石板滑动 | [`SFX_Slab_Slide_02`](sfx/16_Lever_StoneSlab/SFX_Slab_Slide_02.wav) | 2.40 s | 单 |

文件夹：[sfx/16_Lever_StoneSlab/](sfx/16_Lever_StoneSlab/)

### 17. 光圈叶片旋开（第二梯队）

**怎么做的**：天花板上的 14 片青铜叶片一片接一片旋开：每一片是真实的金属滑过金属（LordForklift、Qat 的录音）降调成大块铜片，声像绕着头顶转一圈；底下是转动的机构（真实的木轮转动，降得很低）；全开时铜叶片轻轻共振成一个和弦（D、A，铜盘的真实振动比例）。合拢是倒过来的顺序、最后一声更实。还有一条叶片滑动的循环，给开合时间不固定的时候用。

**UE 里怎么用**：Iris_Open / Iris_Close：开、合的完整版（3.5 s）。光圈半径跟着玩家的位置慢慢变时（日4 走圆眼光柱），改用 Iris_Move_Loop，音量跟半径的变化速度走，停下时补一个 Open 的最后 1 秒（或者只停循环）。立体声，放在圆眼中心（头顶）。

| 用途 | 文件 | 时长 | 声道 |
|---|---|---|---|
| 开合 | [`SFX_Iris_Open`](sfx/17_Iris_Blades/SFX_Iris_Open.wav) | 4.80 s | 立体 |
| 开合 | [`SFX_Iris_Close`](sfx/17_Iris_Blades/SFX_Iris_Close.wav) | 4.80 s | 立体 |
| 滑动·循环 | [`SFX_Iris_Move_Loop`](sfx/17_Iris_Blades/SFX_Iris_Move_Loop.wav)（循环） | 4.80 s | 立体 |

文件夹：[sfx/17_Iris_Blades/](sfx/17_Iris_Blades/)

### 18. 桥门开、关（第二梯队）

**怎么做的**：屋顶细桥尽头的青铜桥门绕门柱转 1.4 秒。开：老铜门轴的低沉呻吟（真实的大铁门吱呀声降了 6 个半音，去掉尖的部分），铜门本身微微共振，转到位轻轻一顿。关：同样的呻吟更快，最后是厚重的合拢（铁门撞击 + 石门砰地合上的低频）和一声落闩——接住最后一缕光以后它再也不开，所以关门要像“定了”。

**UE 里怎么用**：Gate_Open：人走近桥尾、门开始转时播；Gate_Close：接住最后一缕光、门开始转回去时播（合拢那一下在 1.35 s）。单声道，放在门轴上。

| 用途 | 文件 | 时长 | 声道 |
|---|---|---|---|
| 开 | [`SFX_Gate_Open`](sfx/18_Bridge_Gate/SFX_Gate_Open.wav) | 2.40 s | 单 |
| 关 | [`SFX_Gate_Close`](sfx/18_Bridge_Gate/SFX_Gate_Close.wav) | 3.60 s | 单 |

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

**怎么做的**：接住最后一缕光、回到桥头以后，另外半圈踏步一级接一级降成楼梯：12 块石头先后往下一沉、各自“咚”地落定（vestibule-door 的石面重击和石头落地，降调），从桥头沿着弧线一路过去（声像从右到左），间隔先快后慢，底下是整段的隆隆声。另附 4 个单级的版本，给程序逐级触发用。

**UE 里怎么用**：Stairs_Lower：楼梯开始降的那一刻播一次，立体声，放在楼梯中段。要逐级同步的话改用 Stairs_Lower_Step_01–04（单声道，放在那一级上，Random）。

| 用途 | 文件 | 时长 | 声道 |
|---|---|---|---|
| 整段 | [`SFX_Stairs_Lower`](sfx/24_Stairs_Lower/SFX_Stairs_Lower.wav) | 5.00 s | 立体 |
| 单级 | `SFX_Stairs_Lower_Step_01` … `04`（4 个） | 0.83–0.91 s | 单 |

文件夹：[sfx/24_Stairs_Lower/](sfx/24_Stairs_Lower/)

### 25. 塞勒涅神像亮起、半桥伸出（第二梯队）

**怎么做的**：月光整个落进她怀里的月亮：低音区一声很深的颂钵（D3），20 的长音在这里“解决”——摩擦颂钵 D4、A4 一起长起来，最上面是水晶杯的 D6，像整座雕像慢慢亮透。半桥：一段石桥从池沿沿半径伸向水亭（2 秒，比雕像轻的石头摩擦），桥头搅动水面（真实的浪拍礁石里最轻的一段），到头轻轻一顿。

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

### 27. 放上金苹果（第二梯队）

**怎么做的**：结局动作。金苹果轻轻落进浑天仪的铜托：一声软的金属碰金属（HenKonen 的金属轻碰，低通抹软），铜托本身“嗡”一下（铜盘的真实振动比例）；接着苹果从金色变成月白、光一点点亮起来（0.5–3 秒）：颂钵 D4、水晶杯 A5 和 D6 慢慢长起来，最后停在一个很安静的 D 上。

**UE 里怎么用**：放上苹果那一刻播，放在小亭的浑天仪上。不要和结局音乐（13）抢：结局音乐最好在 3 秒以后进来。

| 用途 | 文件 | 时长 | 声道 |
|---|---|---|---|
| 放上 | [`SFX_Apple_Place`](sfx/27_Apple_Place/SFX_Apple_Place.wav) | 6.00 s | 立体 |

文件夹：[sfx/27_Apple_Place/](sfx/27_Apple_Place/)

### 28. 脚步：青铜（第二梯队）

**怎么做的**：凉鞋踩在厚青铜板上（环道、细桥、半桥）：和石头脚步同一双凉鞋，下面的“实”换成青铜——厚铜板的真实振动比例做的短共振（不是薄铁皮那种空响），叠一点真实的金属地面脚步（nate_asdfg、gristi 的录音，低通）。走 8 个、快走 6 个、落地 2 个。

**UE 里怎么用**：和石头脚步同一套触发，脚下是青铜（Physical Material = Bronze）时换这一组。

| 用途 | 文件 | 时长 | 声道 |
|---|---|---|---|
| 走 | `SFX_Footstep_Bronze_Walk_01` … `08`（8 个） | 0.32–0.35 s | 单 |
| 快走 | `SFX_Footstep_Bronze_Run_01` … `06`（6 个） | 0.26–0.33 s | 单 |
| 落地 | [`SFX_Land_Bronze_01`](sfx/28_Footstep_Bronze/SFX_Land_Bronze_01.wav) | 0.33 s | 单 |
| 落地 | [`SFX_Land_Bronze_02`](sfx/28_Footstep_Bronze/SFX_Land_Bronze_02.wav) | 0.34 s | 单 |

文件夹：[sfx/28_Footstep_Bronze/](sfx/28_Footstep_Bronze/)

### 29. 界面：按钮悬停、确认、返回，开始游戏（第二梯队）

**怎么做的**：界面也用游戏里的材料：悬停是一把小锤在石头上轻轻一点（Shamewap 的录音，很短、很轻）；确认是一只小铜钵敲一下（FOSSarts），0.8 秒收住；返回是同一只钵、更低更闷、更短；开始游戏是铜钵一声，接着水晶杯 D、A 慢慢亮起来，像走进光里（3.5 秒）。

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
- 第三、四梯队（31–58）。其中不少可以直接复用这里的素材：脚步（月石、月桥、影桥）用 4 的光路脚步换成 6 的颂钵；墙里楼梯的窗、石块用 16、23 的石头；碎片放入凹槽用 27。
- 这些声音是按频谱、波形、响度一条条检查过的，但还需要真人戴耳机在游戏里听一遍：哪条太响、太长、太“假”，告诉我改哪个函数的哪几个参数。

## 素材出处

全部是 Freesound 上的 CC0（公有领域）录音：可以商用、可以改，不需要署名。还是列出来，方便以后找回原始录音、换更高质量的版本（这里用的是 Freesound 的高质量试听版，约 192 kbps）。

| 编号 | 作者 | 名字 |
|---|---|---|

| [59159](https://freesound.org/people/Coleco/sounds/59159/) | Coleco | singingbowlstruck2.wav |
| [107589](https://freesound.org/people/Qat/sounds/107589/) | Qat | unsheath_sword.wav |
| [119911](https://freesound.org/people/ftpalad/sounds/119911/) | ftpalad | Footsteps Sandals Going Up Concrete Steps.aif |
| [119912](https://freesound.org/people/ftpalad/sounds/119912/) | ftpalad | Footsteps Sandals on Concrete.aif |
| [193823](https://freesound.org/people/jhumbucker/sounds/193823/) | jhumbucker | Wine glass tinkles |
| [197404](https://freesound.org/people/SpliceSound/sounds/197404/) | SpliceSound | 01-14 Footsteps, Tile, Male Barefoot, Scuffs.wav |
| [198403](https://freesound.org/people/ani_music/sounds/198403/) | ani_music | ANI - Wine glass - Rubbing 1a |
| [202004](https://freesound.org/people/ryancacophony/sounds/202004/) | ryancacophony | singing bowl sing.wav |
| [255762](https://freesound.org/people/Squidocto/sounds/255762/) | Squidocto | bell-bowl G-ish.wav |
| [256251](https://freesound.org/people/spectral9/sounds/256251/) | spectral9 | Wine Glass Sustained Note F#6 |
| [271668](https://freesound.org/people/HonorHunter/sounds/271668/) | HonorHunter | Water gush; full.wav |
| [274767](https://freesound.org/people/launemax/sounds/274767/) | launemax | Open and Close an iron gate |
| [352829](https://freesound.org/people/Kinoton/sounds/352829/) | Kinoton | Tomb Door Open, Stone Scrape |
| [389692](https://freesound.org/people/Shamewap/sounds/389692/) | Shamewap | Tiny Hammer on Stone.wav |
| [391448](https://freesound.org/people/saturdaysoundguy/sounds/391448/) | saturdaysoundguy | Shirt Whoosh 1.wav |
| [391794](https://freesound.org/people/Alexbuk/sounds/391794/) | Alexbuk | METAL SFX & FOLEY, Metal slide, clunk and clink (door bolt).wav |
| [418150](https://freesound.org/people/PappaBert/sounds/418150/) | PappaBert | Ringing sound from crystal glass in H (Bb). |
| [419146](https://freesound.org/people/PappaBert/sounds/419146/) | PappaBert | Ringing sound from crystal glass. Tune: C |
| [419147](https://freesound.org/people/PappaBert/sounds/419147/) | PappaBert | Ringing sound from crystal glass. Tune: G |
| [448418](https://freesound.org/people/LordForklift/sounds/448418/) | LordForklift | Metal Slide 2 |
| [454148](https://freesound.org/people/kyles/sounds/454148/) | kyles | ratchet pulley winch pull metal plastic junk slide rattle.flac |
| [457956](https://freesound.org/people/dan.pugsley/sounds/457956/) | dan.pugsley | Waves lapping on rocks |
| [463811](https://freesound.org/people/nate_asdfg/sounds/463811/) | nate_asdfg | Footsteps on Metal Floor |
| [465807](https://freesound.org/people/PaceHeart/sounds/465807/) | PaceHeart | big stone door suddenly slamming shut |
| [495390](https://freesound.org/people/Nox_Sound/sounds/495390/) | Nox_Sound | Foley_Whoosh_Clothes.wav |
| [508178](https://freesound.org/people/Breviceps/sounds/508178/) | Breviceps | Water Pouring Out of Bucket |
| [525029](https://freesound.org/people/bruno.auzet/sounds/525029/) | bruno.auzet | sea from cliff.wav |
| [530987](https://freesound.org/people/patchytherat/sounds/530987/) | patchytherat | stone door close.wav |
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
| [715478](https://freesound.org/people/KVV_Audio/sounds/715478/) | KVV_Audio | MECHRolr_Turning A Wooden Wheel 01_KVV_FREE |
| [734632](https://freesound.org/people/Vrymaa/sounds/734632/) | Vrymaa | Footsteps Sandals - Walk & run |
| [762646](https://freesound.org/people/FOSSarts/sounds/762646/) | FOSSarts | small brass sound bowl strike and ring - 3 |
| [791907](https://freesound.org/people/LePainMaudit/sounds/791907/) | LePainMaudit | Heavy chain |
| [813622](https://freesound.org/people/SecureSubset/sounds/813622/) | SecureSubset | Footsteps - Stone, Rock, Concrete, Cement |
| [844329](https://freesound.org/people/NahuelMartinez/sounds/844329/) | NahuelMartinez | Stone Slab Door Grinding - Heavy Rock Scrape (Mono) |
| [858891](https://freesound.org/people/xtra1/sounds/858891/) | xtra1 | Stone on Stone Hit |
