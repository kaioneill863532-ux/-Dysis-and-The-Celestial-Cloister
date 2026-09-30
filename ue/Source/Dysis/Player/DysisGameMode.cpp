#include "DysisGameMode.h"
#include "DysisCharacter.h"

ADysisGameMode::ADysisGameMode()
{
	DefaultPawnClass = ADysisCharacter::StaticClass();
}