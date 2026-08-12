// Fill out your copyright notice in the Description page of Project Settings.


#include "GameAPI.h"
#include "GameAutoPlugin.h"
#include "Serialization/JsonWriter.h"
#include "Policies/CondensedJsonPrintPolicy.h"
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "EngineUtils.h"
#include "UAutoCore.h"
#include <GameFunctionLibrary.h>
#include <Combat/Item/MechanismMiniGame.h>
#include <UI/Guide/IndicatorBase.h>
#include "Common/Triggers/AOITriggerBox.h"
#include <Combat/Item/Mechanism/Mechanism/ElevatorMechanismBody.h>
#include "Blueprint/AIBlueprintHelperLibrary.h"
#include "Navigation/PathFollowingComponent.h"
#include "Char/CharacterBase.h"
#include "CaptureStatData.h"
#include "ScenePerfCheck.h"
#include <Combat/Item/PickupProjectile.h>
#include <UAutoRunner.h>
#include "Combat/Buff/BuffManager.h"
#include <Story/TaskGuidePointBase.h>
#include <Char/PlayerCharMoveComp.h>
#include "Char/PlayerCharacter.h"
#include "Game/GameMode/EMGameState.h"
#include "Char/MonsterCharacter.h"
#include <Combat/Item/Mechanism/MoveCompentBase/ElevatorCharacter.h>
FString GameAPI::GetLocation(TArray<FString> Args)
{
	APawn* Player = UUAutoCore::Instance()->GetGameWorld()->GetFirstPlayerController()->GetPawn();
	if (Player != nullptr)
	{
		FVector Location = Player->GetActorLocation();

		FString JsonStr;
		TSharedRef<TJsonWriter<TCHAR, TCondensedJsonPrintPolicy<TCHAR>>> JsonWriter = TJsonWriterFactory<TCHAR,TCondensedJsonPrintPolicy<TCHAR>>::Create(&JsonStr);
		JsonWriter->WriteObjectStart();

		JsonWriter->WriteValue("x", Location.X);
		JsonWriter->WriteValue("y", Location.Y);
		JsonWriter->WriteValue("z", Location.Z);

		JsonWriter->WriteObjectEnd();
		JsonWriter->Close();

		return JsonStr;
	}

	return "error:noPlayer";
	
}
FString GameAPI::SetLocation(TArray<FString> Args)
{
	if (Args.Num() < 4) { return "error:incorrectNumberOfParameters"; }
	APawn* Player = UUAutoCore::Instance()->GetGameWorld()->GetFirstPlayerController()->GetPawn();
	if (Player != nullptr)
	{
		Player->SetActorLocation(FVector(FCString::Atof(*Args[1]), FCString::Atof(*Args[2]), FCString::Atof(*Args[3])));
		return "true";
	}

	return "error:noPlayer";
}
FString GameAPI::SetPawnRotation(TArray<FString> Args)
{
	if (Args.Num() < 4) { return "error:incorrectNumberOfParameters"; }
	APawn* Player = UUAutoCore::Instance()->GetGameWorld()->GetFirstPlayerController()->GetPawn();
	if (Player != nullptr)
	{
		Player->SetActorRotation(FRotator(FCString::Atof(*Args[1]), FCString::Atof(*Args[2]), FCString::Atof(*Args[3])));
		return "true";
	}

	return "error:noPlayer";
}


FString GameAPI::GetPawnRotation(TArray<FString> Args)
{
	APawn* Player = UUAutoCore::Instance()->GetGameWorld()->GetFirstPlayerController()->GetPawn();
	if (Player != nullptr)
	{
		FRotator Rotator = Player->GetActorRotation();

		FString JsonStr;
		TSharedRef<TJsonWriter<TCHAR, TCondensedJsonPrintPolicy<TCHAR>>> JsonWriter = TJsonWriterFactory<TCHAR, TCondensedJsonPrintPolicy<TCHAR>>::Create(&JsonStr);
		JsonWriter->WriteObjectStart();

		JsonWriter->WriteValue("p", Rotator.Pitch);
		JsonWriter->WriteValue("y", Rotator.Yaw);
		JsonWriter->WriteValue("r", Rotator.Roll);

		JsonWriter->WriteObjectEnd();
		JsonWriter->Close();

		return JsonStr;
	}

	return "error:noPlayer";

}
FString GameAPI::SetControlRotation(TArray<FString> Args)
{
	if (Args.Num() < 4) { return "error:incorrectNumberOfParameters"; }
	APlayerController* Controller = UUAutoCore::Instance()->GetGameWorld()->GetFirstPlayerController();
	if (Controller != nullptr)
	{
		Controller->SetControlRotation(FRotator(FCString::Atof(*Args[1]), FCString::Atof(*Args[2]), FCString::Atof(*Args[3])));
		return "true";
	}

	return "error:noPlayer";
}

FString GameAPI::GetControlRotation(TArray<FString> Args)
{
	APlayerController* Controller = UUAutoCore::Instance()->GetGameWorld()->GetFirstPlayerController();
	if (Controller != nullptr)
	{
		FRotator Rotator = Controller->GetControlRotation();

		FString JsonStr;
		TSharedRef<TJsonWriter<TCHAR, TCondensedJsonPrintPolicy<TCHAR>>> JsonWriter = TJsonWriterFactory<TCHAR, TCondensedJsonPrintPolicy<TCHAR>>::Create(&JsonStr);
		JsonWriter->WriteObjectStart();

		JsonWriter->WriteValue("p", Rotator.Pitch);
		JsonWriter->WriteValue("y", Rotator.Yaw);
		JsonWriter->WriteValue("r", Rotator.Roll);

		JsonWriter->WriteObjectEnd();
		JsonWriter->Close();

		return JsonStr;
	}

	return "error:noPlayer";

}


//查找怪物
FString GameAPI::FindMonsterLocation(TArray<FString> Args) {
	FVector TargetPos;
	UGameFunctionLibrary::GetRecentMonsterLocation(TargetPos);
	if (TargetPos.IsZero())
	{
		return "error:no monsters";
	}
	FString JsonStr;
	TSharedRef<TJsonWriter<TCHAR, TCondensedJsonPrintPolicy<TCHAR>>> JsonWriter = TJsonWriterFactory<TCHAR, TCondensedJsonPrintPolicy<TCHAR>>::Create(&JsonStr);
	JsonWriter->WriteObjectStart();

	JsonWriter->WriteValue("x", TargetPos.X);
	JsonWriter->WriteValue("y", TargetPos.Y);
	JsonWriter->WriteValue("z", TargetPos.Z);

	JsonWriter->WriteObjectEnd();
	JsonWriter->Close();

	return JsonStr;
}

//查找怪物
FString GameAPI::FindLongCaoMonster(TArray<FString> Args) {

	TArray<AActor*> monsters;
	UGameFunctionLibrary::GetMonsters(monsters);
	FString JsonStr;
	TSharedRef<TJsonWriter<TCHAR, TCondensedJsonPrintPolicy<TCHAR>>> JsonWriter = TJsonWriterFactory<TCHAR, TCondensedJsonPrintPolicy<TCHAR>>::Create(&JsonStr);
	JsonWriter->WriteArrayStart();
	for (AActor* monster : monsters)
	{
		FVector MLoc = monster->GetActorLocation();
		JsonWriter->WriteObjectStart();
		AMonsterCharacter* Monster = Cast<AMonsterCharacter>(monster);
		if (Monster!=nullptr)
		{
			FString BuffName = "";
			for (auto item : Monster->GetBuffManager()->Buffs) {
				BuffName += FString::FromInt(item.Buff->BuffId) + ";";
			}
			JsonWriter->WriteValue("buffs", BuffName);
		}
		
		JsonWriter->WriteValue("x", MLoc.X);
		JsonWriter->WriteValue("y", MLoc.Y);
		JsonWriter->WriteValue("z", MLoc.Z);

		JsonWriter->WriteObjectEnd();
	}
	

	JsonWriter->WriteArrayEnd();
	JsonWriter->Close();

	return JsonStr;
}

FString GameAPI::SetAimRotation(TArray<FString> Args)
{
	if (Args.Num() < 4) { return "error:incorrectNumberOfParameters"; }
	UGameFunctionLibrary::AimRotation(FCString::Atof(*Args[1]), FCString::Atof(*Args[2]), FCString::Atof(*Args[3]));

	return "success";
}

FString GameAPI::FindMonsterAndAim(TArray<FString> Args) {
	FVector TargetPos;
	UGameFunctionLibrary::GetRecentMonsterLocation(TargetPos);
	if (TargetPos.IsZero())
	{
		return "Not Find Monster";
	}
	UGameFunctionLibrary::AimRotation(TargetPos.X, TargetPos.Y, TargetPos.Z);
	return "success";
}

FString GameAPI::UnlockMiniGames(TArray<FString> Args) {
	UWorld* GameWorld = UUAutoCore::Instance()->GetGameWorld();
	if (GameWorld)
	{
		// 加载蓝图类资源
		UClass* MiniGameClass = LoadClass<AActor>(NULL, TEXT("Blueprint'/Game/BluePrints/Item/MiniGame/BP_MiniGameBase.BP_MiniGameBase_C'"));
		if (MiniGameClass != NULL)
		{
			for (TActorIterator<AActor> It(GameWorld, MiniGameClass); It; ++It)
			{
				AActor* MiniGame = *It;
				if (MiniGame)
				{
					AMechanismMiniGame* MechanismMiniGame = Cast<AMechanismMiniGame>(MiniGame);
					MechanismMiniGame->AlwaysSuccess = true;
				}
			}
		}
	}
	return "success";
}

FString GameAPI::GetBlueprintActorLoc(TArray<FString> Args)
{
	if (Args.Num() < 2) { return "error:incorrectNumberOfParameters"; }
	FString JsonStr;
	TSharedRef<TJsonWriter<TCHAR, TCondensedJsonPrintPolicy<TCHAR>>> JsonWriter = TJsonWriterFactory<TCHAR, TCondensedJsonPrintPolicy<TCHAR>>::Create(&JsonStr);

	FVector Loc = FVector::ZeroVector;
	UWorld* GameWorld = UUAutoCore::Instance()->GetGameWorld();
	if (GameWorld)
	{
		UClass* BallClass = LoadClass<AActor>(NULL, *Args[1]);
		if (BallClass != NULL)
		{
			JsonWriter->WriteArrayStart();
			for (TActorIterator<AActor> It(GameWorld, BallClass); It; ++It)
			{
				AActor* ABatNew = *It;
				if (ABatNew)
				{
					Loc = ABatNew->GetActorLocation();
					JsonWriter->WriteObjectStart();
					JsonWriter->WriteValue("name", ABatNew->GetFName().ToString());
					JsonWriter->WriteValue("x", Loc.X);
					JsonWriter->WriteValue("y", Loc.Y);
					JsonWriter->WriteValue("z", Loc.Z);
					JsonWriter->WriteObjectEnd();
				}
			}
			JsonWriter->WriteArrayEnd();
		}
	}
	JsonWriter->Close();
	return JsonStr;
}

FString GameAPI::SetBlueprintActorLoc(TArray<FString> Args)
{

	if (Args.Num() < 6) { return "error:incorrectNumberOfParameters"; }

	UWorld* GameWorld = UUAutoCore::Instance()->GetGameWorld();
	if (GameWorld)
	{
		UClass* BallClass = LoadClass<AActor>(NULL, *Args[1]);
		if (BallClass != NULL)
		{
			for (TActorIterator<AActor> It(GameWorld, BallClass); It; ++It)
			{
				AActor* ABatNew = *It;
				if (ABatNew)
				{
					if (ABatNew->GetFName().ToString()== Args[2])
					{
						ABatNew->SetActorLocation(FVector(FCString::Atof(*Args[3]), FCString::Atof(*Args[4]), FCString::Atof(*Args[5])));
						return "true";
					}
				}
			}
		}
	};
	return "false";
}

FString GameAPI::SetBlueprintActorMeshLoc(TArray<FString> Args)
{

	if (Args.Num() < 7) { return "error:incorrectNumberOfParameters"; }

	UWorld* GameWorld = UUAutoCore::Instance()->GetGameWorld();
	if (GameWorld)
	{
		UClass* BallClass = LoadClass<AActor>(NULL, *Args[1]);
		if (BallClass != NULL)
		{
			for (TActorIterator<AActor> It(GameWorld, BallClass); It; ++It)
			{
				AActor* ABatNew = *It;
				if (ABatNew)
				{
					if (ABatNew->GetFName().ToString() == Args[2])
					{
						UStaticMeshComponent* Component =Cast<UStaticMeshComponent>(ABatNew->GetDefaultSubobjectByName(*Args[3]));
						if (Component)
						{
							Component->SetWorldLocation(FVector(FCString::Atof(*Args[4]), FCString::Atof(*Args[5]), FCString::Atof(*Args[6])));
							break;
						}
						return "true";
					}
				}
			}
		}
	};
	return "false";
}


FString GameAPI::GetMechanismLoc(TArray<FString> Args) {

	FString JsonStr;
	TSharedRef<TJsonWriter<TCHAR, TCondensedJsonPrintPolicy<TCHAR>>> JsonWriter = TJsonWriterFactory<TCHAR, TCondensedJsonPrintPolicy<TCHAR>>::Create(&JsonStr);

	FVector Loc = FVector::ZeroVector;
	UWorld* GameWorld = UUAutoCore::Instance()->GetGameWorld();
	TArray<AActor*> Mechanisms;
	if (GameWorld)
	{
		APawn* Player = GameWorld->GetFirstPlayerController()->GetPawn();
		if (Player)
		{
			for (TObjectIterator<AMechanismMiniGame> It; It; ++It){Mechanisms.Add(*It);}
			for (TObjectIterator<AElevatorMechanismBody> It; It; ++It){Mechanisms.Add(*It);}
			for (TObjectIterator<AElevatorCharacter> It; It; ++It){Mechanisms.Add(*It);}
			JsonWriter->WriteArrayStart();
			for (AActor* mechanism : Mechanisms)
			{
				Loc = mechanism->GetActorLocation();
				JsonWriter->WriteObjectStart();
				JsonWriter->WriteValue("name", mechanism->GetFName().ToString());
				JsonWriter->WriteValue("x", Loc.X);
				JsonWriter->WriteValue("y", Loc.Y);
				JsonWriter->WriteValue("z", Loc.Z);
				JsonWriter->WriteValue("distance", FMath::RoundToInt(FVector::Dist(Player->GetActorLocation(), Loc)));
				JsonWriter->WriteObjectEnd();
			}
		}
		JsonWriter->WriteArrayEnd();
	}
	JsonWriter->Close();
	return JsonStr;
}

FString GameAPI::GetMechanismMaps(TArray<FString> Args) {

	FString JsonStr;
	TSharedRef<TJsonWriter<TCHAR, TCondensedJsonPrintPolicy<TCHAR>>> JsonWriter = TJsonWriterFactory<TCHAR, TCondensedJsonPrintPolicy<TCHAR>>::Create(&JsonStr);

	FVector Loc = FVector::ZeroVector;
	UWorld* GameWorld = UUAutoCore::Instance()->GetGameWorld();
	if (GameWorld)
	{
		JsonWriter->WriteArrayStart();
		
		AEMGameState* GameState = Cast<AEMGameState>(GameWorld->GetGameState());
		if (GameState)
		{
			for (auto MapName : GameState->MechanismMap)
			{
				if (Args[1] == "&")
				{
					JsonWriter->WriteValue(MapName.Key);
				}
				else if (MapName.Key == Args[1])
				{
					for (auto MapItem : MapName.Value.Array)
					{
						AActor* AMapItem = Cast<AActor>(MapItem);
						if (AMapItem)
						{
							JsonWriter->WriteObjectStart();
							Loc = AMapItem->GetActorLocation();
							JsonWriter->WriteValue("name", MapItem->GetFName().ToString());
							JsonWriter->WriteValue("x", Loc.X);
							JsonWriter->WriteValue("y", Loc.Y);
							JsonWriter->WriteValue("z", Loc.Z);
							JsonWriter->WriteObjectEnd();
						}
					}
					break;
				}
			}
		}
		JsonWriter->WriteArrayEnd();
	}
	JsonWriter->Close();
	return JsonStr;
}

FString GameAPI::GetProjectileLoc(TArray<FString> Args) {

	FString JsonStr;
	TSharedRef<TJsonWriter<TCHAR, TCondensedJsonPrintPolicy<TCHAR>>> JsonWriter = TJsonWriterFactory<TCHAR, TCondensedJsonPrintPolicy<TCHAR>>::Create(&JsonStr);

	FVector Loc = FVector::ZeroVector;
	UWorld* GameWorld = UUAutoCore::Instance()->GetGameWorld();
	if (GameWorld)
	{
		// 加载蓝图类资源
		UClass* BatNewClass = LoadClass<AActor>(NULL, TEXT("Blueprint'/Game/AssetDesign/Item/Pickups/AutoPick/BatNew.BatNew_C'"));
		if (BatNewClass != NULL)
		{
			JsonWriter->WriteArrayStart();
			for (TActorIterator<AActor> It(GameWorld, BatNewClass); It; ++It)
			{
				AActor* ABatNew = *It;
				if (ABatNew)
				{
					APickupProjectile* AProjectile = Cast<APickupProjectile>(ABatNew);
					Loc = AProjectile->GetActorLocation();
					if (Loc.X== 100000){continue;}
					JsonWriter->WriteObjectStart();
					JsonWriter->WriteValue("name", AProjectile->GetFName().ToString());
					JsonWriter->WriteValue("x", Loc.X);
					JsonWriter->WriteValue("y", Loc.Y);
					JsonWriter->WriteValue("z", Loc.Z);
					JsonWriter->WriteObjectEnd();
				}
			}
			JsonWriter->WriteArrayEnd();
		}
	}
	JsonWriter->Close();
	return JsonStr;
}

FString GameAPI::GetIndicatorLoc(TArray<FString> Args) {
	FString JsonStr;
	TSharedRef<TJsonWriter<TCHAR, TCondensedJsonPrintPolicy<TCHAR>>> JsonWriter = TJsonWriterFactory<TCHAR, TCondensedJsonPrintPolicy<TCHAR>>::Create(&JsonStr);
	JsonWriter->WriteArrayStart();
	FVector Loc = FVector(0, 0, 0);
	for (TObjectIterator<UIndicatorBase> It; It; ++It)
	{
		UIndicatorBase* CurrentObject = *It;
		Loc = CurrentObject->CurrentWorldLoc;
		if (!Loc.IsZero() && CurrentObject->IsVisible())
		{
			JsonWriter->WriteObjectStart();
			JsonWriter->WriteValue("name", CurrentObject->GetFName().ToString());
			JsonWriter->WriteValue("ondoor", CurrentObject->IndicatorState == EIndicatorState::OnDoor);
			JsonWriter->WriteValue("distance", CurrentObject->PointRealDistance);
			JsonWriter->WriteValue("type", CurrentObject->GuideType.ToString());
			JsonWriter->WriteValue("x", Loc.X);
			JsonWriter->WriteValue("y", Loc.Y);
			JsonWriter->WriteValue("z", Loc.Z);
			JsonWriter->WriteObjectEnd();
		}
	}

	JsonWriter->WriteArrayEnd();
	JsonWriter->Close();
	return JsonStr;
}

FString GameAPI::GetInteractiveLoc(TArray<FString> Args) {
	FString JsonStr;
	TSharedRef<TJsonWriter<TCHAR, TCondensedJsonPrintPolicy<TCHAR>>> JsonWriter = TJsonWriterFactory<TCHAR, TCondensedJsonPrintPolicy<TCHAR>>::Create(&JsonStr);
	FVector Loc = FVector::ZeroVector;
	UWorld* GameWorld = UUAutoCore::Instance()->GetGameWorld();
	AActor* PlayerActor = UGameplayStatics::GetPlayerCharacter(GameWorld, 0);
	if (GameWorld)
	{
		JsonWriter->WriteArrayStart();
		for (TObjectIterator<UInteractiveBaseComponent> It; It; ++It)
		{
			if (It)
			{
				if (Args[1]!="&" && !It->GetFName().ToString().Contains(Args[1])){continue;}
				Loc = It->GetComponentLocation();
				if (Loc.X == 0 || Loc.X== 100000) { continue; }
				JsonWriter->WriteObjectStart();
				JsonWriter->WriteValue("name", It->GetFName().ToString());
				JsonWriter->WriteValue("IsCanInteractive", It->IsCanInteractive(PlayerActor));
				JsonWriter->WriteValue("x", Loc.X);
				JsonWriter->WriteValue("y", Loc.Y);
				JsonWriter->WriteValue("z", Loc.Z);
				JsonWriter->WriteObjectEnd();
			}
		}
		JsonWriter->WriteArrayEnd();
	}
	JsonWriter->Close();
	return JsonStr;
}


FString GameAPI::GetTaskIndicatorLoc(TArray<FString> Args) {
	FString JsonStr;
	TSharedRef<TJsonWriter<TCHAR, TCondensedJsonPrintPolicy<TCHAR>>> JsonWriter = TJsonWriterFactory<TCHAR, TCondensedJsonPrintPolicy<TCHAR>>::Create(&JsonStr);
	FVector Loc = FVector::ZeroVector;

	JsonWriter->WriteArrayStart();
	for (TObjectIterator<UTaskGuidePointBase> It; It; ++It)
	{
		UTaskGuidePointBase* CurrentObject = *It;
		Loc = CurrentObject->TargetPointPos;
		if (!Loc.IsZero() && CurrentObject->Visibility != ESlateVisibility::Collapsed)
		{
			JsonWriter->WriteObjectStart();
			JsonWriter->WriteValue("name", CurrentObject->TargetPointName.ToString());;
			JsonWriter->WriteValue("distance", CurrentObject->PointRealDistance);
			JsonWriter->WriteValue("x", Loc.X);
			JsonWriter->WriteValue("y", Loc.Y);
			JsonWriter->WriteValue("z", Loc.Z);
			JsonWriter->WriteObjectEnd();
		}
	}
	JsonWriter->WriteArrayEnd();
	
	JsonWriter->Close();
	return JsonStr;
}


FString GameAPI::MoveToHandler(TArray<FString> Args) 
{
	if (Args.Num() < 4) { return "error:incorrectNumberOfParameters"; }
	FVector DirVector = FVector(FCString::Atof(*Args[1]), FCString::Atof(*Args[2]), FCString::Atof(*Args[3]));

	UWorld* World = UUAutoCore::Instance()->GetGameWorld();
	APlayerController* PlayerController = Cast<APlayerController>(UGameplayStatics::GetPlayerController(World, 0));
	// 寻路
	if (PlayerController && PlayerController->GetPawn())
	{
		if (Args.Num()>=5 && Args[4]=="old")
		{
			UAIBlueprintHelperLibrary::SimpleMoveToLocation(PlayerController, DirVector);
		}
		else {
			UGameFunctionLibrary::SimpleMoveToLocation(PlayerController, DirVector);
		}
		
	}
	return "success";
}


FString GameAPI::IsMoveHandler(TArray<FString> Args)
{
	UPathFollowingComponent* PFollowComp = UGameFunctionLibrary::GetPFollowComp();
	if (PFollowComp != nullptr )
	{
		if (PFollowComp->DidMoveReachGoal())
		{
			return "0";
		}
		return "1";
	}
	return "0";
}

float NormalWalkSpeed = 0;
float CrouchWalkSpeed = 0;
FString GameAPI::SetMoveSpeedHandler(TArray<FString> Args)
{
	UWorld* World = UUAutoCore::Instance()->GetGameWorld(); 
	ACharacterBase* PlayerOwner = Cast<ACharacterBase>(UGameplayStatics::GetPlayerCharacter(World, 0));
	if (PlayerOwner)
	{
		if (NormalWalkSpeed == 0)
		{
			NormalWalkSpeed = PlayerOwner->PlayerSlideAtttirbute.NormalWalkSpeed;
			CrouchWalkSpeed = PlayerOwner->PlayerSlideAtttirbute.CrouchWalkSpeed;
		}
		PlayerOwner->PlayerSlideAtttirbute.NormalWalkSpeed = NormalWalkSpeed * FCString::Atof(*Args[1]);
		PlayerOwner->PlayerSlideAtttirbute.CrouchWalkSpeed = CrouchWalkSpeed * FCString::Atof(*Args[1]);
		return "success";
	}
	return "fail";
	
	
}
FString GameAPI::CameraFollowHandler(TArray<FString> Args)
{
	if (Args[1]=="1")
	{
		UGameFunctionLibrary::StartFollow();
		return "1";
	}
	UGameFunctionLibrary::StopFollow();
	return "0";
}

FString GameAPI::AimMonsterHandler(TArray<FString> Args)
{
	if (Args[1] == "1")
	{
		UGameFunctionLibrary::StartAimMonster();
		return "1";
	}
	UGameFunctionLibrary::StopAimMonster();
	return "0";
}

FString GameAPI::CaptureStatHandler(TArray<FString> Args)
{
#if !STATS
	return "-1";
#endif
	if (Args[1] == "-1")
	{
		CaptureStatData::Get()->Prepare(Args);
		return "1";
	}
	else if (Args[1] == "1")
	{
		CaptureStatData::Get()->Start();
		return "1";
	}
	else if(Args[1] == "0") {
		CaptureStatData::Get()->Stop();
		
		return CaptureStatData::Get()->GetReportFile();
	}
	else if (Args[1] == "AddLabel")
	{
		CaptureStatData::Get()->LabelName = Args[2];
		return "1";
	}
	else if (Args[1] == "AddLabelAndCMD")
	{
		if (UAutoRunner::CheckIsShipping())
		{
			return "error:BuildIsShipping";
		}
		UE_LOG(LogUAuto, Log, TEXT("UAuto ExecuteConsoleCommand: %s"), *Args[3]);
		CaptureStatData::Get()->LabelName = Args[2];
		UKismetSystemLibrary::ExecuteConsoleCommand(UUAutoCore::Instance()->GetGameWorld(), Args[3]);
		return "1";
		
	}
	return "-2";
	
}

FString GameAPI::ScenePerfCheckHandler(TArray<FString> Args)
{

	if (Args[1] == "1")
	{
		if (Args.Num()>=2) {
			ScenePerfCheck::Get()->DistanceIntervals = FCString::Atof(*Args[2]);
		}
		ScenePerfCheck::Get()->Start();
		return "1";
	}
	else if (Args[1] == "2"){
		if (!ScenePerfCheck::Get()->Is_Running)
		{
			return ScenePerfCheck::Get()->GetReportFile();
		}
		else {
			return FString::FromInt(ScenePerfCheck::Get()->GetProgress());
		}
		//return "1";
	}
	else if(Args[1] == "-1")
	{
		//强制停止
		ScenePerfCheck::Get()->Stop();
		return ScenePerfCheck::Get()->GetReportFile();
	}
	return "-2";

}

FString GameAPI::GetScenePerfData(TArray<FString> Args)
{
	UWorld* World = UUAutoCore::Instance()->GetGameWorld();
	if (World == nullptr)
	{
		return "error:worldNull";
	}

	UGameViewportClient* ViewportClient = World->GetGameViewport();
	if (ViewportClient == nullptr)
	{
		return "error:viewportClientNull";
	}

	if (Args.Num() > 1 && Args[1] == "fields")
	{
		FString JsonStr;
		TSharedRef<TJsonWriter<TCHAR, TCondensedJsonPrintPolicy<TCHAR>>> JsonWriter = TJsonWriterFactory<TCHAR, TCondensedJsonPrintPolicy<TCHAR>>::Create(&JsonStr);
		JsonWriter->WriteObjectStart();
		JsonWriter->WriteArrayStart(TEXT("fields"));

		TArray<FString> AllFieldList;
		TArray<FString> AllStatCommandList;
		UGameFunctionLibrary::AddAllScenePerfField(AllFieldList, AllStatCommandList);
		for (const FString& FieldName : AllFieldList)
		{
			JsonWriter->WriteObjectStart();
			JsonWriter->WriteValue(TEXT("name"), FieldName);
			JsonWriter->WriteValue(TEXT("stat"), UGameFunctionLibrary::GetScenePerfFieldStatCommand(FieldName));
			JsonWriter->WriteObjectEnd();
		}

		JsonWriter->WriteArrayEnd();
		JsonWriter->WriteObjectEnd();
		JsonWriter->Close();
		return JsonStr;
	}

	if (Args.Num() > 1 && Args[1] == "start")
	{
		TArray<FString> FieldList;
		TArray<FString> StatCommandList;
		bool HasValidMetricArg = false;
		if (Args.Num() <= 2)
		{
			UGameFunctionLibrary::AddAllScenePerfField(FieldList, StatCommandList);
		}
		else
		{
			for (int32 Index = 2; Index < Args.Num(); Index++)
			{
				FString MetricName = Args[Index].TrimStartAndEnd();
				if (MetricName.IsEmpty() || MetricName == TEXT("&"))
				{
					continue;
				}
				HasValidMetricArg = true;
				if (UGameFunctionLibrary::GetScenePerfFieldStatCommand(MetricName).IsEmpty())
				{
					return "error:invalidPerfField:" + MetricName;
				}
				if (!FieldList.Contains(MetricName))
				{
					FieldList.Add(MetricName);
				}
				const FString StatCommand = UGameFunctionLibrary::GetScenePerfFieldStatCommand(MetricName);
				if (!StatCommandList.Contains(StatCommand))
				{
					StatCommandList.Add(StatCommand);
				}
			}
			if (!HasValidMetricArg)
			{
				UGameFunctionLibrary::AddAllScenePerfField(FieldList, StatCommandList);
			}
		}

		if (FieldList.Num() == 0)
		{
			return "error:emptyPerfFields";
		}

		UGameFunctionLibrary::StartScenePerfStat(World, ViewportClient, FieldList, StatCommandList);
		FString JsonStr;
		TSharedRef<TJsonWriter<TCHAR, TCondensedJsonPrintPolicy<TCHAR>>> JsonWriter = TJsonWriterFactory<TCHAR, TCondensedJsonPrintPolicy<TCHAR>>::Create(&JsonStr);
		JsonWriter->WriteObjectStart();
		JsonWriter->WriteValue(TEXT("ret"), TEXT("1"));
		JsonWriter->WriteArrayStart(TEXT("fields"));
		for (const FString& FieldName : FieldList)
		{
			JsonWriter->WriteValue(FieldName);
		}
		JsonWriter->WriteArrayEnd();
		JsonWriter->WriteRawJSONValue(TEXT("deviceInfo"), UGameFunctionLibrary::GetDeviceInfoJson());
		JsonWriter->WriteObjectEnd();
		JsonWriter->Close();
		return JsonStr;
	}

	if (Args.Num() > 1 && Args[1] == "stop")
	{
		UGameFunctionLibrary::StopScenePerfStat(World, ViewportClient);
		return "1";
	}

	if (!UGameFunctionLibrary::IsScenePerfStatEnabled())
	{
		return "error:notStart";
	}

	TMap<FString, double> ScenePerfValueMap;
	UGameFunctionLibrary::GetScenePerfValue(ViewportClient, ScenePerfValueMap);
	APawn* Player = World->GetFirstPlayerController() ? World->GetFirstPlayerController()->GetPawn() : nullptr;
	APlayerController* PlayerController = World->GetFirstPlayerController();
	FVector PlayerLocation = FVector::ZeroVector;
	FRotator PlayerRotation = FRotator::ZeroRotator;
	FRotator ControlRotation = FRotator::ZeroRotator;
	if (Player != nullptr)
	{
		PlayerLocation = Player->GetActorLocation();
		PlayerRotation = Player->GetActorRotation();
	}
	if (PlayerController != nullptr)
	{
		ControlRotation = PlayerController->GetControlRotation();
	}

	FString JsonStr;
	TSharedRef<TJsonWriter<TCHAR, TCondensedJsonPrintPolicy<TCHAR>>> JsonWriter = TJsonWriterFactory<TCHAR, TCondensedJsonPrintPolicy<TCHAR>>::Create(&JsonStr);
	JsonWriter->WriteObjectStart();
	JsonWriter->WriteValue(TEXT("frame"), (int64)GFrameNumber);
	JsonWriter->WriteValue(TEXT("mapName"), World->GetMapName());
	JsonWriter->WriteObjectStart(TEXT("playerLocation"));
	JsonWriter->WriteValue(TEXT("x"), PlayerLocation.X);
	JsonWriter->WriteValue(TEXT("y"), PlayerLocation.Y);
	JsonWriter->WriteValue(TEXT("z"), PlayerLocation.Z);
	JsonWriter->WriteObjectEnd();
	JsonWriter->WriteObjectStart(TEXT("playerRotation"));
	JsonWriter->WriteValue(TEXT("pitch"), PlayerRotation.Pitch);
	JsonWriter->WriteValue(TEXT("yaw"), PlayerRotation.Yaw);
	JsonWriter->WriteValue(TEXT("roll"), PlayerRotation.Roll);
	JsonWriter->WriteObjectEnd();
	JsonWriter->WriteObjectStart(TEXT("cameraRotation"));
	JsonWriter->WriteValue(TEXT("pitch"), ControlRotation.Pitch);
	JsonWriter->WriteValue(TEXT("yaw"), ControlRotation.Yaw);
	JsonWriter->WriteValue(TEXT("roll"), ControlRotation.Roll);
	JsonWriter->WriteObjectEnd();
	for (const FString& FieldName : UGameFunctionLibrary::GetScenePerfFieldList())
	{
		if (ScenePerfValueMap.Contains(FieldName))
		{
			JsonWriter->WriteValue(FieldName, ScenePerfValueMap[FieldName]);
		}
	}
	JsonWriter->WriteObjectEnd();
	JsonWriter->Close();
	return JsonStr;
}

FString GameAPI::SetUseAccelerationForPaths(TArray<FString> Args)
{
	UWorld* World = UUAutoCore::Instance()->GetGameWorld();
	ACharacterBase* PlayerOwner = Cast<ACharacterBase>(UGameplayStatics::GetPlayerCharacter(World, 0));
	if (PlayerOwner)
	{
		UPlayerCharMoveComp* MovementComponent = Cast<UPlayerCharMoveComp>(PlayerOwner->GetMovementComponent());
		if (MovementComponent)
		{
			MovementComponent->SetUseAccelerationForPaths(Args[1] == "1");
			return Args[1];
		}
	}
	return "fail";

}

FString GameAPI::InputAction(TArray<FString> Args)
{
	if (Args.Num() < 3) { return "error:incorrectNumberOfParameters"; }
	UWorld* World = UUAutoCore::Instance()->GetGameWorld();
	auto PlayerCharacter = Cast<APlayerCharacter>(UGameplayStatics::GetPlayerCharacter(World, 0));
	if (PlayerCharacter)
	{
		if (Args[1] == "BulletJump")//对特殊的动作进行封装
		{
			PlayerCharacter->ActionCallback("SwitchCrouch", IE_Released);
			PlayerCharacter->ActionCallback("Jump", IE_Pressed);
			PlayerCharacter->ActionCallback("Jump", IE_Released);
		}
		else {
			if (Args[2] == "press" || Args[2] == "click")
			{
				PlayerCharacter->ActionCallback(FName(Args[1]), IE_Pressed);
			}
			if (Args[2] == "release" || Args[2] == "click")
			{
				PlayerCharacter->ActionCallback(FName(Args[1]), IE_Released);
			}
		}
		return "1";
	}
	
	
	return "0";
}

FString GameAPI::GTestHandler(TArray<FString> Args)
{
	//UnLua::CallTableFunc(UnLua::GetState(), "GM_Command","MockAllSystemCondition");
//#if !EM_FOR_DISTRIBUTION
//	UEMGameInstance* GameInstance = Cast<UEMGameInstance>(UUAutoCore::Instance()->GetGameWorld()->GetGameInstance());
//	if (IsValid(GameInstance))
//	{
//		GameInstance->GetAvatar()->ExecuteGM(Args[1], Args[2], true);
//	}
//#endif
	return "success";

}



FString GameAPI::GetCondemnLoc(TArray<FString> Args)
{
	FString JsonStr;
	TSharedRef<TJsonWriter<TCHAR, TCondensedJsonPrintPolicy<TCHAR>>> JsonWriter = TJsonWriterFactory<TCHAR, TCondensedJsonPrintPolicy<TCHAR>>::Create(&JsonStr);

	FVector Loc = FVector::ZeroVector;
	UWorld* GameWorld = UUAutoCore::Instance()->GetGameWorld();

	if (GameWorld)
	{
		const FString BPPath = TEXT("/Game/BluePrints/Story/Interactive/InteractiveComponent/BP_PenalizeInteractiveComponent.BP_PenalizeInteractiveComponent_C");
		UClass* ComponentClass = LoadClass<UActorComponent>(nullptr, *BPPath);  // 加载蓝图类

		if (ComponentClass != nullptr)
		{
			JsonWriter->WriteArrayStart();

			for (TActorIterator<AActor> It(GameWorld); It; ++It)
			{
				AActor* Actor = *It;
				if (Actor)
				{
					TArray<UActorComponent*> Components = Actor->GetComponentsByClass(ComponentClass);
					for (UActorComponent* Component : Components)
					{
						if (Component)
						{
							USceneComponent* SceneComponent = Cast<USceneComponent>(Component);
							if (SceneComponent)
							{
								Loc = SceneComponent->GetComponentLocation();
								JsonWriter->WriteObjectStart();
								JsonWriter->WriteValue("name", Actor->GetFName().ToString());
								JsonWriter->WriteValue("x", Loc.X);
								JsonWriter->WriteValue("y", Loc.Y);
								JsonWriter->WriteValue("z", Loc.Z);
								JsonWriter->WriteObjectEnd();
							}
						}
					}
				}
			}

			JsonWriter->WriteArrayEnd();
		}

	}


	JsonWriter->Close();
	return JsonStr;
}

FString GameAPI::ShowScreenText(TArray<FString> Args)
{
	FString Text;
	for (int32 Index = 1; Index < Args.Num(); Index++)
	{
		if (Args[Index].IsEmpty() || Args[Index] == TEXT("&"))
		{
			continue;
		}
		if (!Text.IsEmpty())
		{
			Text += TEXT(";");
		}
		Text += Args[Index];
	}
	if (Text.IsEmpty())
	{
		return "error:incorrectNumberOfParameters";
	}
	return UGameFunctionLibrary::ShowScreenText(Text) ? "1" : "0";
}

