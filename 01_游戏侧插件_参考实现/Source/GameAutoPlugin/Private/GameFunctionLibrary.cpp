// Fill out your copyright notice in the Description page of Project Settings.


#include "GameFunctionLibrary.h"
#include <UAutoCore.h>
#include "Kismet/GameplayStatics.h"
#include <Kismet/KismetMathLibrary.h>
#include "NavigationSystem.h"
#include "NavMesh/RecastNavMesh.h"
#include "AIController.h"
#include "Game/GameMode/EMGameState.h"
#include "Char/MonsterCharacter.h"
#include "Misc/App.h"
#include "GenericPlatform/GenericPlatformMemory.h"
#include "Serialization/JsonWriter.h"
#include "Policies/CondensedJsonPrintPolicy.h"
#include "RHI.h"
#include <Stats/StatsData.h>

// Add default functionality here for any IGameFunctionLibrary functions that are not pure virtual.

bool UGameFunctionLibrary::bIsFollow = false;
bool UGameFunctionLibrary::bIsAim = false; 
bool UGameFunctionLibrary::bIsAimMonster = false;
bool UGameFunctionLibrary::bIsRunJump = false;
bool UGameFunctionLibrary::bIsRunJumping = false;
FVector UGameFunctionLibrary::AimLocation = FVector::ZeroVector;
TArray<FVector> UGameFunctionLibrary::MonitorLinkPoints;
UPathFollowingComponent* UGameFunctionLibrary::PFollowComp = nullptr;
FAIRequestID UGameFunctionLibrary::MoveRequestID;
bool UGameFunctionLibrary::bScenePerfStatEnabled = false;
TArray<FString> UGameFunctionLibrary::ScenePerfFieldList;
TArray<FString> UGameFunctionLibrary::ScenePerfStatCommandList;

struct FScenePerfFieldDef
{
	const TCHAR* FieldName;
	const TCHAR* StatCommand;
};

static const FScenePerfFieldDef GScenePerfFieldDefs[] = {
	{ TEXT("fps"), TEXT("Unit") },
	{ TEXT("FrameTime"), TEXT("Unit") },
	{ TEXT("GameThreadTime"), TEXT("Unit") },
	{ TEXT("RenderThreadTime"), TEXT("Unit") },
	{ TEXT("GPUFrameTime"), TEXT("Unit") },
	{ TEXT("RHITTime"), TEXT("Unit") },
	{ TEXT("NiagaraNumSystems"), TEXT("Niagara") },
	{ TEXT("NiagaraNumParticles"), TEXT("Niagara") },
	{ TEXT("NiagaraNumMeshVerts"), TEXT("Niagara") },
	{ TEXT("NiagaraIndirectDraws"), TEXT("Niagara") },
	{ TEXT("RHITriangles"), TEXT("RHI") },
	{ TEXT("RHIDrawPrimitiveCalls"), TEXT("RHI") },
	{ TEXT("RHIDrawCalls"), TEXT("RHI") },
	{ TEXT("RHIPrimitivesDrawn"), TEXT("RHI") },
	{ TEXT("MeshDrawCalls"), TEXT("SceneRendering") },
	{ TEXT("SceneLights"), TEXT("SceneRendering") },
	{ TEXT("STAT_TextureMemory2D"), TEXT("RHI") },
	{ TEXT("STAT_RenderTargetMemory2D"), TEXT("RHI") },
	{ TEXT("STAT_VertexBufferMemory"), TEXT("RHI") },
	{ TEXT("STAT_IndexBufferMemory"), TEXT("RHI") },
	{ TEXT("STAT_RenderTargetMemoryCube"), TEXT("RHI") },
	{ TEXT("STAT_RenderTargetMemory3D"), TEXT("RHI") },
	{ TEXT("STAT_TextureMemoryCube"), TEXT("RHI") },
	{ TEXT("STAT_TextureMemory3D"), TEXT("RHI") },
	{ TEXT("STAT_UniformBufferMemory"), TEXT("RHI") },
	{ TEXT("STAT_StructuredBufferMemory"), TEXT("RHI") },
	{ TEXT("STAT_PixelBufferMemory"), TEXT("RHI") },
	{ TEXT("UsedPhysical"), TEXT("Memory") },
	{ TEXT("PeakUsedPhysical"), TEXT("Memory") },
	{ TEXT("UsedVirtual"), TEXT("Memory") },
	{ TEXT("PeakUsedVirtual"), TEXT("Memory") },
	{ TEXT("AvailablePhysical"), TEXT("Memory") },
	{ TEXT("AvailableVirtual"), TEXT("Memory") },
};

void UGameFunctionLibrary::Tick(float DeltaTime)
{

	if ((GFrameNumber & 0x02) != 0 && MonitorLinkPoints.Num() >= 2)
	{
		UWorld* World = UUAutoCore::Instance()->GetGameWorld();
		APlayerCharacter* PlayerCharacter = Cast<APlayerCharacter>(UGameplayStatics::GetPlayerCharacter(World, 0));
		if (PlayerCharacter)
		{
			FVector PlayerLoc = PlayerCharacter->GetActorLocation();
			if (!bIsRunJump && PFollowComp && FVector::Dist(MonitorLinkPoints[0], PlayerLoc) <= 150)
			{
				PFollowComp->PauseMove(MoveRequestID, EPathFollowingVelocityMode::Reset);
				bIsRunJump = true;
				bIsRunJumping = false;
				return;
			}
			else if (PFollowComp && FVector::Dist(MonitorLinkPoints[1], PlayerLoc) <= 150)
			{
				PFollowComp->ResumeMove(MoveRequestID);
				MonitorLinkPoints.Empty();
				bIsRunJumping = false;
				bIsRunJump = false;
			}
			if (bIsRunJump && !bIsRunJumping)
			{
				FVector LaunchDirection = FVector::ZeroVector;
				UGameplayStatics::SuggestProjectileVelocity_CustomArc(World, LaunchDirection, PlayerLoc, MonitorLinkPoints[1]);
				PlayerCharacter->LaunchCharacter(LaunchDirection + FVector(2, 2, 1100), true, true);
				bIsRunJumping = true;
			}
		}
	}
	
	if (bIsAim || bIsFollow || bIsAimMonster)
	{
		UWorld* World = UUAutoCore::Instance()->GetGameWorld();
		APlayerController* PlayerController = UGameplayStatics::GetPlayerController(World, 0);

		if (!PlayerController)
		{
			return;
		}
		FRotator TargetRotator=FRotator::ZeroRotator;
		if (bIsAimMonster)
		{
			GetRecentMonsterLocation(AimLocation);
		}
		if ((bIsAim || bIsAimMonster) && AimLocation != FVector::ZeroVector)
		{
			const FVector CameraLocation = PlayerController->PlayerCameraManager->GetCameraLocation();
			TargetRotator = UKismetMathLibrary::FindLookAtRotation(CameraLocation, AimLocation);
		}
		else if (bIsFollow)
		{
			APawn* Player = PlayerController->GetPawn();
			if (Player)
			{
				TargetRotator = Player->GetActorRotation();
			}
		}
		if (TargetRotator !=  FRotator::ZeroRotator)
		{
			TargetRotator.Pitch += 10;
			FRotator NewRotator = FMath::RInterpTo(PlayerController->GetControlRotation(), TargetRotator, DeltaTime, 5.0f);
			NewRotator.Roll = 0;
			PlayerController->SetControlRotation(NewRotator);
		}
		else if (bIsAim)
		{
			bIsAim = false;
		}
		
	}
}

void UGameFunctionLibrary::GetMonsters(TArray<AActor*>& Monsters)
{
	Monsters.Reset();
	UWorld* GameWorld = UUAutoCore::Instance()->GetGameWorld();
	if (GameWorld)
	{
		AEMGameState* GameState = Cast<AEMGameState>(GameWorld->GetGameState());
		if (GameState)
		{
			for (auto TempTargetPair : GameState->MonsterMap)
			{
				AMonsterCharacter* T = TempTargetPair.Value;
				if (IsValid(T)&& T->IsActorValidInGame())
				{
					if (T->IsPureMonster() && !T->IsSkillCreature() && !T->IsSummonMonster() && !T->IsDead())
					{
						Monsters.Add(T);
					}
				}
			}
		}
		
	}
}

void UGameFunctionLibrary::GetRecentMonsterLocation(FVector & TargetPos) {

	TargetPos = FVector::ZeroVector;

	APawn* Player = UUAutoCore::Instance()->GetGameWorld()->GetFirstPlayerController()->GetPawn();
	if (Player != nullptr)
	{
		FVector playerPos = Player->GetActorLocation();

		TArray<AActor*> monsters;

		GetMonsters(monsters);
		float closestDist = 10000;
		for (AActor* monster : monsters)
		{
			FVector weakPos = monster->GetActorLocation();
			float dist = FVector::Dist(weakPos, playerPos);
			if (dist < closestDist )
			{
				closestDist = dist;
				TargetPos = weakPos;
			}
		}
	}
}

void UGameFunctionLibrary::AimRotation(float x, float y, float z) {
	FVector LAim = FVector(x, y, z);
	APlayerController* PlayerController = UUAutoCore::Instance()->GetGameWorld()->GetFirstPlayerController();
	if (PlayerController)
	{
		const FVector PawnLocation = PlayerController->GetPawn()->GetActorLocation();
		FRotator ControlRotator = UKismetMathLibrary::MakeRotFromX(LAim -PawnLocation);
		ControlRotator.Yaw-=FMath::RadiansToDegrees(FMath::Atan2(45, FVector::Dist(LAim, PawnLocation)));
		ControlRotator.Pitch += 10;
		ControlRotator.Roll = 0;
		PlayerController->SetControlRotation(ControlRotator);

	}
	
} 


UPathFollowingComponent* InitNavigationControl(AController& Controller)
{
	AAIController* AsAIController = Cast<AAIController>(&Controller);
	UPathFollowingComponent* PathFollowingComp = nullptr;

	if (AsAIController)
	{
		PathFollowingComp = AsAIController->GetPathFollowingComponent();
	}
	else
	{
		PathFollowingComp = Controller.FindComponentByClass<UPathFollowingComponent>();
		if (PathFollowingComp == nullptr)
		{
			PathFollowingComp = NewObject<UPathFollowingComponent>(&Controller);
			PathFollowingComp->RegisterComponentWithWorld(Controller.GetWorld());
			PathFollowingComp->Initialize();
		}
	}

	return PathFollowingComp;
}

UPathFollowingComponent* UGameFunctionLibrary::SimpleMoveToLocation(AController* Controller, const FVector& GoalLocation)
{
	UNavigationSystemV1* NavSys = Controller ? FNavigationSystem::GetCurrent<UNavigationSystemV1>(Controller->GetWorld()) : nullptr;
	if (NavSys == nullptr || Controller == nullptr || Controller->GetPawn() == nullptr)
	{
		UE_LOG(LogNavigation, Warning, TEXT("UNavigationSystemV1::SimpleMoveToActor called for NavSys:%s Controller:%s controlling Pawn:%s (if any of these is None then there's your problem"),
			*GetNameSafe(NavSys), *GetNameSafe(Controller), Controller ? *GetNameSafe(Controller->GetPawn()) : TEXT("NULL"));
		return nullptr;
	}

	PFollowComp = InitNavigationControl(*Controller);

	if (PFollowComp == nullptr)
	{
		return PFollowComp;
	}

	if (!PFollowComp->IsPathFollowingAllowed())
	{
		return PFollowComp;
	}

	const bool bAlreadyAtGoal = PFollowComp->HasReached(GoalLocation, EPathFollowingReachMode::OverlapAgent);

	// script source, keep only one move request at time
	if (PFollowComp->GetStatus() != EPathFollowingStatus::Idle)
	{
		PFollowComp->AbortMove(*NavSys, FPathFollowingResultFlags::ForcedScript | FPathFollowingResultFlags::NewRequest, FAIRequestID::AnyRequest, bAlreadyAtGoal ? EPathFollowingVelocityMode::Reset : EPathFollowingVelocityMode::Keep);
	}

	// script source, keep only one move request at time
	if (PFollowComp->GetStatus() != EPathFollowingStatus::Idle)
	{
		PFollowComp->AbortMove(*NavSys, FPathFollowingResultFlags::ForcedScript | FPathFollowingResultFlags::NewRequest);
	}

	if (bAlreadyAtGoal)
	{
		PFollowComp->RequestMoveWithImmediateFinish(EPathFollowingResult::Success);
	}
	else
	{
		const FVector AgentNavLocation = Controller->GetNavAgentLocation();
		const ANavigationData* NavData = NavSys->GetNavDataForProps(Controller->GetNavAgentPropertiesRef(), AgentNavLocation);
		if (NavData)
		{
			FPathFindingResult Result = NavSys->FindPathSync(FPathFindingQuery(Controller, *NavData, AgentNavLocation, GoalLocation));
			if (Result.IsSuccessful())
			{
				TArray<FNavPathPoint> PathPoints = Result.Path->GetPathPoints();
				for (size_t i = 0; i < PathPoints.Num(); i++)
				{
					if (PathPoints[i].CustomLinkId != 0 && i+1< PathPoints.Num())
					{
						MonitorLinkPoints.Empty();
						MonitorLinkPoints.Add(PathPoints[i].Location);
						MonitorLinkPoints.Add(PathPoints[i + 1].Location);
						bIsRunJump = false;
						break;
					}
				}
				MoveRequestID = PFollowComp->RequestMove(FAIMoveRequest(GoalLocation), Result.Path);
			}
			else if (PFollowComp->GetStatus() != EPathFollowingStatus::Idle)
			{
				PFollowComp->RequestMoveWithImmediateFinish(EPathFollowingResult::Invalid);
			}
		}
	}
	return PFollowComp;
}

FString UGameFunctionLibrary::GetScenePerfFieldStatCommand(const FString& FieldName)
{
	for (const FScenePerfFieldDef& FieldDef : GScenePerfFieldDefs)
	{
		if (FieldName == FieldDef.FieldName)
		{
			return FieldDef.StatCommand;
		}
	}
	return TEXT("");
}

void UGameFunctionLibrary::AddAllScenePerfField(TArray<FString>& FieldList, TArray<FString>& StatCommandList)
{
	for (const FScenePerfFieldDef& FieldDef : GScenePerfFieldDefs)
	{
		if (!FieldList.Contains(FieldDef.FieldName))
		{
			FieldList.Add(FieldDef.FieldName);
		}
		if (!StatCommandList.Contains(FieldDef.StatCommand))
		{
			StatCommandList.Add(FieldDef.StatCommand);
		}
	}
}

bool UGameFunctionLibrary::IsScenePerfFieldEnabled(const FString& FieldName)
{
	return ScenePerfFieldList.Contains(FieldName);
}

bool UGameFunctionLibrary::IsScenePerfStatCommandEnabled(const FString& StatCommand)
{
	return ScenePerfStatCommandList.Contains(StatCommand);
}

void UGameFunctionLibrary::StartScenePerfStat(UWorld* World, UGameViewportClient* ViewportClient, const TArray<FString>& FieldList, const TArray<FString>& StatCommandList)
{
	ScenePerfFieldList = FieldList;
	ScenePerfStatCommandList = StatCommandList;
	for (const FString& StatCommand : ScenePerfStatCommandList)
	{
		GEngine->ExecEngineStat(World, ViewportClient, *(StatCommand + TEXT(" -nodisplay")));
	}
	bScenePerfStatEnabled = true;
}

void UGameFunctionLibrary::StopScenePerfStat(UWorld* World, UGameViewportClient* ViewportClient)
{
	for (const FString& StatCommand : ScenePerfStatCommandList)
	{
		GEngine->ExecEngineStat(World, ViewportClient, *StatCommand);
	}
	bScenePerfStatEnabled = false;
	ScenePerfFieldList.Empty();
	ScenePerfStatCommandList.Empty();
}

void UGameFunctionLibrary::GetScenePerfValue(UGameViewportClient* ViewportClient, TMap<FString, double>& ScenePerfValueMap)
{
	for (const FString& FieldName : ScenePerfFieldList)
	{
		ScenePerfValueMap.Add(FieldName, 0.0);
	}

	if (IsScenePerfStatCommandEnabled(TEXT("Unit")))
	{
		const FStatUnitData* StatUnitData = ViewportClient->GetStatUnitData();
		double FrameTime = 0.0;
		if (StatUnitData != nullptr)
		{
			if (IsScenePerfFieldEnabled(TEXT("RenderThreadTime")))
			{
				ScenePerfValueMap.Add(TEXT("RenderThreadTime"), StatUnitData->RawRenderThreadTime);
			}
			if (IsScenePerfFieldEnabled(TEXT("GameThreadTime")))
			{
				ScenePerfValueMap.Add(TEXT("GameThreadTime"), StatUnitData->RawGameThreadTime);
			}
			FrameTime = StatUnitData->RawFrameTime;
			if (IsScenePerfFieldEnabled(TEXT("FrameTime")))
			{
				ScenePerfValueMap.Add(TEXT("FrameTime"), FrameTime);
			}
			if (IsScenePerfFieldEnabled(TEXT("RHITTime")))
			{
				ScenePerfValueMap.Add(TEXT("RHITTime"), StatUnitData->RawRHITTime);
			}
			if (IsScenePerfFieldEnabled(TEXT("GPUFrameTime")))
			{
				ScenePerfValueMap.Add(TEXT("GPUFrameTime"), StatUnitData->RawGPUFrameTime[0]);
			}
		}
		if (IsScenePerfFieldEnabled(TEXT("fps")) && FrameTime > 0.0)
		{
			ScenePerfValueMap.Add(TEXT("fps"), 1000.0 / FrameTime);
		}
	}

#if STATS
	FGameThreadStatsData* ViewData = FLatestGameThreadStatsData::Get().Latest;
	if (ViewData != nullptr)
	{
		for (int32 GroupIndex = 0; GroupIndex < ViewData->GroupNames.Num(); GroupIndex++)
		{
			const FName GroupName = ViewData->GroupNames[GroupIndex];
			const FActiveStatGroupInfo& StatGroup = ViewData->ActiveStatGroups[GroupIndex];
			if (GroupName == TEXT("STATGROUP_Niagara") && IsScenePerfStatCommandEnabled(TEXT("Niagara")))
			{
				for (int32 CounterIndex = 0; CounterIndex < StatGroup.CountersAggregate.Num(); CounterIndex++)
				{
					const FString StatName = StatGroup.CountersAggregate[CounterIndex].GetShortName().ToString();
					const double StatData = StatGroup.CountersAggregate[CounterIndex].GetValue_double(EComplexStatField::IncAve);
					if (StatName == TEXT("STAT_NiagaraNumSystems") && IsScenePerfFieldEnabled(TEXT("NiagaraNumSystems")))
					{
						ScenePerfValueMap.Add(TEXT("NiagaraNumSystems"), StatData);
					}
					else if (StatName == TEXT("STAT_NiagaraNumParticles") && IsScenePerfFieldEnabled(TEXT("NiagaraNumParticles")))
					{
						ScenePerfValueMap.Add(TEXT("NiagaraNumParticles"), StatData);
					}
					else if (StatName == TEXT("STAT_NiagaraNumMeshVerts") && IsScenePerfFieldEnabled(TEXT("NiagaraNumMeshVerts")))
					{
						ScenePerfValueMap.Add(TEXT("NiagaraNumMeshVerts"), StatData);
					}
					else if (StatName == TEXT("STAT_NiagaraIndirectDraws") && IsScenePerfFieldEnabled(TEXT("NiagaraIndirectDraws")))
					{
						ScenePerfValueMap.Add(TEXT("NiagaraIndirectDraws"), StatData);
					}
				}
			}
			else if (GroupName == TEXT("STATGROUP_RHI") && IsScenePerfStatCommandEnabled(TEXT("RHI")))
			{
				for (int32 CounterIndex = 0; CounterIndex < StatGroup.CountersAggregate.Num(); CounterIndex++)
				{
					const FString StatName = StatGroup.CountersAggregate[CounterIndex].GetShortName().ToString();
					const double StatData = StatGroup.CountersAggregate[CounterIndex].GetValue_double(EComplexStatField::IncAve);
					if (StatName == TEXT("STAT_RHITriangles") && IsScenePerfFieldEnabled(TEXT("RHITriangles")))
					{
						ScenePerfValueMap.Add(TEXT("RHITriangles"), StatData);
					}
					else if (StatName == TEXT("STAT_RHIDrawPrimitiveCalls") && IsScenePerfFieldEnabled(TEXT("RHIDrawPrimitiveCalls")))
					{
						ScenePerfValueMap.Add(TEXT("RHIDrawPrimitiveCalls"), StatData);
					}
				}
				for (const FComplexStatMessage& StatMessage : StatGroup.MemoryAggregate)
				{
					const FString StatName = StatMessage.GetShortName().ToString();
					const double StatData = StatMessage.GetValue_double(EComplexStatField::IncMax);
					if (StatName == TEXT("STAT_TextureMemory2D") && IsScenePerfFieldEnabled(TEXT("STAT_TextureMemory2D")))
					{
						ScenePerfValueMap.Add(TEXT("STAT_TextureMemory2D"), StatData);
					}
					else if (StatName == TEXT("STAT_RenderTargetMemory2D") && IsScenePerfFieldEnabled(TEXT("STAT_RenderTargetMemory2D")))
					{
						ScenePerfValueMap.Add(TEXT("STAT_RenderTargetMemory2D"), StatData);
					}
					else if (StatName == TEXT("STAT_VertexBufferMemory") && IsScenePerfFieldEnabled(TEXT("STAT_VertexBufferMemory")))
					{
						ScenePerfValueMap.Add(TEXT("STAT_VertexBufferMemory"), StatData);
					}
					else if (StatName == TEXT("STAT_IndexBufferMemory") && IsScenePerfFieldEnabled(TEXT("STAT_IndexBufferMemory")))
					{
						ScenePerfValueMap.Add(TEXT("STAT_IndexBufferMemory"), StatData);
					}
					else if (StatName == TEXT("STAT_RenderTargetMemoryCube") && IsScenePerfFieldEnabled(TEXT("STAT_RenderTargetMemoryCube")))
					{
						ScenePerfValueMap.Add(TEXT("STAT_RenderTargetMemoryCube"), StatData);
					}
					else if (StatName == TEXT("STAT_RenderTargetMemory3D") && IsScenePerfFieldEnabled(TEXT("STAT_RenderTargetMemory3D")))
					{
						ScenePerfValueMap.Add(TEXT("STAT_RenderTargetMemory3D"), StatData);
					}
					else if (StatName == TEXT("STAT_TextureMemoryCube") && IsScenePerfFieldEnabled(TEXT("STAT_TextureMemoryCube")))
					{
						ScenePerfValueMap.Add(TEXT("STAT_TextureMemoryCube"), StatData);
					}
					else if (StatName == TEXT("STAT_TextureMemory3D") && IsScenePerfFieldEnabled(TEXT("STAT_TextureMemory3D")))
					{
						ScenePerfValueMap.Add(TEXT("STAT_TextureMemory3D"), StatData);
					}
					else if (StatName == TEXT("STAT_UniformBufferMemory") && IsScenePerfFieldEnabled(TEXT("STAT_UniformBufferMemory")))
					{
						ScenePerfValueMap.Add(TEXT("STAT_UniformBufferMemory"), StatData);
					}
					else if (StatName == TEXT("STAT_StructuredBufferMemory") && IsScenePerfFieldEnabled(TEXT("STAT_StructuredBufferMemory")))
					{
						ScenePerfValueMap.Add(TEXT("STAT_StructuredBufferMemory"), StatData);
					}
					else if (StatName == TEXT("STAT_PixelBufferMemory") && IsScenePerfFieldEnabled(TEXT("STAT_PixelBufferMemory")))
					{
						ScenePerfValueMap.Add(TEXT("STAT_PixelBufferMemory"), StatData);
					}
				}
			}
			else if (GroupName == TEXT("STATGROUP_SceneRendering") && IsScenePerfStatCommandEnabled(TEXT("SceneRendering")))
			{
				for (int32 CounterIndex = 0; CounterIndex < StatGroup.CountersAggregate.Num(); CounterIndex++)
				{
					const FString StatName = StatGroup.CountersAggregate[CounterIndex].GetShortName().ToString();
					const double StatData = StatGroup.CountersAggregate[CounterIndex].GetValue_double(EComplexStatField::IncAve);
					if (StatName == TEXT("STAT_MeshDrawCalls") && IsScenePerfFieldEnabled(TEXT("MeshDrawCalls")))
					{
						ScenePerfValueMap.Add(TEXT("MeshDrawCalls"), StatData);
					}
					else if (StatName == TEXT("STAT_SceneLights") && IsScenePerfFieldEnabled(TEXT("SceneLights")))
					{
						ScenePerfValueMap.Add(TEXT("SceneLights"), StatData);
					}
				}
			}
		}
	}
	if (IsScenePerfStatCommandEnabled(TEXT("RHI")))
	{
		if (IsScenePerfFieldEnabled(TEXT("RHIDrawCalls")))
		{
			ScenePerfValueMap.Add(TEXT("RHIDrawCalls"), GNumDrawCallsRHI[0]);
		}
		if (IsScenePerfFieldEnabled(TEXT("RHIPrimitivesDrawn")))
		{
			ScenePerfValueMap.Add(TEXT("RHIPrimitivesDrawn"), GNumPrimitivesDrawnRHI[0]);
		}
	}
#endif

	if (IsScenePerfStatCommandEnabled(TEXT("Memory")))
	{
		const FPlatformMemoryStats MemoryStats = FPlatformMemory::GetStats();
		if (IsScenePerfFieldEnabled(TEXT("UsedPhysical")))
		{
			ScenePerfValueMap.Add(TEXT("UsedPhysical"), static_cast<double>(MemoryStats.UsedPhysical));
		}
		if (IsScenePerfFieldEnabled(TEXT("PeakUsedPhysical")))
		{
			ScenePerfValueMap.Add(TEXT("PeakUsedPhysical"), static_cast<double>(MemoryStats.PeakUsedPhysical));
		}
		if (IsScenePerfFieldEnabled(TEXT("UsedVirtual")))
		{
			ScenePerfValueMap.Add(TEXT("UsedVirtual"), static_cast<double>(MemoryStats.UsedVirtual));
		}
		if (IsScenePerfFieldEnabled(TEXT("PeakUsedVirtual")))
		{
			ScenePerfValueMap.Add(TEXT("PeakUsedVirtual"), static_cast<double>(MemoryStats.PeakUsedVirtual));
		}
		if (IsScenePerfFieldEnabled(TEXT("AvailablePhysical")))
		{
			ScenePerfValueMap.Add(TEXT("AvailablePhysical"), static_cast<double>(MemoryStats.AvailablePhysical));
		}
		if (IsScenePerfFieldEnabled(TEXT("AvailableVirtual")))
		{
			ScenePerfValueMap.Add(TEXT("AvailableVirtual"), static_cast<double>(MemoryStats.AvailableVirtual));
		}
	}
}

FString UGameFunctionLibrary::GetDeviceInfoJson()
{
	FString OSLabel;
	FString OSVersion;
	FPlatformMisc::GetOSVersions(OSLabel, OSVersion);

	FString JsonStr;
	TSharedRef<TJsonWriter<TCHAR, TCondensedJsonPrintPolicy<TCHAR>>> JsonWriter = TJsonWriterFactory<TCHAR, TCondensedJsonPrintPolicy<TCHAR>>::Create(&JsonStr);
	JsonWriter->WriteObjectStart();
	JsonWriter->WriteValue(TEXT("buildVersion"), FApp::GetBuildVersion());
	JsonWriter->WriteValue(TEXT("primaryGpuBrand"), FPlatformMisc::GetPrimaryGPUBrand());
	JsonWriter->WriteValue(TEXT("cpuBrand"), FPlatformMisc::GetCPUBrand());
	JsonWriter->WriteValue(TEXT("deviceMakeAndModel"), FPlatformMisc::GetDeviceMakeAndModel());
	JsonWriter->WriteValue(TEXT("os"), OSLabel);
	JsonWriter->WriteValue(TEXT("osVersion"), OSVersion);
	JsonWriter->WriteValue(TEXT("graphicsRHI"), FApp::GetGraphicsRHI());
	JsonWriter->WriteValue(TEXT("deviceId"), FPlatformMisc::GetDeviceId());
	JsonWriter->WriteObjectEnd();
	JsonWriter->Close();
	return JsonStr;
}

bool UGameFunctionLibrary::ShowScreenText(const FString& Text)
{
	if (GEngine == nullptr || Text.IsEmpty())
	{
		return false;
	}
	GEngine->AddOnScreenDebugMessage(-1, 5.0f, FColor::Yellow, Text);
	return true;
}

