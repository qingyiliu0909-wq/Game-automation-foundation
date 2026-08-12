// Copyright Epic Games, Inc. All Rights Reserved.

#include "GameAutoPlugin.h"
#include "UAutoCore.h"

#define LOCTEXT_NAMESPACE "FGameAutoPluginModule"

//DEFINE_LOG
DEFINE_LOG_CATEGORY(LogUAuto)

UUAutoCore* FGameAutoPluginModule::AutoCore = nullptr;
bool FGameAutoPluginModule::Development = false;

void FGameAutoPluginModule::StartupModule()
{
	UE_LOG(LogUAuto, Log, TEXT("UAuto Started successfully"));
	// This code will execute after your module is loaded into memory; the exact timing is specified in the .uplugin file per-module

	BindDelegates();

#if UE_TRACE_ENABLED
	UE_LOG(LogUAuto, Log, TEXT("UAuto UE_TRACE_ENABLED is Running"));
#endif

}

void FGameAutoPluginModule::ShutdownModule()
{
	// This function may be called during shutdown to clean up your module.  For modules that support dynamic reloading,
	// we call this function before unloading the module.
	PluginEnd();
}

void FGameAutoPluginModule::BindDelegates()
{
#if WITH_EDITOR
	if (GIsEditor)
	{
		//将WorldStart/WorldEnd函数添加到编辑器的 PostPIEStarted/EndPIE 事件中。当游戏开始/结束时 执行。
		FEditorDelegates::PostPIEStarted.AddRaw(this, &FGameAutoPluginModule::WorldStart);
		FEditorDelegates::EndPIE.AddRaw(this, &FGameAutoPluginModule::WorldEnd);
	}
	else
	{
		FCoreDelegates::OnFEngineLoopInitComplete.AddRaw(this, &FGameAutoPluginModule::WorldStart2);
		FCoreDelegates::OnExit.AddRaw(this, &FGameAutoPluginModule::WorldEnd2);
	}
#else
	//将WorldStart2/WorldEnd2函数添加到引擎的 OnFEngineLoopInitComplete/OnExit 事件中。当游戏开始/结束时 执行。
	FCoreDelegates::OnFEngineLoopInitComplete.AddRaw(this, &FGameAutoPluginModule::WorldStart2);
	FCoreDelegates::OnExit.AddRaw(this, &FGameAutoPluginModule::WorldEnd2);
#endif
	FCoreDelegates::OnShutdownAfterError.AddRaw(this, &FGameAutoPluginModule::WorldEnd2);
}

void FGameAutoPluginModule::WorldStart(bool bSimulate)
{
//UE_SERVER
	UE_LOG(LogUAuto, Log, TEXT("UAutoCore WorldStart is successed!"));
	PluginStart();
}

void FGameAutoPluginModule::WorldStart2()
{
	UE_LOG(LogUAuto, Log, TEXT("UAutoCore WorldStart2 is successed!"));
	PluginStart();
}

void FGameAutoPluginModule::WorldEnd(bool bSimulate)
{
	UE_LOG(LogUAuto, Log, TEXT("UAutoCore WorldEnd is successed!"));
	PluginEnd();
}
void FGameAutoPluginModule::WorldEnd2()
{
	UE_LOG(LogUAuto, Log, TEXT("UAutoCore WorldEnd2 is successed!"));
	PluginEnd();
}

void FGameAutoPluginModule::PluginStart()
{
	if (!AutoCore)
	{
		AutoCore = UUAutoCore::Instance();
		AutoCore->Init();
	}
}

void FGameAutoPluginModule::PluginEnd()
{
	if (AutoCore)
	{
		AutoCore->Release();
		AutoCore = nullptr;
	}

}

#undef LOCTEXT_NAMESPACE
	
IMPLEMENT_MODULE(FGameAutoPluginModule, GameAutoPlugin)