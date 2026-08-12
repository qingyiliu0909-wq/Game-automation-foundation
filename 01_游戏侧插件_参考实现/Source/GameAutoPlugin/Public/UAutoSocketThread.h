// Fill out your copyright notice in the Description page of Project Settings.

#pragma once

#include "CoreMinimal.h"
#include "Sockets.h"
#include "UObject/NoExportTypes.h"
#include "UAutoSocketThread.generated.h"

DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FUAutoReceiveSocketDataDelegate, FString, Data); //Receive Connect Callback
DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FUAutoLostConnectionDelegate, UUAutoSocketThread*, Thread);	//DisConnect Callback

/**
 * @brief Buffer interface for receiving and storing Socket messages
 */
class IReceiveSwap
{
public:
	virtual ~IReceiveSwap() = default;

	/**
	 * @brief Add Socket information to buffer
	 * @param Message Content sent from Socket client
	 */
	virtual void AddMessage(uint32 UTID,FString Message) = 0;

protected:
	/**
	 * @brief Message cache
	 */
	TQueue<TTuple<uint32, FString>> SwapData;
};

/**
 * SocketThread 继承FRunnable
 */
UCLASS()
class GAMEAUTOPLUGIN_API UUAutoSocketThread : public UObject, public FRunnable
{
	GENERATED_BODY()
public:
	uint32 ThreadID;
	FRunnableThread* FRThread;
	//FRunnable Interface
	virtual bool Init() override { return true; }
	virtual uint32 Run() override;
	virtual void Stop() override;
	virtual void Exit() override {}

	void SetReceiveSwap(IReceiveSwap* Swap);

	void StartThread(FSocket* Socket, uint32 SizeSend, uint32 SizeRec);

	bool SendData(FString Data);

	int32 CalcUtf8NumFromString(const FString& Str);

public:
	FUAutoReceiveSocketDataDelegate ReceiveSocketDataDelegate;
	FUAutoLostConnectionDelegate	LostConnectionDelegate;

protected:
	FSocket* ConnectSocket;
	uint32 SendDataSize;
	uint32 RecDataSize;
	TArray<uint8> ReceiveData;
	FRunnableThread* pThread;
	bool bThreadStop;

	IReceiveSwap* ReceiveSwap;
};

