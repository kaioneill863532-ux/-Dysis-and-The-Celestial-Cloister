// 自动生成，不要手改。来源：docs/ue-handoff/golden_time.json（v0.12）。重新生成：python ue/Tools/gen_sky_data.py
#pragma once

#include "CoreMinimal.h"

namespace DysisSkyData
{
	// ───── consts ─────
	inline constexpr double LAT = 35.0;
	inline constexpr double DEC_SUN = -21.0;
	inline constexpr double DEC_MOON = 20.0;
	inline constexpr double F[4] = { 0.0, 6.0, 14.5, 23.0 };
	inline constexpr double CEIL = 29.5;
	inline constexpr double RING_Y = 30.3;
	inline constexpr double SEAM[2] = { 116.0, 140.0 };
	inline constexpr double R_IN = 15.5;
	inline constexpr double R_A = 12.19;
	inline constexpr double TOP_Y = 37.5;
	inline constexpr double H_I = 22.369624;
	inline constexpr double H_B1TOP = 24.6;
	inline constexpr double H_B2TOP = 29.6;
	inline constexpr double H_H0 = 32.5;
	inline constexpr double H_H1 = 35.8;
	inline constexpr double H_X = 30.124322;
	inline constexpr double H_M = 33.5;
	inline constexpr double H_OC = 37.190433;
	inline constexpr double H_TOP = 71.364764;
	inline constexpr double H_J = 76.0;
	inline constexpr double H_L3A = 82.0;
	inline constexpr double H_SW = 102.178372;
	inline constexpr double H_3X = 125.428372;
	inline constexpr double H_G = 160.5952;
	inline constexpr double H_TW = 144.0;
	inline constexpr double H_BR = 194.152981;
	inline constexpr double H_END = 195.652981;
	inline constexpr double RELIEF_H = 31.050616;
	inline constexpr double B1_H = 24.0;
	inline constexpr double B2_H = 29.0;
	inline constexpr double TWINS_Hc = 144.0;
	inline constexpr double TWINS_Hw = 151.4952;
	inline constexpr double MOONBR_H0 = 144.0;
	inline constexpr double MOONBR_H1 = 163.5952;
	inline constexpr double J_AZ = 218.083135;
	inline constexpr double AZ_OC = 38.083135;
	inline constexpr double T_AZ = 34.333135;
	inline constexpr double CATCH_AZ = 27.833135;
	inline constexpr double DN_FOOT = 101.0;
	inline constexpr double LAND[2] = { 219.65499563146398, 227.65499563146398 };
	inline constexpr double UP_TOP[2] = { 26.83313499019505, 41.83313499019505 };
	inline constexpr double UP_SPAN = 162.178139;

	// ───── 每层的时间线：line 沿方位角线性；piece 折线（两头之外保持端点值） ─────
	struct FZoneLine { bool bPiece; double Lo, Hi, A0, H0, K; int32 NumPts; double Pts[8][2]; };
	inline constexpr FZoneLine DayZones[4] = {  // day，下标 = 层号
		{ false, 140.0, 476.0, 382.5, 22.369624, 0.02419406, 0, {} },  // L0
		{ false, 140.0, 476.0, 160.0, 24.6, 0.02312049, 0, {} },  // L1
		{ false, 140.0, 476.0, 254.0, 29.6, 0.01638507, 0, {} },  // L2
		{ false, 140.0, 476.0, 203.40336, 36.0, 0.00611483, 0, {} },  // L3
	};
	inline constexpr FZoneLine NightZones[4] = {  // night，下标 = 层号
		{ true, 140.0, 476.0, 0.0, 0.0, 0.0, 4, { { 382.21297, 195.652981 }, { 407.21297, 193.752981 }, { 457.0, 163.5952 }, { 475.5, 163.5952 } } },  // L0
		{ false, 140.0, 476.0, 250.6, 144.0, -0.072, 0, {} },  // L1
		{ false, 140.0, 476.0, 286.0, 125.428372, -0.02213367, 0, {} },  // L2
		{ false, 140.0, 476.0, 461.0, 82.0, -0.10025424, 0, {} },  // L3
	};

	// ───── 墙里的两段楼梯 ─────
	struct FTunnel { const TCHAR* Id; double ATop, ABot, YTop, YBot, TopDoor, BotDoor; };
	inline constexpr FTunnel Tunnels[2] = {
		{ TEXT("TS"), 257.727998, 323.727998, 23.0, 14.5, 259.727998, 321.727998 },
		{ TEXT("TR"), 180.705205, 110.0, 14.5, 6.0, 178.705205, 112.0 },
	};

	// ───── 光路上按高度插值：[y0, H0, y1, H1] ─────
	struct FBeamTimeY { const TCHAR* Id; double Y0, H0, Y1, H1; };
	inline constexpr FBeamTimeY BeamTimeY[5] = {
		{ TEXT("b1"), 0.0, 24.0, 9.4, 24.6 },
		{ TEXT("b2"), 6.0, 29.0, 18.3, 29.6 },
		{ TEXT("h1"), 14.5, 32.5, 26.4, 35.8 },
		{ TEXT("h2"), 14.5, 32.5, 26.4, 35.8 },
		{ TEXT("h3"), 14.5, 32.5, 26.4, 35.8 },
	};

	// ───── 月桥：沿桥的点（UE 厘米），按最近点的序号插值 ─────
	inline constexpr int32 NumMoonBridgePts = 73;
	inline constexpr double MoonBridgePtsUE[73][3] = {
		{ -321.97, -1201.61, 600.0 },
		{ -279.83, -1188.8, 594.28 },
		{ -238.16, -1174.56, 588.56 },
		{ -196.98, -1158.92, 582.83 },
		{ -156.37, -1141.88, 577.09 },
		{ -116.35, -1123.48, 571.32 },
		{ -76.99, -1103.73, 565.53 },
		{ -38.31, -1082.66, 559.71 },
		{ -0.38, -1060.28, 553.85 },
		{ 36.77, -1036.63, 547.96 },
		{ 73.1, -1011.73, 542.02 },
		{ 108.57, -985.62, 536.04 },
		{ 143.12, -958.31, 530.0 },
		{ 176.73, -929.85, 523.9 },
		{ 209.36, -900.26, 517.75 },
		{ 240.96, -869.58, 511.53 },
		{ 271.5, -837.85, 505.23 },
		{ 300.94, -805.09, 498.87 },
		{ 329.26, -771.36, 492.43 },
		{ 356.42, -736.69, 485.9 },
		{ 382.38, -701.11, 479.3 },
		{ 407.12, -664.67, 472.6 },
		{ 430.6, -627.41, 465.82 },
		{ 452.81, -589.38, 458.94 },
		{ 473.72, -550.62, 451.96 },
		{ 493.3, -511.16, 444.89 },
		{ 511.52, -471.07, 437.71 },
		{ 528.38, -430.38, 430.43 },
		{ 543.84, -389.14, 423.05 },
		{ 557.9, -347.4, 415.56 },
		{ 570.53, -305.21, 407.96 },
		{ 581.72, -262.61, 400.24 },
		{ 591.45, -219.66, 392.42 },
		{ 599.73, -176.4, 384.49 },
		{ 606.53, -132.88, 376.44 },
		{ 611.85, -89.16, 368.28 },
		{ 615.68, -45.29, 360.0 },
		{ 618.02, -1.31, 351.61 },
		{ 618.86, 42.73, 343.11 },
		{ 618.21, 86.76, 334.49 },
		{ 616.07, 130.75, 325.76 },
		{ 612.43, 174.65, 316.91 },
		{ 607.31, 218.39, 307.96 },
		{ 600.7, 261.94, 298.89 },
		{ 592.62, 305.23, 289.71 },
		{ 583.07, 348.23, 280.43 },
		{ 572.07, 390.87, 271.05 },
		{ 559.62, 433.12, 261.55 },
		{ 545.75, 474.92, 251.96 },
		{ 530.47, 516.23, 242.27 },
		{ 513.8, 556.99, 232.48 },
		{ 495.75, 597.17, 222.6 },
		{ 476.35, 636.71, 212.63 },
		{ 455.61, 675.56, 202.57 },
		{ 433.57, 713.69, 192.43 },
		{ 410.25, 751.05, 182.2 },
		{ 385.67, 787.6, 171.9 },
		{ 359.87, 823.29, 161.53 },
		{ 332.87, 858.09, 151.08 },
		{ 304.7, 891.95, 140.57 },
		{ 275.4, 924.83, 130.0 },
		{ 245.0, 956.7, 119.37 },
		{ 213.53, 987.52, 108.69 },
		{ 181.04, 1017.25, 97.96 },
		{ 147.56, 1045.86, 87.19 },
		{ 113.12, 1073.32, 76.38 },
		{ 77.78, 1099.59, 65.53 },
		{ 41.56, 1124.65, 54.65 },
		{ 4.51, 1148.47, 43.75 },
		{ -33.33, 1171.01, 32.83 },
		{ -71.91, 1192.26, 21.9 },
		{ -111.19, 1212.18, 10.95 },
		{ -151.12, 1230.76, 0.0 },
	};
}
