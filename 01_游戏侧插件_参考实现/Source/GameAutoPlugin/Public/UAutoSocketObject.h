// Fill out your copyright notice in the Description page of Project Settings.

#pragma once

#include "CoreMinimal.h"
#include "UObject/NoExportTypes.h"
#include "UAutoSocketThread.h"
#include "EngineMinimal.h"
#include "Interfaces/IHttpRequest.h"
#include "Interfaces/IHttpResponse.h"
#include "UAutoSocketObject.generated.h"

DECLARE_DYNAMIC_MULTICAST_DELEGATE_TwoParams(FUAutoObjectConnectReceiveDelegate, FString, RemoteIP, int32, RemotePort);
DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FUAutoObjectConnectedServerResultDelegate, bool, bSuccess);
/* 
 */
UCLASS(BlueprintType)
class GAMEAUTOPLUGIN_API UUAutoSocketObject : public UObject, public IReceiveSwap
{
	GENERATED_BODY()
public:
	UUAutoSocketObject(const FObjectInitializer& ObjectInitializer);
	virtual void BeginDestroy() override;

	UFUNCTION(BlueprintCallable, Category = Network)
	bool Create(const FString& IP, int32 Port, int32 ReceiveSize = 1024, int32 SendSize = 1024);

	void PauseTimers();

	void UnPauseTimers();

	UFUNCTION(BlueprintCallable, Category = Network)
	void SendData(FString Message);

	UFUNCTION(BlueprintCallable, Category = Network)
	void Close();

	virtual void AddMessage(uint32 UTID,FString Message) override;

	// 获取缓冲区中的的消息
	void GetSwapData(TArray<FString>& Messages);

	inline FTimerManager& GetCharacterTimerManager() const { return *CharacterTimerManager.Get(); }
protected:

	/** Server */
	void ConnectTickCheck();
	void DisConnectTickCheck();
	UFUNCTION()
	void OnDisConnected(UUAutoSocketThread* pThread);



	/** Client */
	UFUNCTION(BlueprintCallable, Category = UAutoTest)
	void ConnectServer(FString IP, int32 Port);
	//重连服务器
	void ReconnectServer();
	void ControlReport();
	void SurviveResponse(FHttpRequestPtr HttpRequest, FHttpResponsePtr HttpResponse, bool bWasSuccessful);
	void ControlHeartbeat();
protected:
	class FSocket* Socket;
	bool bShutDown;
	int32 SendDataSize;
	int32 RecDataDize;

	uint32 ExecutingThreadID;

	TUniquePtr<FTimerManager, TDefaultDelete<FTimerManager>> CharacterTimerManager;

	UPROPERTY()
	TArray<class UUAutoSocketThread*> RecThreads;

	UPROPERTY(BlueprintAssignable, VisibleAnywhere, Category = Network)
	FUAutoReceiveSocketDataDelegate ReceiveSocketDataDelegate;

	UPROPERTY(BlueprintAssignable, VisibleAnywhere, Category = Network)
	FUAutoObjectConnectedServerResultDelegate ConnectedServerResultDelegate;

	/** Server */
	FSocket* RecSocket;
	FString ServerIP;
	int32 ServerPort;
	FTimerHandle ConnectCheckHandler;
	FTimerHandle DisConnectCheckHandler;
	FTimerHandle ConnectHandler;
	FUAutoObjectConnectReceiveDelegate ConnectReceiveDelegate;

	UWorld* World = nullptr;
};
