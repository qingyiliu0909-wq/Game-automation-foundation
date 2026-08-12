// Copyright Epic Games, Inc. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"
#include "Modules/ModuleManager.h"

class UUAutoCore;


// 声明一个Category为LogUAuto
DECLARE_LOG_CATEGORY_EXTERN(LogUAuto, Log, All)

class FGameAutoPluginModule : public IModuleInterface
{
public:

	/** IModuleInterface implementation */
	virtual void StartupModule() override;
	virtual void ShutdownModule() override;

	void BindDelegates();

	void WorldStart(bool bSimulate);
	void WorldStart2();

	void WorldEnd(bool bSimulate);
	void WorldEnd2();

	static UUAutoCore* AutoCore;

	static bool Development;

private:

	void PluginStart();

	void PluginEnd();
};
