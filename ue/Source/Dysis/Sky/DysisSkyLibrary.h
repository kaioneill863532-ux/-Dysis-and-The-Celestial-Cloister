// 日落回廊 · 日月轨道 + “站在哪里决定几点”。逐函数照 docs/ue-handoff/reference_time.py 翻译，数据来自 DysisSkyData.generated.h。
#pragma once

#include "CoreMinimal.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "DysisSkyLibrary.generated.h"

UCLASS()
class DYSIS_API UDysisSkyLibrary : public UBlueprintFunctionLibrary
{
	GENERATED_BODY()

public:
	/** “没有上一刻”的 Sticky 值。 */
	static constexpr float NoSticky = -999.f;

	/** 太阳方向单位向量（UE 坐标：X=北、Y=东、Z=上）。H 是时角（度），钟点 = 12:00 + H/15。 */
	UFUNCTION(BlueprintPure, Category = "Dysis|Sky")
	static FVector DysisSunDir(float H);

	/** 月亮方向单位向量（时角比太阳晚 180°）。 */
	UFUNCTION(BlueprintPure, Category = "Dysis|Sky")
	static FVector DysisMoonDir(float H);

	/** 平行光朝向：光从 Dir 那边射过来。Pitch = −高度角，Yaw = 方位角 + 180，Roll = 0。 */
	UFUNCTION(BlueprintPure, Category = "Dysis|Sky")
	static FRotator DysisLightRotation(FVector Dir);

	/**
	 * 人踩在 Zone 上、脚底位置是 PosCm（UE 厘米）时的时刻 H。
	 * Sticky = 上一刻的 H；传 −999 表示“没有上一刻”：规则里该用 sticky 的地方原样返回 −999。
	 * bNight = 已经接住最后一缕光：结果夹在 [H_TOP, H_END]（所以夜里 −999 会变成 H_TOP）。
	 */
	UFUNCTION(BlueprintCallable, Category = "Dysis|Sky")
	static float DysisTimeAt(const FString& Zone, FVector PosCm, bool bNight, float Sticky);

	/**
	 * 脚下区域：Ground 上有 Tag “DysisZone=<区域名>” 就用它（墙体是 “DysisZone=wall”，再按半径、方位角分出两段楼梯），
	 * 否则按脚底高度兜底（灰盒 zoneOf 的最后几行）。
	 */
	UFUNCTION(BlueprintPure, Category = "Dysis|Sky")
	static FString DysisZoneOf(const AActor* Ground, FVector FootCm);

	/** 钟点（小时）= 12 + H/15。 */
	UFUNCTION(BlueprintPure, Category = "Dysis|Sky")
	static float DysisClockHours(float H) { return 12.f + H / 15.f; }

	/** 方位角（度，北 0°、顺时针，0–360）和高度角（度）。 */
	UFUNCTION(BlueprintPure, Category = "Dysis|Sky")
	static void DysisAzAlt(FVector Dir, float& AzDeg, float& AltDeg);

	/** 灰盒常数，给组员用（H_I、H_TOP、H_END……）。不认识的名字返回 0 并打警告。 */
	UFUNCTION(BlueprintPure, Category = "Dysis|Sky")
	static float DysisConst(FName Name);

	// C++ 里用的双精度版本
	static FVector SkyDir(double HDeg, double DecDeg);
	static double TimeAtD(const FString& Zone, const FVector& PosCm, bool bNight, double Sticky);
};