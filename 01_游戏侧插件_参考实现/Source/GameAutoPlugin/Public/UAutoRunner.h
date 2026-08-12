// Fill out your copyright notice in the Description page of Project Settings.

#pragma once

#include "CoreMinimal.h"
#include "UAutoSocketObject.h"

// UAuto 自动消息处理委托(通过)
DECLARE_DELEGATE_RetVal_OneParam(FString, FUAutoMsgHandleDelegate, TArray<FString> Args);
/**
 * 
 */
class GAMEAUTOPLUGIN_API UAutoRunner
{
public:

	static UAutoRunner* Get();

	void Init();
	void Release();

	void ReStartServer();

	void Tick(float DeltaTime);

	TMap<uint64, TWeakPtr<SWidget>>* GetWidgetChache();

	static bool CheckIsShipping();

protected:
	void StartServer(FString ip, int port);
	void StopServer();

	// 寻找到的 UI 控件缓存
	static TMap<uint64, TWeakPtr<SWidget>> WidgetChache;

	// 消息处理
	TMap<FString, FUAutoMsgHandleDelegate> MsgHandler;

	UUAutoSocketObject* Server = nullptr;

private:
	static FString HelpHandler(TArray<FString> Args);


	const FString ip = "0.0.0.0";
	const int port = 13000;
};
