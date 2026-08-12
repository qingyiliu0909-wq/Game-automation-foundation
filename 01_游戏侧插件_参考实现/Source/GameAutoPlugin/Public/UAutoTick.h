// Fill out your copyright notice in the Description page of Project Settings.

#pragma once

#include "CoreMinimal.h"
#include "UObject/NoExportTypes.h"
#include "UAutoTick.generated.h"
/**
 *
 */
UCLASS()
class GAMEAUTOPLUGIN_API UUAutoTick : public UObject, public FTickableGameObject
{
	GENERATED_BODY()

public:
	virtual void Tick(float DeltaTime) override;
	virtual bool IsTickable() const override;
	virtual TStatId GetStatId() const override;

};
