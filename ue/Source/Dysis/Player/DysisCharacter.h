// 日落回廊 · 测试用的第一人称玩家：WASD 走、鼠标看、空格跳、Shift 跑，身上挂着 UDysisTimeComponent。
// 组员有自己的 Character 时，直接把 UDysisTimeComponent 加到那个 Character 上就行，这个类可以不用。
#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Character.h"
#include "DysisCharacter.generated.h"

class UCameraComponent;
class UDysisTimeComponent;
class UInputAction;
class UInputMappingContext;
struct FInputActionValue;

UCLASS()
class DYSIS_API ADysisCharacter : public ACharacter
{
	GENERATED_BODY()

public:
	ADysisCharacter();

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Dysis")
	TObjectPtr<UCameraComponent> Camera;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Dysis")
	TObjectPtr<UDysisTimeComponent> Time;

	UPROPERTY(EditAnywhere, Category = "Dysis")
	float WalkSpeed = 450.f;

	UPROPERTY(EditAnywhere, Category = "Dysis")
	float RunSpeed = 900.f;

	virtual void PostInitializeComponents() override;
	virtual void PawnClientRestart() override;
	virtual void SetupPlayerInputComponent(UInputComponent* PlayerInputComponent) override;

private:
	void Move(const FInputActionValue& Value);
	void Look(const FInputActionValue& Value);
	void RunOn();
	void RunOff();

	UPROPERTY(Transient)
	TObjectPtr<UInputMappingContext> Mapping;

	UPROPERTY(Transient)
	TObjectPtr<UInputAction> MoveAction;

	UPROPERTY(Transient)
	TObjectPtr<UInputAction> LookAction;

	UPROPERTY(Transient)
	TObjectPtr<UInputAction> JumpAction;

	UPROPERTY(Transient)
	TObjectPtr<UInputAction> RunAction;
};