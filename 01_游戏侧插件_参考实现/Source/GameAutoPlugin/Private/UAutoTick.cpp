// Fill out your copyright notice in the Description page of Project Settings.


#include "UAutoTick.h"
#include "UAutoCore.h"
#include "GameAutoPlugin.h"


void UUAutoTick::Tick(float DeltaTime)
{
	UUAutoCore* AutoCore = FGameAutoPluginModule::AutoCore;
	if (AutoCore)
	{
		AutoCore->Tick(DeltaTime);
	}
}

bool UUAutoTick::IsTickable() const
{

#if !UE_SERVER
	return true;
#else
	return false;
#endif
}

TStatId UUAutoTick::GetStatId() const
{
	return Super::GetStatID();
}