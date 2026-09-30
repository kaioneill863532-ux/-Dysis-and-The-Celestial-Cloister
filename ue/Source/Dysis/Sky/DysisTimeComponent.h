// 日落回廊 · 挂在玩家 Character 上的时间组件：每帧按脚下区域和脚底位置算时刻 H（灰盒 tick），再把天摆到 H。
#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "DysisTimeComponent.generated.h"

class ADysisSkyActor;
class ACharacter;

DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FDysisTimeChanged, float, H);

UCLASS(ClassGroup = (Dysis), meta = (BlueprintSpawnableComponent))
class DYSIS_API UDysisTimeComponent : public UActorComponent
{
	GENERATED_BODY()

public:
	UDysisTimeComponent();

	// ───── 状态 ─────
	/** 当前时刻（开始时是 H_I，岛上 13:29）。 */
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Dysis|Time")
	float H;

	/** 上一刻的 H（跳起、下落、水里等“时间不动”的地方用它）。 */
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Dysis|Time")
	float Sticky;

	/** 已经接住最后一缕光（夜里）。 */
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Dysis|Time")
	bool bNight = false;

	/** 脚下的区域（最后一次站在地上时判定的）。 */
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Dysis|Time")
	FString Zone;

	/** 最后一次算时间用的脚底位置（UE 厘米）。 */
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Dysis|Time")
	FVector FootCm = FVector::ZeroVector;

	/** 要摆的天。不填就在关卡里找第一个 ADysisSkyActor。 */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Dysis|Time")
	TObjectPtr<ADysisSkyActor> SkyActor;

	/**
	 * 脚底高度取“从脚底竖直往下打到的那个面”，和灰盒一样（灰盒的脚底就是 probe 射线打到的地面）。
	 * 关掉就是“Actor 位置 − 胶囊半高”：会比地面高出 CharacterMovement 悬空的那 ~2 cm，
	 * 在楼梯上胶囊压着上一级踏步的边，胶囊底会落在两级踏面之间。
	 */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Dysis|Time")
	bool bFootOnFloorSurface = true;

	/** 时刻变了就广播（组员的光、机关可以订阅）。 */
	UPROPERTY(BlueprintAssignable, Category = "Dysis|Time")
	FDysisTimeChanged OnTimeChanged;

	// ───── 给组员用的接口 ─────
	/** 变成夜里（接住最后一缕光）的那一刻：Sticky = H，同灰盒 catchLight。 */
	UFUNCTION(BlueprintCallable, Category = "Dysis|Time")
	void SetNight(bool bInNight);

	/** 过场时强制钉住时刻（同灰盒 state.forceH）。 */
	UFUNCTION(BlueprintCallable, Category = "Dysis|Time")
	void SetForcedTime(float InH);

	UFUNCTION(BlueprintCallable, Category = "Dysis|Time")
	void ClearForcedTime();

	UFUNCTION(BlueprintPure, Category = "Dysis|Time")
	bool HasForcedTime() const { return bHasForcedTime; }

	/** 组员的光柱、月石站上去时告诉这里区域名，例如 beam:b1（只在站在地上时生效）。 */
	UFUNCTION(BlueprintCallable, Category = "Dysis|Time")
	void SetZoneOverride(const FString& InZone);

	UFUNCTION(BlueprintCallable, Category = "Dysis|Time")
	void ClearZoneOverride();

	UFUNCTION(BlueprintPure, Category = "Dysis|Time")
	FString GetZoneOverride() const { return ZoneOverride; }

	/** 现在是不是站在地上（CharacterMovement->IsMovingOnGround()）。 */
	UFUNCTION(BlueprintPure, Category = "Dysis|Time")
	bool IsOnGround() const;

	/** 调试 / 测试：把玩家的脚底放到 FootCm，设好昼夜，几帧后在日志里打印区域、H、主光（控制台 Dysis.Go 用它）。 */
	UFUNCTION(BlueprintCallable, Category = "Dysis|Debug")
	void DebugTeleportFeet(FVector InFootCm, bool bInNight, int32 ReportAfterFrames = 8);

	/** 一行文字：区域、H、钟点、主光、Pitch/Yaw、脚底位置。 */
	UFUNCTION(BlueprintPure, Category = "Dysis|Debug")
	FString DescribeState() const;

	virtual void BeginPlay() override;
	virtual void TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction) override;

private:
	ADysisSkyActor* ResolveSky();
	FVector ComputeFoot(const ACharacter* Character) const;

	bool bHasForcedTime = false;
	float ForcedTime = 0.f;
	FString ZoneOverride;
	int32 PendingReportFrames = -1;
	bool bBroadcastedOnce = false;
};