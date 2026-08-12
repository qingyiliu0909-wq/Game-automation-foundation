// Fill out your copyright notice in the Description page of Project Settings.


#include "UAutoRunner.h"
#include "GameAPI.h"
#include "UAutoAPI.h"
#include "GameAutoPlugin.h"
#include "UAutoDebugMode.h"
#include "CaptureStatData.h"
#include "ScenePerfCheck.h"
#include "Serialization/JsonWriter.h"
#include "Policies/CondensedJsonPrintPolicy.h"
#include <UAutoFunctionLibrary.h>

TMap<uint64, TWeakPtr<SWidget> > UAutoRunner::WidgetChache;

UAutoRunner* UAutoRunner::Get()
{
	static TUniquePtr<UAutoRunner> Instance = MakeUnique<UAutoRunner>();
	return Instance.Get();
}

void UAutoRunner::Init()
{
	StartServer(ip, port);

	// 注册 UAuto 原生接口

	ADD_UAUTO_API(getPluginVersion, GetPluginVersion, MsgHandler)
	ADD_UAUTO_API(getEngineVersion, GetEngineVersion, MsgHandler)
	ADD_UAUTO_API(closeConnection, CloseConnectionHandler, MsgHandler)
	ADD_UAUTO_API(getAppName, GetAppNameHandler, MsgHandler)
	ADD_UAUTO_API(findObject, FindObjectHandler, MsgHandler)
	ADD_UAUTO_API(tapObject, TapObjectHandler, MsgHandler)
	ADD_UAUTO_API(mouseDown, MouseDownHandler, MsgHandler)
	ADD_UAUTO_API(getText, GetTextHandler, MsgHandler)
	ADD_UAUTO_API(setText, SetTextHandler, MsgHandler)
	ADD_UAUTO_API(getScreen, GetScreenHandler, MsgHandler)
	ADD_UAUTO_API(findChild, FindChildHandler, MsgHandler)
	ADD_UAUTO_API(objectExist, ObjectExistHandler, MsgHandler)
	ADD_UAUTO_API(objectExistOnlyTap, ObjectExistOnlyTapHandler, MsgHandler)
	ADD_UAUTO_API(debugMode, DebugModeHandler, MsgHandler)
	ADD_UAUTO_API(findText, FindTextHandler, MsgHandler)
	ADD_UAUTO_API(findTextAndClickWhich, FindTextAndWhichClickHandler, MsgHandler)
	ADD_UAUTO_API(getParent, GetParentHandler, MsgHandler)
	ADD_UAUTO_API(tapScreen, TapScreenHandler, MsgHandler)
	ADD_UAUTO_API(clickScreen, ClickScreenHandler, MsgHandler)
	ADD_UAUTO_API(memReport, MemReportHandler, MsgHandler)
	ADD_UAUTO_API(consoleCommand, ExecuteConsoleCommand, MsgHandler)
	ADD_UAUTO_API(log, LogHandler, MsgHandler)
	ADD_UAUTO_API(setScrollOffset, SetScrollOffsetHandler, MsgHandler)
	ADD_UAUTO_API(switchMode, SwitchModeHandler, MsgHandler)
	ADD_UAUTO_API(findActorByName, FindActorByNameHandler, MsgHandler)
	ADD_UAUTO_API(getMapName, GetMapName, MsgHandler)
	ADD_UAUTO_API(getLogFileList, GetLogFileList, MsgHandler)
	ADD_UAUTO_API(getLogFileInfo, GetLogFileInfo, MsgHandler)
	ADD_UAUTO_API(getLogFileContent, GetLogFileContent, MsgHandler)
	ADD_UAUTO_API(getLogFileTail, GetLogFileTail, MsgHandler)
	ADD_UAUTO_API(getLogFileChunk, GetLogFileChunk, MsgHandler)
	ADD_UAUTO_API(inputKey, InputKeys, MsgHandler)
	ADD_UAUTO_API(inputAxis, InputAxis, MsgHandler)
	ADD_UAUTO_API(switchWays, SwitchWaysHandler, MsgHandler)
	ADD_UAUTO_API(switchExcludeNotVisible, SwitchExcludeNotVisibleHandler, MsgHandler)
	ADD_UAUTO_API(Test, TestHandler, MsgHandler)

	// 注册游戏自定义接口
	ADD_GAME_API(getLocation, GetLocation, MsgHandler)
	ADD_GAME_API(setLocation, SetLocation, MsgHandler)
	ADD_GAME_API(getPRotation, GetPawnRotation, MsgHandler)
	ADD_GAME_API(setPRotation, SetPawnRotation, MsgHandler)
	ADD_GAME_API(getCRotation, GetControlRotation, MsgHandler)
	ADD_GAME_API(setCRotation, SetControlRotation, MsgHandler)
	ADD_GAME_API(setAimRotation, SetAimRotation, MsgHandler)
	ADD_GAME_API(findMonsterLocation, FindMonsterLocation, MsgHandler)
	ADD_GAME_API(findMonsterAndAim, FindMonsterAndAim, MsgHandler)
	ADD_GAME_API(findLongCaoMonster, FindLongCaoMonster, MsgHandler)
	ADD_GAME_API(unlockMiniGames, UnlockMiniGames, MsgHandler)
	ADD_GAME_API(getIndicatorLoc, GetIndicatorLoc, MsgHandler)
	ADD_GAME_API(getTaskIndicatorLoc, GetTaskIndicatorLoc, MsgHandler)
	ADD_GAME_API(getMechanismLoc, GetMechanismLoc, MsgHandler)
	ADD_GAME_API(getMechanismMaps, GetMechanismMaps, MsgHandler)
	ADD_GAME_API(getInteractiveLoc, GetInteractiveLoc, MsgHandler)
	ADD_GAME_API(setMoveSpeed, SetMoveSpeedHandler, MsgHandler)
	ADD_GAME_API(moveTo, MoveToHandler, MsgHandler)
	ADD_GAME_API(isMove, IsMoveHandler, MsgHandler)
	ADD_GAME_API(cameraFollow, CameraFollowHandler, MsgHandler)
	ADD_GAME_API(aimMonster, AimMonsterHandler, MsgHandler)
	ADD_GAME_API(captureStat, CaptureStatHandler, MsgHandler)
	ADD_GAME_API(scenePerfCheck, ScenePerfCheckHandler, MsgHandler)
	ADD_GAME_API(getScenePerfData, GetScenePerfData, MsgHandler)
	ADD_GAME_API(getProjectileLoc, GetProjectileLoc, MsgHandler)
	ADD_GAME_API(setUseAccelerationForPaths, SetUseAccelerationForPaths, MsgHandler)
	ADD_GAME_API(inputAction, InputAction, MsgHandler)
	ADD_GAME_API(showScreenText, ShowScreenText, MsgHandler)
	ADD_GAME_API(getCondemnLoc, GetCondemnLoc, MsgHandler)
	ADD_GAME_API(getBlueprintActorLoc, GetBlueprintActorLoc, MsgHandler)
	ADD_GAME_API(setBlueprintActorLoc, SetBlueprintActorLoc, MsgHandler)
	ADD_GAME_API(setBlueprintActorMeshLoc, SetBlueprintActorMeshLoc, MsgHandler)

	ADD_GAME_API(GTest, GTestHandler, MsgHandler)



	FUAutoMsgHandleDelegate HelpHandler;
	HelpHandler.BindStatic(UAutoRunner::HelpHandler);
	MsgHandler.Add("help", HelpHandler);

}

void UAutoRunner::Release()
{
	UAutoDebugMode::Get()->Stop();
	StopServer();

	WidgetChache.Empty();
	MsgHandler.Empty();
}

void UAutoRunner::ReStartServer()
{
	StopServer();
	StartServer(ip, port);
}

void UAutoRunner::StartServer(FString IPAddress, int listeningPort)
{
	if (Server == nullptr)
	{
		Server = NewObject<UUAutoSocketObject>(GetTransientPackage());
		Server->AddToRoot();

		Server->Create(IPAddress, listeningPort, INT_MAX, INT_MAX);


		if (Server)
		{
			UE_LOG(LogUAuto, Log, TEXT("Create Server Success"));
		}
		else {
			UE_LOG(LogUAuto, Error, TEXT("Create Server Failed"));
		}
	}
	else
	{
		UE_LOG(LogUAuto, Warning, TEXT("Server Exist, Skip"));
	}
}

void UAutoRunner::StopServer()
{
	if (Server)
	{
		Server->Close();
		Server->RemoveFromRoot();
		Server = nullptr;
	}
}

FString UAutoRunner::HelpHandler(TArray<FString> Args)
{
	TArray<FString> Keys;
	Get()->MsgHandler.GetKeys(Keys);


	FString JsonStr;
	TSharedRef<TJsonWriter<TCHAR, TCondensedJsonPrintPolicy<TCHAR>>> JsonWriter = TJsonWriterFactory<TCHAR,TCondensedJsonPrintPolicy<TCHAR>>::Create(&JsonStr);

	JsonWriter->WriteArrayStart();
	for (auto Key : Keys)
	{
		JsonWriter->WriteValue(Key);
	}
	JsonWriter->WriteArrayEnd();

	JsonWriter->Close();
	return JsonStr;
}

void UAutoRunner::Tick(float DeltaTime)
{
	if (Server)
	{
		TArray<FString> Messages;
		Server->GetCharacterTimerManager().Tick(DeltaTime);
		Server->GetSwapData(Messages);
		// 处理获取到的消息
		for (auto Message : Messages)
		{
			//测试使用
			//UE_LOG(LogUAuto, Warning, TEXT("接收到参数 %s"), *Message);

			// 传入的参数根据 ';' 进行分割，第一个参数永远为指令名，最后一个参数永远为结束符号 '&' 
			TArray<FString> Args;
			Message.ParseIntoArray(Args, TEXT(";"));

			// 根据对应指令执行操作
			if (MsgHandler.Contains(Args[0]))
			{
				FString Result = MsgHandler[Args[0]].Execute(Args);
				FString Msg = FString::Printf(TEXT("altstart::%s::altLog::::altend"), *Result);
				Msg=Msg.Replace(TEXT("\\\\"),TEXT("/"));
				// 处理完指令以后将结果发送给脚本端
				Server->SendData(Msg);
			}
			// 如果没有注册对应指令，返回错误信息
			else
			{
				FString Msg = FString::Printf(TEXT("altstart::error:no message %s::altLog::::altend"), *Message);
				Server->SendData(Msg);
			}
		}

		// DebugMode 录制
		TArray<FString> RecodeMessages;
		if (UAutoDebugMode::Get()->Tick(DeltaTime, RecodeMessages))
		{
			for (FString RecodeMessage : RecodeMessages)
			{
				FString Msg = FString::Printf(TEXT("altstart::%s::altLog::::altend"), *RecodeMessage);
				Server->SendData(Msg);
			}
		}

		// 数据采集
		CaptureStatData::Get()->Tick(DeltaTime);
		ScenePerfCheck::Get()->Tick(DeltaTime);

	}

}

TMap<uint64, TWeakPtr<SWidget>>* UAutoRunner::GetWidgetChache()
{
	return &WidgetChache;
}

bool UAutoRunner::CheckIsShipping()
{
#if UE_BUILD_SHIPPING
	return true;
#else
	return false;
#endif
}
