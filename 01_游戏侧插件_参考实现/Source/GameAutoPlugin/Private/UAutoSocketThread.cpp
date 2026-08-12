// Fill out your copyright notice in the Description page of Project Settings.


#include "UAutoSocketThread.h"
#include "SocketSubsystem.h"
#include "GameAutoPlugin.h"
#include"Components/ListView.h"


uint32 UUAutoSocketThread::Run()
{
	UE_LOG(LogUAuto, Log, TEXT("UAutoSocketThread Run"))
		int32 sent = 0; 
		while (!bThreadStop && ConnectSocket)
		{
			//检测连接是否断开
			if (!ConnectSocket->Send(nullptr, 0, sent))
			{
				UE_LOG(LogUAuto, Log, TEXT("Connect lost "));
				Stop();
				LostConnectionDelegate.Broadcast(this);
				continue;
			}

			uint32 Size;
			if (ConnectSocket && ConnectSocket->HasPendingData(Size))
			{
				ReceiveData.Init(0, FMath::Min(Size, RecDataSize));
				int32 Readed;
				ConnectSocket->Recv(ReceiveData.GetData(), RecDataSize, Readed);

				TArray<uint8> GRecvBuf;
				GRecvBuf.Init(0, FMath::Min(Size, RecDataSize));
				uint8* Buff = GRecvBuf.GetData();

				FMemory::Memcpy(Buff, ReceiveData.GetData(), ReceiveData.Num());

				FUTF8ToTCHAR TCHARData(reinterpret_cast<const ANSICHAR*>(Buff), ReceiveData.Num());

				FString ReceivedString = FString(TCHARData.Length(), TCHARData.Get());

				ReceiveSwap->AddMessage(ThreadID,ReceivedString);
				if (ReceiveSocketDataDelegate.IsBound())
				{
					ReceiveSocketDataDelegate.Broadcast(ReceivedString);
				}
				else
				{
					// UE_LOG(LogUAuto, Warning, TEXT(" thread ReceiveSocketDataDelegate num is 0 "));
				}
			}

			FPlatformProcess::Sleep(0.01);
		}
	return 0;
}

void UUAutoSocketThread::SetReceiveSwap(IReceiveSwap* Swap)
{
	ReceiveSwap = Swap;
}

void UUAutoSocketThread::StartThread(FSocket* Socket, uint32 SizeSend, uint32 SizeRec)
{
	this->ConnectSocket = Socket;
	this->SendDataSize = SizeSend;
	this->RecDataSize = SizeRec;
	FRThread =  FRunnableThread::Create(this, TEXT("Receive Threald"));
	if (FRThread != nullptr)
	{
		ThreadID = FRThread->GetThreadID();
	}
	
	
}

void UUAutoSocketThread::Stop()
{
	if (ConnectSocket && !bThreadStop)
	{

		ConnectSocket->Close();
		ConnectSocket = nullptr;
		UE_LOG(LogUAuto, Log, TEXT("UUAutoSocketThread Stop"))
	}
	bThreadStop = true;
}

bool UUAutoSocketThread::SendData(FString Message)
{
	if (!bThreadStop)
	{
		TCHAR* SendMessage = Message.GetCharArray().GetData();
		int32 size = CalcUtf8NumFromString(Message);
		int32 sent = 0;
		if (size >= (int32)SendDataSize)
		{
			UE_LOG(LogUAuto, Error, TEXT("Send Data Size is Larger than Max Size for set"));
		}
		else
		{
			if (ConnectSocket && ConnectSocket->Send((uint8*)TCHAR_TO_UTF8(SendMessage), size, sent))
			{
				 //UE_LOG(LogUAuto, Warning, TEXT("___Send Succeed!"));
				return true;

			}
			else
			{
				UE_LOG(LogUAuto, Error, TEXT("___Send Failed!"));
			}
		}
	}
	return false;
}

int32 UUAutoSocketThread::CalcUtf8NumFromString(const FString& Str)
{
	int32 result = 0;

	for (int i = 0; i < Str.Len(); ++i)
	{
		if (Str[i] <= 0x7f)
		{
			result += 1;
		}
		else if (Str[i] <= 0x07ff)
		{
			result += 2;
		}
		else if (Str[i] <= 0xffff)
		{
			result += 3;
		}
		else
		{
			result += 4;
		}
	}

	return result;
}
