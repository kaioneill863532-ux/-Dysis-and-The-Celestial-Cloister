#include "DysisCharacter.h"
#include "Sky/DysisTimeComponent.h"
#include "Camera/CameraComponent.h"
#include "Components/CapsuleComponent.h"
#include "EnhancedInputComponent.h"
#include "EnhancedInputSubsystems.h"
#include "InputAction.h"
#include "InputMappingContext.h"
#include "InputModifiers.h"
#include "Engine/LocalPlayer.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"

ADysisCharacter::ADysisCharacter()
{
	GetCapsuleComponent()->InitCapsuleSize(35.f, 90.f);
	bUseControllerRotationYaw = true;
	bUseControllerRotationPitch = false;
	bUseControllerRotationRoll = false;

	Camera = CreateDefaultSubobject<UCameraComponent>(TEXT("Camera"));
	Camera->SetupAttachment(GetCapsuleComponent());
	Camera->SetRelativeLocation(FVector(0.f, 0.f, 70.f));
	Camera->bUsePawnControlRotation = true;

	Time = CreateDefaultSubobject<UDysisTimeComponent>(TEXT("DysisTime"));

	UCharacterMovementComponent* Move = GetCharacterMovement();
	Move->MaxWalkSpeed = WalkSpeed;
	Move->JumpZVelocity = 480.f;
	Move->AirControl = 0.35f;
}

void ADysisCharacter::PostInitializeComponents()
{
	Super::PostInitializeComponents();

	// 输入在运行时建好，不依赖内容资源
	auto MakeAction = [this](const TCHAR* Name, EInputActionValueType Type)
	{
		UInputAction* A = NewObject<UInputAction>(this, Name);
		A->ValueType = Type;
		return A;
	};
	MoveAction = MakeAction(TEXT("IA_DysisMove"), EInputActionValueType::Axis2D);
	LookAction = MakeAction(TEXT("IA_DysisLook"), EInputActionValueType::Axis2D);
	JumpAction = MakeAction(TEXT("IA_DysisJump"), EInputActionValueType::Boolean);
	RunAction = MakeAction(TEXT("IA_DysisRun"), EInputActionValueType::Boolean);

	Mapping = NewObject<UInputMappingContext>(this, TEXT("IMC_Dysis"));
	auto Swizzle = [this]() { return NewObject<UInputModifierSwizzleAxis>(this); };   // 默认 YXZ：键值放到 Y（前后）
	auto Negate = [this]() { return NewObject<UInputModifierNegate>(this); };
	Mapping->MapKey(MoveAction, EKeys::W).Modifiers.Add(Swizzle());
	{ FEnhancedActionKeyMapping& M = Mapping->MapKey(MoveAction, EKeys::S); M.Modifiers.Add(Swizzle()); M.Modifiers.Add(Negate()); }
	Mapping->MapKey(MoveAction, EKeys::A).Modifiers.Add(Negate());
	Mapping->MapKey(MoveAction, EKeys::D);
	Mapping->MapKey(LookAction, EKeys::Mouse2D);
	Mapping->MapKey(JumpAction, EKeys::SpaceBar);
	Mapping->MapKey(RunAction, EKeys::LeftShift);
}

void ADysisCharacter::PawnClientRestart()
{
	Super::PawnClientRestart();
	if (const APlayerController* PC = Cast<APlayerController>(GetController()))
		if (UEnhancedInputLocalPlayerSubsystem* Sub = ULocalPlayer::GetSubsystem<UEnhancedInputLocalPlayerSubsystem>(PC->GetLocalPlayer()))
			Sub->AddMappingContext(Mapping, 0);
}

void ADysisCharacter::SetupPlayerInputComponent(UInputComponent* PlayerInputComponent)
{
	Super::SetupPlayerInputComponent(PlayerInputComponent);
	if (UEnhancedInputComponent* In = Cast<UEnhancedInputComponent>(PlayerInputComponent))
	{
		In->BindAction(MoveAction, ETriggerEvent::Triggered, this, &ADysisCharacter::Move);
		In->BindAction(LookAction, ETriggerEvent::Triggered, this, &ADysisCharacter::Look);
		In->BindAction(JumpAction, ETriggerEvent::Started, this, &ACharacter::Jump);
		In->BindAction(JumpAction, ETriggerEvent::Completed, this, &ACharacter::StopJumping);
		In->BindAction(RunAction, ETriggerEvent::Started, this, &ADysisCharacter::RunOn);
		In->BindAction(RunAction, ETriggerEvent::Completed, this, &ADysisCharacter::RunOff);
	}
}

void ADysisCharacter::Move(const FInputActionValue& Value)
{
	const FVector2D V = Value.Get<FVector2D>();
	const FRotator Yaw(0.f, GetControlRotation().Yaw, 0.f);
	AddMovementInput(FRotationMatrix(Yaw).GetUnitAxis(EAxis::X), V.Y);
	AddMovementInput(FRotationMatrix(Yaw).GetUnitAxis(EAxis::Y), V.X);
}

void ADysisCharacter::Look(const FInputActionValue& Value)
{
	const FVector2D V = Value.Get<FVector2D>();
	AddControllerYawInput(V.X);
	AddControllerPitchInput(-V.Y);
}

void ADysisCharacter::RunOn() { GetCharacterMovement()->MaxWalkSpeed = RunSpeed; }
void ADysisCharacter::RunOff() { GetCharacterMovement()->MaxWalkSpeed = WalkSpeed; }