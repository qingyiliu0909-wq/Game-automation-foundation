// Fill out your copyright notice in the Description page of Project Settings.

#pragma once

#include "CoreMinimal.h"
#include "UObject/Interface.h"
#include <Blueprint/AIBlueprintHelperLibrary.h>
#include "Navigation/PathFollowingComponent.h"
#include "AITypes.h"
#include "GameFunctionLibrary.generated.h"

// This class does not need to be modified.
UCLASS()
class UGameFunctionLibrary : public UObject
{
	GENERATED_BODY()

public:
	void Tick(float DeltaTime);
	/** 获取当前 World 中的敌人 */
	static void GetMonsters(TArray<AActor*>& Monsters);
	static void GetRecentMonsterLocation(FVector& TargetPos);
	static void AimRotation(float x, float y, float z);

	static UPathFollowingComponent* SimpleMoveToLocation(AController* Controller, const FVector& GoalLocation);

	static FString GetScenePerfFieldStatCommand(const FString& FieldName);
	static void AddAllScenePerfField(TArray<FString>& FieldList, TArray<FString>& StatCommandList);
	static void StartScenePerfStat(UWorld* World, UGameViewportClient* ViewportClient, const TArray<FString>& FieldList, const TArray<FString>& StatCommandList);
	static void StopScenePerfStat(UWorld* World, UGameViewportClient* ViewportClient);
	static bool IsScenePerfStatEnabled() { return bScenePerfStatEnabled; }
	static const TArray<FString>& GetScenePerfFieldList() { return ScenePerfFieldList; }
	static void GetScenePerfValue(UGameViewportClient* ViewportClient, TMap<FString, double>& ScenePerfValueMap);
	static FString GetDeviceInfoJson();
	static bool ShowScreenText(const FString& Text);

	static void StopFollow() { bIsFollow = false; }
	static void StartFollow() { bIsFollow = true; }
	static void StopAim() { bIsAim = false; }
	static void StartAim() { bIsAim = true; }
	static void StopAimMonster() { bIsAimMonster = false; }
	static void StartAimMonster() { bIsAimMonster = true; }
	static void SetAimLocation(FVector Location) { AimLocation = Location; }
	static UPathFollowingComponent* GetPFollowComp() { return PFollowComp; }

private:

	static bool bIsFollow ;
	static bool bIsAim ;
	static bool bIsAimMonster;
	static bool bIsRunJump;
	static bool bIsRunJumping;
	static FVector AimLocation ;
	static TArray <FVector> MonitorLinkPoints;
	static UPathFollowingComponent* PFollowComp ;
	static FAIRequestID MoveRequestID ;
	static bool bScenePerfStatEnabled;
	static TArray<FString> ScenePerfFieldList;
	static TArray<FString> ScenePerfStatCommandList;

	static bool IsScenePerfFieldEnabled(const FString& FieldName);
	static bool IsScenePerfStatCommandEnabled(const FString& StatCommand);
	
};
