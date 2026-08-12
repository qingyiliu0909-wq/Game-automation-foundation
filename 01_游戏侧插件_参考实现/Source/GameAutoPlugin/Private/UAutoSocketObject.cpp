// Fill out your copyright notice in the Description page of Project Settings.


#include "UAutoSocketObject.h"
#if WITH_EDITOR
#include "Editor/UnrealEdEngine.h"
#endif
#include "Engine/GameEngine.h"
#include "GameAutoPlugin.h"
#include <UAutoFunctionLibrary.h>
#include "Common/TcpSocketBuilder.h"
#include "HttpModule.h"
#include "Policies/CondensedJsonPrintPolicy.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"

UUAutoSocketObject::UUAutoSocketObject(const FObjectInitializer& ObjectInitializer)
{
	bShutDown = false;
}

void UUAutoSocketObject::BeginDestroy()
{
	Super::BeginDestroy();
	Close();
	bShutDown = true;

}

bool UUAutoSocketObject::Create(const FString& IP, int32 Port, int32 ReceiveSize, int32 SendSize)
{
	this->SendDataSize = SendSize;
	this->RecDataDize = ReceiveSize;
	
	FIPv4Address ServerAddr;
	if (!FIPv4Address::Parse(IP, ServerAddr))
	{
		UE_LOG(LogUAuto, Error, TEXT("Server Ip %s is illegal"), *IP);
	}
	//创建一个自己的定时器
	CharacterTimerManager = MakeUnique<FTimerManager>();

	Socket = FTcpSocketBuilder(TEXT("Socket Listener"))
		.AsReusable()
		.AsBlocking()
		.BoundToAddress(ServerAddr)
		.BoundToPort(Port)
		.Listening(8)
		.WithReceiveBufferSize(SendDataSize)
		.WithSendBufferSize(RecDataDize);

	if (!Socket)
	{
		UE_LOG(LogUAuto, Error, TEXT("Create  Socket Error!"));
		return false;
	}


#if WITH_EDITOR
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
	
	
	GetCharacterTimerManager().SetTimer(ConnectCheckHandler, this, &UUAutoSocketObject::ConnectTickCheck, 0.5, true);
	GetCharacterTimerManager().SetTimer(DisConnectCheckHandler, this, &UUAutoSocketObject::DisConnectTickCheck, 10, true,15);
#if PLATFORM_ANDROID || PLATFORM_IOS || PLATFORM_OPENHARMONY //只有移动端开启游戏控制
	GetCharacterTimerManager().SetTimer(ConnectHandler, this, &UUAutoSocketObject::ControlHeartbeat, 30, true, 30);
	UUAutoSocketObject::ControlReport();
	// 注册应用切后台事件
	FCoreDelegates::ApplicationHasReactivatedDelegate.AddUObject(this, &UUAutoSocketObject::UnPauseTimers);
	FCoreDelegates::ApplicationWillDeactivateDelegate.AddUObject(this, &UUAutoSocketObject::PauseTimers);
#endif
	return true;

}

void UUAutoSocketObject::PauseTimers()
{
	if (!GetCharacterTimerManager().IsTimerPaused(ConnectCheckHandler))
	{
		GetCharacterTimerManager().PauseTimer(ConnectCheckHandler);
		GetCharacterTimerManager().PauseTimer(DisConnectCheckHandler);
#if PLATFORM_ANDROID || PLATFORM_IOS || PLATFORM_OPENHARMONY
		GetCharacterTimerManager().PauseTimer(ConnectHandler);
#endif
	} 
}

void UUAutoSocketObject::UnPauseTimers()
{
	if (GetCharacterTimerManager().IsTimerPaused(ConnectCheckHandler))
	{
		GetCharacterTimerManager().UnPauseTimer(ConnectCheckHandler);
		GetCharacterTimerManager().UnPauseTimer(DisConnectCheckHandler);
#if PLATFORM_ANDROID || PLATFORM_IOS || PLATFORM_OPENHARMONY
		GetCharacterTimerManager().UnPauseTimer(ConnectHandler);
#endif
	}
}

void UUAutoSocketObject::SendData(FString Message)
{
	for (auto SocketThread : RecThreads)
	{
		if (SocketThread->ThreadID==ExecutingThreadID)
		{
			SocketThread->SendData(Message);
			break;
		}
	}
}

void UUAutoSocketObject::Close()
{

	if (Socket)
	{
		for (auto RecThreald : RecThreads)
		{
			RecThreald->Stop();
		}
		Socket->Close();
		ISocketSubsystem::Get(PLATFORM_SOCKETSUBSYSTEM)->DestroySocket(Socket);
		Socket = nullptr;
		RecThreads.Empty();

		// World->GetTimerManager().ClearTimer(ConnectCheckHandler);
	}
	if (RecSocket)
	{
		RecSocket->Close();
		ISocketSubsystem::Get(PLATFORM_SOCKETSUBSYSTEM)->DestroySocket(RecSocket);
		RecSocket = nullptr;
	}

}

void UUAutoSocketObject::AddMessage(uint32 UTID, FString Message)
{
	SwapData.Enqueue(MakeTuple(UTID,Message));
}

void UUAutoSocketObject::ConnectTickCheck()
{
	bool bPending = false;
	if (Socket && Socket->HasPendingConnection(bPending) && bPending)
	{
		UE_LOG(LogUAuto, Warning, TEXT("New connection received!!"));
		TSharedRef<FInternetAddr> RemoteAddress = ISocketSubsystem::Get(PLATFORM_SOCKETSUBSYSTEM)->CreateInternetAddr();
		RecSocket = Socket->Accept(*RemoteAddress, TEXT("Receive Socket"));
		UUAutoSocketThread* RSThread = NewObject<UUAutoSocketThread>(this);
		RecThreads.Add(RSThread);
		RSThread->ReceiveSocketDataDelegate = ReceiveSocketDataDelegate;
		RSThread->LostConnectionDelegate.AddDynamic(this, &UUAutoSocketObject::OnDisConnected);
		RSThread->SetReceiveSwap(this);
		RSThread->StartThread(RecSocket, SendDataSize, RecDataDize);
		ConnectReceiveDelegate.Broadcast(RemoteAddress->ToString(false), RemoteAddress->GetPort());
	}
}
void UUAutoSocketObject::DisConnectTickCheck()
{
	for (int32 i = RecThreads.Num() - 1; i >= 0; --i)
	{
		if (!RecThreads[i]->SendData("|"))
		{
			RecThreads[i]->Stop();
			RecThreads.RemoveAt(i);
		}
	}
}
void UUAutoSocketObject::OnDisConnected(UUAutoSocketThread* pThread)
{
	UE_LOG(LogUAuto, Warning, TEXT("Client lost"));
	if (RecThreads.Contains(pThread))
	{
		if (pThread)
		{
			pThread->Stop();
		}
		RecThreads.Remove(pThread);
		//if (pThread)
		//{
		//	pThread->FRThread->Kill();
		//	delete pThread;
		//}
	}
	if (ConnectedServerResultDelegate.IsBound())
	{
		ConnectedServerResultDelegate.Broadcast(false);
	}
}

void UUAutoSocketObject::GetSwapData(TArray<FString>& Messages)
{
	uint32 TID = 0;
	while (!SwapData.IsEmpty())
	{
		//FString Message;
		TTuple<uint32, FString> Message;
		SwapData.Peek(Message);
		if (TID==0 || TID!= Message.Get<0>())
		{
			SwapData.Dequeue(Message);
			Messages.Add(Message.Get<1>());
			ExecutingThreadID = Message.Get<0>();
		}
		
	}
}

void UUAutoSocketObject::ConnectServer(FString ip, int32 Port)
{
	ServerIP = ip;
	ServerPort = Port;
	UE_LOG(LogUAuto, Warning, TEXT("befor ip = %s"), *ServerIP);
	AsyncTask(ENamedThreads::AnyThread, [&]()
		{
			UE_LOG(LogUAuto, Warning, TEXT("thread ip = %s"), *ServerIP);
			TSharedPtr<FInternetAddr> addr = ISocketSubsystem::Get(PLATFORM_SOCKETSUBSYSTEM)->CreateInternetAddr();
			bool Success = true;
			addr->SetIp(*ServerIP, Success);
			if (!Success)
			{
				ConnectedServerResultDelegate.Broadcast(false);
				return;
			}
			addr->SetPort(Port);

			if (bShutDown && Socket->Connect(*addr))
			{
				UUAutoSocketThread* RSThread = NewObject<UUAutoSocketThread>();
				RecThreads.Add(RSThread);
				RSThread->ReceiveSocketDataDelegate = ReceiveSocketDataDelegate;
				RSThread->LostConnectionDelegate.AddDynamic(this, &UUAutoSocketObject::OnDisConnected);
				RSThread->StartThread(Socket, SendDataSize, RecDataDize);
				UE_LOG(LogUAuto, Warning, TEXT("Client Connect Success"));
				if (ConnectedServerResultDelegate.IsBound())
				{
					ConnectedServerResultDelegate.Broadcast(true);
				}

			}
			else
			{
				ESocketErrors LastErr = ISocketSubsystem::Get(PLATFORM_SOCKETSUBSYSTEM)->GetLastErrorCode();

				UE_LOG(LogUAuto, Warning, TEXT("Connect failed with error code (%d) error (%s)"), LastErr, ISocketSubsystem::Get(PLATFORM_SOCKETSUBSYSTEM)->GetSocketError(LastErr));
				if (ConnectedServerResultDelegate.IsBound())
				{
					ConnectedServerResultDelegate.Broadcast(false);
				}
			}
			return;
		});

}

void UUAutoSocketObject::ReconnectServer()
{
	Close();
	Socket = FTcpSocketBuilder(TEXT("Client Socket"))
		.AsReusable()
		.AsBlocking()
		.WithReceiveBufferSize(RecDataDize)
		.WithSendBufferSize(SendDataSize);
	ConnectServer(ServerIP, ServerPort);
}
void UUAutoSocketObject::ControlReport()
{
	FString JsonStr;
	TSharedRef<TJsonWriter<TCHAR, TCondensedJsonPrintPolicy<TCHAR>>> JsonWriter = TJsonWriterFactory<TCHAR, TCondensedJsonPrintPolicy<TCHAR>>::Create(&JsonStr);
	JsonWriter->WriteObjectStart();
	JsonWriter->WriteValue(TEXT("BuildVersion"), FApp::GetBuildVersion());
	JsonWriter->WriteValue(TEXT("PrimaryGPUBrand"), FPlatformMisc::GetPrimaryGPUBrand());
	JsonWriter->WriteValue(TEXT("CPUBrand"), FPlatformMisc::GetCPUBrand());
	FString OSLabel, OSVersion;
	FPlatformMisc::GetOSVersions(OSLabel, OSVersion);
	JsonWriter->WriteValue(TEXT("OS"), OSLabel);
	JsonWriter->WriteValue(TEXT("OSVersion"), OSVersion);
	JsonWriter->WriteValue(TEXT("DeviceId"), FPlatformMisc::GetDeviceId());

	JsonWriter->WriteObjectEnd();

	JsonWriter->Close();

	TSharedRef<IHttpRequest, ESPMode::ThreadSafe> HttpRequest = FHttpModule::Get().CreateRequest();
	HttpRequest->SetHeader("Content-Type", "application/json;charset=UTF-8");
	HttpRequest->SetVerb("POST");
	HttpRequest->SetURL(UUAutoFunctionLibrary::UrlPath+"game_control/survive");
	HttpRequest->SetContentAsString(JsonStr);
	HttpRequest->OnProcessRequestComplete().BindUObject(this, &UUAutoSocketObject::SurviveResponse);
	HttpRequest->ProcessRequest();
}

void UUAutoSocketObject::SurviveResponse(FHttpRequestPtr HttpRequest, FHttpResponsePtr HttpResponse, bool bWasSuccessful)
{
	// 判断是否有效
	if (!HttpRequest.IsValid() || !HttpResponse.IsValid())
	{
		return;
	}
	// 获取响应代码
	int32 responseCode = HttpResponse->GetResponseCode();
	if (HttpRequest->GetStatus()== EHttpRequestStatus::Failed_ConnectionError)
	{
		UE_LOG(LogUAuto, Warning, TEXT("SurviveResponse 请求失败 可能是处于外网状态或者 QA服务器未启动 停止心跳发送"));
		GetCharacterTimerManager().ClearTimer(ConnectHandler);
	}
}
void UUAutoSocketObject::ControlHeartbeat()
{
	UUAutoFunctionLibrary::POSTSendData("", "heartbeat");
}
