#include "DysisTimeComponent.h"
#include "DysisSkyActor.h"
#include "DysisSkyLibrary.h"
#include "Components/CapsuleComponent.h"
#include "EngineUtils.h"
#include "GameFramework/Character.h"
#include "GameFramework/CharacterMovementComponent.h"

DEFINE_LOG_CATEGORY_STATIC(LogDysisTime, Log, All);

UDysisTimeComponent::UDysisTimeComponent()
{
	PrimaryComponentTick.bCanEverTick = true;
	PrimaryComponentTick.TickGroup = TG_PostPhysics;   // CharacterMovement 已经更新过脚下的地面
	H = Sticky = UDysisSkyLibrary::DysisConst(TEXT("H_I"));
	Zone = TEXT("out");
}

void UDysisTimeComponent::BeginPlay()
{
	Super::BeginPlay();
	H = Sticky = UDysisSkyLibrary::DysisConst(TEXT("H_I"));
	if (ADysisSkyActor* Sky = ResolveSky()) Sky->SetTime(H);
	if (!SkyActor) UE_LOG(LogDysisTime, Warning, TEXT("DysisTimeComponent: no ADysisSkyActor in the level, only H is computed"));
}

ADysisSkyActor* UDysisTimeComponent::ResolveSky()
{
	if (!SkyActor && GetWorld())
	{
		for (TActorIterator<ADysisSkyActor> It(GetWorld()); It; ++It) { SkyActor = *It; break; }
	}
	return SkyActor;
}

bool UDysisTimeComponent::IsOnGround() const
{
	const ACharacter* Character = Cast<ACharacter>(GetOwner());
	const UCharacterMovementComponent* Move = Character ? Character->GetCharacterMovement() : nullptr;
	return Move && Move->IsMovingOnGround();
}

FVector UDysisTimeComponent::ComputeFoot(const ACharacter* Character) const
{
	// 脚底 = Actor 位置 − (0, 0, 胶囊半高)；灰盒的位置就是脚底，拿胶囊中心去算楼梯和高度判定都会错
	const UCapsuleComponent* Capsule = Character->GetCapsuleComponent();
	FVector Foot = Character->GetActorLocation() - FVector(0.0, 0.0, Capsule->GetScaledCapsuleHalfHeight());
	const UCharacterMovementComponent* Move = Character->GetCharacterMovement();
	if (bFootOnFloorSurface && Move && Move->CurrentFloor.IsWalkableFloor())
	{
		// 灰盒的脚底 = 从人的位置竖直往下打到的那个面（probe：从脚上 0.4 m 往下）。胶囊会悬在地上 ~2 cm，
		// 在楼梯上还会压在上一级踏步的边上，胶囊底落在两级踏面之间；所以竖直往下打一条射线，取正下方的面。
		FHitResult Hit;
		FCollisionQueryParams Params(SCENE_QUERY_STAT(DysisFootProbe), false, Character);
		FCollisionResponseParams Response;
		Capsule->InitSweepCollisionParams(Params, Response);
		const FVector Start = Foot + FVector(0.0, 0.0, 40.0), End = Foot - FVector(0.0, 0.0, 60.0);
		if (GetWorld()->LineTraceSingleByChannel(Hit, Start, End, Capsule->GetCollisionObjectType(), Params, Response))
			Foot.Z = Hit.ImpactPoint.Z;
		else
			Foot.Z -= Move->CurrentFloor.GetDistanceToFloor();   // 正下方是空的（踩在边沿上）：用胶囊底 − 离地距离
	}
	return Foot;
}

void UDysisTimeComponent::TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction)
{
	Super::TickComponent(DeltaTime, TickType, ThisTickFunction);

	const ACharacter* Character = Cast<ACharacter>(GetOwner());
	const UCharacterMovementComponent* Move = Character ? Character->GetCharacterMovement() : nullptr;

	// 灰盒 tick：强制时刻 > 在地上按脚下算 > 空中保持上一刻
	float NewH;
	if (bHasForcedTime)
	{
		NewH = ForcedTime;
	}
	else if (Move && Move->IsMovingOnGround())
	{
		FootCm = ComputeFoot(Character);
		Zone = !ZoneOverride.IsEmpty() ? ZoneOverride : UDysisSkyLibrary::DysisZoneOf(Move->CurrentFloor.HitResult.GetActor(), FootCm);
		NewH = UDysisSkyLibrary::DysisTimeAt(Zone, FootCm, bNight, Sticky);
	}
	else
	{
		NewH = Sticky;   // 跳起、下落：时间不动
	}
	Sticky = NewH;

	const bool bChanged = NewH != H || !bBroadcastedOnce;
	H = NewH;
	if (ADysisSkyActor* Sky = ResolveSky()) Sky->SetTime(H);   // 没有平滑、没有插值：站到哪里就是那一刻
	if (bChanged) { bBroadcastedOnce = true; OnTimeChanged.Broadcast(H); }

	if (PendingReportFrames >= 0 && PendingReportFrames-- == 0)
		UE_LOG(LogDysisTime, Display, TEXT("Dysis.Go %s"), *DescribeState());
}

void UDysisTimeComponent::SetNight(bool bInNight)
{
	if (bInNight && !bNight) Sticky = H;   // 同灰盒 catchLight：state.sticky = state.H
	bNight = bInNight;
}

void UDysisTimeComponent::SetForcedTime(float InH) { bHasForcedTime = true; ForcedTime = InH; }
void UDysisTimeComponent::ClearForcedTime() { bHasForcedTime = false; }
void UDysisTimeComponent::SetZoneOverride(const FString& InZone) { ZoneOverride = InZone; }
void UDysisTimeComponent::ClearZoneOverride() { ZoneOverride.Reset(); }

void UDysisTimeComponent::DebugTeleportFeet(FVector InFootCm, bool bInNight, int32 ReportAfterFrames)
{
	ACharacter* Character = Cast<ACharacter>(GetOwner());
	if (!Character) return;
	SetNight(bInNight);
	const float HalfHeight = Character->GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
	Character->SetActorLocation(InFootCm + FVector(0.0, 0.0, HalfHeight + 2.0), false, nullptr, ETeleportType::TeleportPhysics);
	if (UCharacterMovementComponent* Move = Character->GetCharacterMovement())
	{
		Move->StopMovementImmediately();
		Move->SetMovementMode(MOVE_Falling);   // 落 2 cm 站稳，CharacterMovement 自己找地面
	}
	PendingReportFrames = FMath::Max(ReportAfterFrames, 1);
}

FString UDysisTimeComponent::DescribeState() const
{
	const ADysisSkyActor* Sky = SkyActor;
	const bool bSun = Sky ? Sky->IsSunMain() : true;
	const FRotator R = Sky ? Sky->GetMainLightRotation() : FRotator::ZeroRotator;
	const float Clock = UDysisSkyLibrary::DysisClockHours(H);
	const int32 Minutes = FMath::FloorToInt(FMath::Fmod(Clock, 24.f) * 60.f + 0.5f);
	return FString::Printf(TEXT("zone=%s H=%.4f clock=%02d:%02d main=%s pitch=%.3f yaw=%.3f night=%d ground=%d foot=(%.1f, %.1f, %.1f)"),
		*Zone, H, (Minutes / 60) % 24, Minutes % 60, bSun ? TEXT("sun") : TEXT("moon"), R.Pitch, R.Yaw, bNight ? 1 : 0, IsOnGround() ? 1 : 0,
		FootCm.X, FootCm.Y, FootCm.Z);
}

// ───── 控制台：Dysis.Go <X> <Y> <Z> [night]（UE 厘米，脚底） / Dysis.Where ─────
namespace
{
	UDysisTimeComponent* FindPlayerTime(UWorld* World)
	{
		if (!World) return nullptr;
		for (FConstPlayerControllerIterator It = World->GetPlayerControllerIterator(); It; ++It)
			if (const APawn* Pawn = It->Get() ? It->Get()->GetPawn() : nullptr)
				if (UDysisTimeComponent* T = Pawn->FindComponentByClass<UDysisTimeComponent>()) return T;
		return nullptr;
	}

	FAutoConsoleCommandWithWorldAndArgs GDysisGo(
		TEXT("Dysis.Go"),
		TEXT("Dysis.Go <X> <Y> <Z> [night]：把玩家的脚底传送到 UE 厘米坐标，站稳后打印区域、H、主光、Pitch、Yaw"),
		FConsoleCommandWithWorldAndArgsDelegate::CreateLambda([](const TArray<FString>& Args, UWorld* World)
		{
			UDysisTimeComponent* T = FindPlayerTime(World);
			if (!T || Args.Num() < 3) { UE_LOG(LogDysisTime, Warning, TEXT("Dysis.Go <X> <Y> <Z> [night]（要在 PIE 里、玩家身上有 DysisTimeComponent）")); return; }
			const bool bNightArg = Args.Num() > 3 && Args[3].Equals(TEXT("night"), ESearchCase::IgnoreCase);
			T->DebugTeleportFeet(FVector(FCString::Atod(*Args[0]), FCString::Atod(*Args[1]), FCString::Atod(*Args[2])), bNightArg);
		}));

	FAutoConsoleCommandWithWorldAndArgs GDysisWhere(
		TEXT("Dysis.Where"),
		TEXT("打印玩家现在的区域、H、主光"),
		FConsoleCommandWithWorldAndArgsDelegate::CreateLambda([](const TArray<FString>&, UWorld* World)
		{
			if (UDysisTimeComponent* T = FindPlayerTime(World)) UE_LOG(LogDysisTime, Display, TEXT("Dysis.Where %s"), *T->DescribeState());
		}));
}