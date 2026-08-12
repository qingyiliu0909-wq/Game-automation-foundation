// Fill out your copyright notice in the Description page of Project Settings.

#pragma once

#include "CoreMinimal.h"
#include "UObject/NoExportTypes.h"
#include "UAutoCore.generated.h"

class UGameFunctionLibrary;

/**
 * 
 */
UCLASS()
class GAMEAUTOPLUGIN_API UUAutoCore : public UObject
{
	GENERATED_BODY()
public:

	static UUAutoCore* Instance();

	void Init();

	void Release();



	UWorld* GetGameWorld();

	UGameFunctionLibrary* GetGameAPILibrary() { return GameAPILibrary; };

	void Tick(float DeltaTime);
	

private:

	static UUAutoCore* AutoCoreInstance;

	bool IsInit = false;

	UGameFunctionLibrary* GameAPILibrary = nullptr;
};
