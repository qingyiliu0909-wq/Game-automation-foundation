// Fill out your copyright notice in the Description page of Project Settings.


#include "UAutoCore.h"

#include "Kismet/GameplayStatics.h"
//#include "Blueprint/WidgetBlueprintLibrary.h"
#if WITH_EDITOR
#include <UnrealEd/Classes/Editor/UnrealEdEngine.h>
#endif
#include <Runtime/Engine/Classes/Engine/GameEngine.h>
#include "GameAutoPlugin.h"
#include "UAutoRunner.h"
#include "GameFunctionLibrary.h"

UUAutoCore* UUAutoCore::AutoCoreInstance = nullptr;

UUAutoCore* UUAutoCore::Instance()
{
	if (AutoCoreInstance == nullptr)
	{
		AutoCoreInstance = NewObject<UUAutoCore>();
		//将AutoCore添加到世界对象的根节点中
		AutoCoreInstance->AddToRoot();
	}

	return AutoCoreInstance;

	//return nullptr;
}
/// <summary>
/// 自动化插件初始
/// </summary>
void UUAutoCore::Init()
{
	UE_LOG(LogUAuto, Log, TEXT("UAutoCore init is successed!"));

	GameAPILibrary = NewObject<UGameFunctionLibrary>();
	GameAPILibrary->AddToRoot();

	// 这里加入插件的其他初始化内容
	UAutoRunner::Get()->Init();

	IsInit = true;
}
/// <summary>
/// 重置自动化状态
/// </summary>
void UUAutoCore::Release()
{
	if (AutoCoreInstance != nullptr)
	{
		AutoCoreInstance->RemoveFromRoot();
		AutoCoreInstance = nullptr;
	}

	if (IsInit)
	{
		// 这里加入插件的析构内容

		if (GameAPILibrary)
		{
			GameAPILibrary->RemoveFromRoot();
			GameAPILibrary = nullptr;
		}

		UAutoRunner::Get()->Release();

	}

	IsInit = false;
}

UWorld* UUAutoCore::GetGameWorld()
{
	UWorld* World = nullptr;

#if WITH_EDITOR
	//UGameInstance* GameInstance = nullptr;
	if (GEngine->IsEditor())
	{
		World = Cast<UUnrealEdEngine>(GEngine)->PlayWorld;
	}
	else
	{
		World = Cast<UGameEngine>(GEngine)->GetGameWorld();
	}
#else
	World = GWorld;
#endif

	return World;
}

void UUAutoCore::Tick(float DeltaTime)
{
	if (GameAPILibrary)
	{
		GameAPILibrary->Tick(DeltaTime);
	}
	UAutoRunner::Get()->Tick(DeltaTime);

}
