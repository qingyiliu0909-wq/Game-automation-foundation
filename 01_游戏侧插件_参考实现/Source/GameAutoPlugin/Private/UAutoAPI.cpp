// Fill out your copyright notice in the Description page of Project Settings.


#include "UAutoAPI.h"

#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"
#include "Serialization/JsonWriter.h"
#include "Types/ReflectionMetadata.h"
#include "Policies/CondensedJsonPrintPolicy.h"

#include "Kismet/GameplayStatics.h"
#include "GameFramework/Actor.h"

#include "UAutoRunner.h"
#include "UAutoCore.h"
#include "UAutoFunctionLibrary.h"
#include "Templates/SharedPointer.h"

#include "UAutoDebugMode.h"
#include <GameAutoPlugin.h>
#include "HAL/PlatformFilemanager.h"
#include <EngineUtils.h>





FString UAutoAPI::CloseConnectionHandler(TArray<FString> Args)
{
    return "";
}

FString UAutoAPI::GetPluginVersion(TArray<FString> Args)
{
    return "2.2";
}
FString UAutoAPI::SwitchWaysHandler(TArray<FString> Args) {
	UUAutoFunctionLibrary::NewWays = !UUAutoFunctionLibrary::NewWays;

	if (UUAutoFunctionLibrary::NewWays)
	{
		return "true";
	}
	return "false";
}

FString UAutoAPI::SwitchExcludeNotVisibleHandler(TArray<FString> Args) {
	UUAutoFunctionLibrary::ExcludeNotVisible = !UUAutoFunctionLibrary::ExcludeNotVisible;

	if (UUAutoFunctionLibrary::ExcludeNotVisible)
	{
		return "true";
	}
	return "false";
}

FString UAutoAPI::GetEngineVersion(TArray<FString> Args)
{
    return UKismetSystemLibrary::GetEngineVersion();
}

FString UAutoAPI::GetAppNameHandler(TArray<FString> Args)
{
    return FApp::GetProjectName();
}


FString UAutoAPI::ExecuteConsoleCommand(TArray<FString> Args)
{
	UE_LOG(LogUAuto, Log, TEXT("UAuto ExecuteConsoleCommand: %s"), *Args[1]);
	UKismetSystemLibrary::ExecuteConsoleCommand(UUAutoCore::Instance()->GetGameWorld(), Args[1]);
	return "success";
}


FString UAutoAPI::FindObjectHandler(TArray<FString> Args)
{
	if (Args.Num() < 3) { return "error:incorrectNumberOfParameters"; }
	FString WidgetPath = Args[1];
	FString By = Args[2];
	uint8 OperationType = 0;
	bool isGetText = false;
	if (Args.Num()>3)
	{
		if (Args[3]=="tap"){
			OperationType = 1;
		}
		else if (Args[3]=="click"){
			OperationType = 4;
		}
		else if (Args[3] == "get_text") {
			OperationType = 2;
		}
		else if (Args[3] == "set_text" && Args.Num() > 4 && Args[4]!="") {
			OperationType = 3;
		}
	}
	TMap<uint64, TWeakPtr<SWidget>>* WidgetCachePtr = UAutoRunner::Get()->GetWidgetChache();
	if (WidgetCachePtr)
	{
		if (By == "path")
		{
			TSharedPtr<SWidget> WidgetPtr = UUAutoFunctionLibrary::FindWidgetByPath(WidgetPath);

			if (WidgetPtr.IsValid())
			{
#if UE_SLATE_WITH_WIDGET_UNIQUE_IDENTIFIER
				WidgetCachePtr->Add(WidgetPtr->GetId(), WidgetPtr);
#endif
				
				FString JsonStr;
				TSharedRef<TJsonWriter<TCHAR, TCondensedJsonPrintPolicy<TCHAR>>> JsonWriter = TJsonWriterFactory<TCHAR,TCondensedJsonPrintPolicy<TCHAR>>::Create(&JsonStr);
				JsonWriter->WriteObjectStart();

				JsonWriter->WriteValue(TEXT("name"), WidgetPath);
#if UE_SLATE_WITH_WIDGET_UNIQUE_IDENTIFIER
				JsonWriter->WriteValue(TEXT("id"), FString::FromInt(WidgetPtr->GetId()));
#else
				JsonWriter->WriteValue(TEXT("id"), 0);
#endif
				FGeometry Geometry = WidgetPtr->GetTickSpaceGeometry();
				float X = Geometry.GetRenderBoundingRect().GetCenter().X;
				float Y = Geometry.GetRenderBoundingRect().GetCenter().Y;

				JsonWriter->WriteValue("x", X);
				JsonWriter->WriteValue("y", Y);
				if (OperationType == 1)
				{
					UUAutoFunctionLibrary::TapWidget(WidgetPtr);
				}
				else if (OperationType == 4)
				{
					UUAutoFunctionLibrary::ClickScreen(FVector2D(X, Y),0.1,false);
				}
				else if (OperationType == 2)
				{
					FString Text = "";
					UUAutoFunctionLibrary::GetText(WidgetPtr, Text);

					JsonWriter->WriteValue(TEXT("text"), Text);
				}
				else if (OperationType == 3) {
					UUAutoFunctionLibrary::SetText(WidgetPtr, Args[4]);
					JsonWriter->WriteValue(TEXT("text"), Args[4]);
				}


				JsonWriter->WriteObjectEnd();

				JsonWriter->Close();

				return JsonStr;
			}
		}
#if UE_SLATE_WITH_WIDGET_UNIQUE_IDENTIFIER
		if (By == "id")
		{
			int id = FCString::Atoi(*WidgetPath);
			if (WidgetCachePtr->Contains(id))
			{
				TSharedPtr<SWidget> WidgetPtr = UUAutoFunctionLibrary::FindWidgetById(id);
				if (WidgetPtr.IsValid())
				{
					
					FString JsonStr;
					TSharedRef<TJsonWriter<TCHAR, TCondensedJsonPrintPolicy<TCHAR>>> JsonWriter = TJsonWriterFactory<TCHAR,TCondensedJsonPrintPolicy<TCHAR>>::Create(&JsonStr);
					JsonWriter->WriteObjectStart();

					JsonWriter->WriteValue(TEXT("name"), UUAutoFunctionLibrary::GetPath(WidgetPtr.Get()));
					if (OperationType == 1)
					{
						UUAutoFunctionLibrary::TapWidget(WidgetPtr);
					}
					else if (OperationType == 2)
					{
						FString Text = "";
						UUAutoFunctionLibrary::GetText(WidgetPtr, Text);

						JsonWriter->WriteValue(TEXT("text"), Text);
					}
					else if (OperationType == 3) {
						UUAutoFunctionLibrary::SetText(WidgetPtr, Args[4]);
						JsonWriter->WriteValue(TEXT("text"), Args[4]);
					}
					JsonWriter->WriteValue(TEXT("id"), FString::FromInt(WidgetPtr->GetId()));

					FGeometry Geometry = WidgetPtr->GetTickSpaceGeometry();
					JsonWriter->WriteValue("x", Geometry.GetRenderBoundingRect().GetCenter().X);
					JsonWriter->WriteValue("y", Geometry.GetRenderBoundingRect().GetCenter().Y);

					JsonWriter->WriteObjectEnd();

					JsonWriter->Close();

					return JsonStr;
				}
			}
		}
#endif
	}

	return "error:notFound";
}
FString UAutoAPI::TapObjectHandler(TArray<FString> Args)
{
	if (Args.Num() < 2) { return "error:incorrectNumberOfParameters"; }
	TSharedPtr<FJsonObject> RootObject = MakeShareable(new FJsonObject());
	auto JsonReader = TJsonReaderFactory<>::Create(Args[1]);
	if (FJsonSerializer::Deserialize(JsonReader, RootObject))
	{
#if UE_SLATE_WITH_WIDGET_UNIQUE_IDENTIFIER
		int WidgetID = FCString::Atoi(*RootObject->GetStringField("id"));
		auto WidgetPtr = UUAutoFunctionLibrary::FindWidgetById(WidgetID);
#else
		FString WidgetPath = RootObject->GetStringField(("name"));
		auto WidgetPtr = UUAutoFunctionLibrary::FindWidgetByPath(WidgetPath);
#endif
		UUAutoFunctionLibrary::TapWidget(WidgetPtr);
		return Args[1];

	}

	return "error:notFound";
}

FString UAutoAPI::MouseDownHandler(TArray<FString> Args)
{
	if (Args.Num() < 2) { return "error:incorrectNumberOfParameters"; }
	TSharedPtr<FJsonObject> RootObject = MakeShareable(new FJsonObject());
	auto JsonReader = TJsonReaderFactory<>::Create(Args[1]);
	if (FJsonSerializer::Deserialize(JsonReader, RootObject))
	{
#if UE_SLATE_WITH_WIDGET_UNIQUE_IDENTIFIER
		int WidgetID = FCString::Atoi(*RootObject->GetStringField("id"));
		auto WidgetPtr = UUAutoFunctionLibrary::FindWidgetById(WidgetID);
#else
		FString WidgetPath = RootObject->GetStringField(("name"));

		auto WidgetPtr = UUAutoFunctionLibrary::FindWidgetByPath(WidgetPath);
#endif
		if (WidgetPtr.IsValid())
		{

			FGeometry Geometry = WidgetPtr->GetTickSpaceGeometry();

			FVector2D ClickPos = Geometry.GetRenderBoundingRect().GetCenter();

			FPointerEvent TouchEvent(
				0,
				0,
				ClickPos,
				ClickPos,
				1,
				true);

			FKeyEvent InKeyEvent(EKeys::Enter, FModifierKeysState(), 0, false, 0, 0);

			WidgetPtr->OnPreviewMouseButtonDown(Geometry, TouchEvent);

			return Args[1];
		}
	}
	return "error:notFound";
}

FString UAutoAPI::GetTextHandler(TArray<FString> Args)
{
	if (Args.Num() < 2) { return "error:incorrectNumberOfParameters"; }
	TSharedPtr<FJsonObject> RootObject = MakeShareable(new FJsonObject());
	auto JsonReader = TJsonReaderFactory<>::Create(Args[1]);
	if (FJsonSerializer::Deserialize(JsonReader, RootObject))
	{
#if UE_SLATE_WITH_WIDGET_UNIQUE_IDENTIFIER
		int WidgetID = FCString::Atoi(*RootObject->GetStringField("id"));
		auto WidgetPtr = UUAutoFunctionLibrary::FindWidgetById(WidgetID);
#else
		FString WidgetPath = RootObject->GetStringField(("name"));
		auto WidgetPtr = UUAutoFunctionLibrary::FindWidgetByPath(WidgetPath);
#endif
		if (WidgetPtr.IsValid())
		{
			FString Text;
			if (UUAutoFunctionLibrary::GetText(WidgetPtr, Text))
			{
				return Text;
			}
			else
			{
				return FString::Printf(TEXT("error:can not get text %s"), *Text);
			}
		}
	}

	return "error:notFound";
}

FString UAutoAPI::SetTextHandler(TArray<FString> Args)
{
	if (Args.Num() < 3) { return "error:incorrectNumberOfParameters"; }
	TSharedPtr<FJsonObject> RootObject = MakeShareable(new FJsonObject());
	auto JsonReader = TJsonReaderFactory<>::Create(Args[1]);
	if (FJsonSerializer::Deserialize(JsonReader, RootObject))
	{
#if UE_SLATE_WITH_WIDGET_UNIQUE_IDENTIFIER
		int WidgetID = FCString::Atoi(*RootObject->GetStringField("id"));
		auto WidgetPtr = UUAutoFunctionLibrary::FindWidgetById(WidgetID);
#else
		FString WidgetPath = RootObject->GetStringField(("name"));
		auto WidgetPtr = UUAutoFunctionLibrary::FindWidgetByPath(WidgetPath);
#endif
		if (WidgetPtr.IsValid())
		{
			UUAutoFunctionLibrary::SetText(WidgetPtr, Args[2]);

			return Args[1];
		}
	}
	return "error:notFound";
}

FString UAutoAPI::GetScreenHandler(TArray<FString> Args)
{
	FString JsonStr;
	TSharedRef<TJsonWriter<TCHAR, TCondensedJsonPrintPolicy<TCHAR>>> JsonWriter = TJsonWriterFactory<TCHAR,TCondensedJsonPrintPolicy<TCHAR>>::Create(&JsonStr);
	JsonWriter->WriteObjectStart();
	auto world = GEngine->GameViewport->Viewport->GetSizeXY();
	JsonWriter->WriteValue(TEXT("height"), world.X);
	JsonWriter->WriteValue(TEXT("width"), world.Y);
	JsonWriter->WriteObjectEnd();
	JsonWriter->Close();
	return JsonStr;
}

FString UAutoAPI::FindChildHandler(TArray<FString> Args)
{
	if (Args.Num() < 2) { return "error:incorrectNumberOfParameters"; }
	// 暂时默认以路径搜索
	FString Path = Args[1];
	TSharedPtr<SWidget> Widget = UUAutoFunctionLibrary::FindWidgetByPath(Path);

	if (Widget.IsValid())
	{

		FChildren* Children = Widget->GetAllChildren();
		TArray<FString> ArrChild;
		for (int i = 0; i < Children->Num(); ++i)
		{
			SWidget* Child = &Children->GetChildAt(i).Get();

			if (!Child->GetVisibility().IsVisible())
			{
				continue;
			}

			TSharedPtr<FReflectionMetaData> MetaData = Child->GetMetaData<FReflectionMetaData>();
			FString Name;
			FString Type;
			if (MetaData.IsValid() && FGameAutoPluginModule::Development)
			{
				Name = MetaData->Name.ToString();
				Type = FString::Printf(TEXT("UMG %s"), *MetaData->Class->GetName());
			}
			else
			{
				Name = Child->GetType().ToString();

				int SameTypeCount = 0;
				for (int j = 0; j < Children->Num(); ++j)
				{
					SWidget* ChildTemp = &Children->GetChildAt(j).Get();
					if (ChildTemp == Child)
						break;
					if (ChildTemp->GetType() == Child->GetType())
					{
						++SameTypeCount;
					}
				}
				Name = FString::Printf(TEXT("%s_%i"), *Name, SameTypeCount);
				Type = FString::Printf(TEXT("Slate %s"), *Name);
			}

			FString JsonStr;
			TSharedRef<TJsonWriter<TCHAR, TCondensedJsonPrintPolicy<TCHAR>>> JsonWriter = TJsonWriterFactory<TCHAR,TCondensedJsonPrintPolicy<TCHAR>>::Create(&JsonStr);
			JsonWriter->WriteObjectStart();

			JsonWriter->WriteValue(TEXT("name"), Name);
#if UE_SLATE_WITH_WIDGET_UNIQUE_IDENTIFIER
			JsonWriter->WriteValue(TEXT("id"), FString::FromInt(Child->GetId()));
#endif
			JsonWriter->WriteValue(TEXT("type"), Type);

			JsonWriter->WriteObjectEnd();

			JsonWriter->Close();

			// 由于打包时会在 UserWidgetBP 的结尾处添加对应的ID，因此这里用前面部分进行判断
			ArrChild.Add(JsonStr);
		}

		FString Arr;
		Arr.Append("[");
		if (ArrChild.Num() > 0)
		{
			Arr.Append(ArrChild[0]);
			for (size_t i = 1; i < ArrChild.Num(); i++)
			{
				Arr.Append(",");
				Arr.Append(ArrChild[i]);
			}
		}
		Arr.Append("]");
		return Arr;
	}

	return "error:notFound";
}

FString UAutoAPI::ObjectExistHandler(TArray<FString> Args)
{
	if (Args.Num() < 2) { return "error:incorrectNumberOfParameters"; }
	FString WidgetPath = Args[1];
	TSharedPtr<SWidget> Widget = UUAutoFunctionLibrary::FindWidgetByPath(WidgetPath);
	if (Widget.IsValid())
	{
		if (Widget->GetVisibility().IsVisible())
		{
			return "1";
		}
		return "0";
	}
	return "error:notFound";
}

FString UAutoAPI::ObjectExistOnlyTapHandler(TArray<FString> Args)
{
	if (Args.Num() < 2) { return "error:incorrectNumberOfParameters"; }
	FString WidgetPath = Args[1];
	TSharedPtr<SWidget> Widget = UUAutoFunctionLibrary::FindWidgetByPath(WidgetPath);

	if (Widget.IsValid())
	{
		if (Widget->GetVisibility().IsVisible())
		{
			UUAutoFunctionLibrary::TapWidget(Widget);
			return "1";
		}
		return "0";
	}
	return "error:notFound";
}

FString UAutoAPI::DebugModeHandler(TArray<FString> Args)
{
	if (Args[1] == "0") {
		return UAutoDebugMode::Get()->Start();
	}
	else {
		return UAutoDebugMode::Get()->Stop();
	}
	
}

FString UAutoAPI::FindTextHandler(TArray<FString> Args)
{
	if (Args.Num() < 2) { return "error:incorrectNumberOfParameters"; }
	TArray<FString> ArrPath = UUAutoFunctionLibrary::GetUserWidgetByText(Args[1]);
	FString JsonStr;

	TSharedRef<TJsonWriter<TCHAR, TCondensedJsonPrintPolicy<TCHAR>>> JsonWriter = TJsonWriterFactory<TCHAR,TCondensedJsonPrintPolicy<TCHAR>>::Create(&JsonStr);
	JsonWriter->WriteArrayStart();

	for (FString Item : ArrPath)
	{
		JsonWriter->WriteValue(Item);
	}
	JsonWriter->WriteArrayEnd();
	JsonWriter->Close();

	return JsonStr;
}

FString UAutoAPI::GetParentHandler(TArray<FString> Args)
{
	if (Args.Num() < 2) { return "error:incorrectNumberOfParameters"; }
	TSharedPtr<FJsonObject> RootObject = MakeShareable(new FJsonObject());
	auto JsonReader = TJsonReaderFactory<>::Create(Args[1]);
	if (FJsonSerializer::Deserialize(JsonReader, RootObject))
	{

#if UE_SLATE_WITH_WIDGET_UNIQUE_IDENTIFIER
		int WidgetID = FCString::Atoi(*RootObject->GetStringField("id"));
		auto WidgetPtr = UUAutoFunctionLibrary::FindWidgetById(WidgetID);
#else
		FString WidgetPath = RootObject->GetStringField(("name"));
		auto WidgetPtr = UUAutoFunctionLibrary::FindWidgetByPath(WidgetPath);
#endif
		TMap<uint64, TWeakPtr<SWidget>>* WidgetCachePtr = UAutoRunner::Get()->GetWidgetChache();

		if (WidgetPtr.IsValid())
		{
			auto Widget = WidgetPtr->GetParentWidget();

			if (Widget.IsValid())
			{
#if UE_SLATE_WITH_WIDGET_UNIQUE_IDENTIFIER
				WidgetCachePtr->Add(Widget->GetId(), Widget);
#endif

				FString JsonStr;
				TSharedRef<TJsonWriter<TCHAR, TCondensedJsonPrintPolicy<TCHAR>>> JsonWriter = TJsonWriterFactory<TCHAR,TCondensedJsonPrintPolicy<TCHAR>>::Create(&JsonStr);
				JsonWriter->WriteObjectStart();

				JsonWriter->WriteValue(TEXT("name"), UUAutoFunctionLibrary::GetPath(Widget.Get()));
#if UE_SLATE_WITH_WIDGET_UNIQUE_IDENTIFIER
				JsonWriter->WriteValue(TEXT("id"), UUAutoFunctionLibrary::GetID(Widget.Get()));
#endif

				JsonWriter->WriteObjectEnd();

				JsonWriter->Close();
				return JsonStr;
			}
		}
	}
	return "error:notFound";
}

FString UAutoAPI::TapScreenHandler(TArray<FString> Args)
{
	if (Args.Num()< 4){return "error:incorrectNumberOfParameters";}
	UUAutoFunctionLibrary::TapScreen(FVector2D(FCString::Atof(*Args[1]), FCString::Atof(*Args[2])), Args[3]);
	return "success";
}

FString UAutoAPI::ClickScreenHandler(TArray<FString> Args)
{
	if (Args.Num() < 4) { return "error:incorrectNumberOfParameters"; }
	bool bRight = false;
	if (Args.Num() > 4)
	{
		bRight = Args[4] == "1" || Args[4].ToLower() == "true";
	}
	UUAutoFunctionLibrary::ClickScreen(FVector2D(FCString::Atof(*Args[1]), FCString::Atof(*Args[2])), FCString::Atof(*Args[3]), bRight);
	return "success";
}

FString UAutoAPI::FindTextAndWhichClickHandler(TArray<FString> Args)
{
	if (Args.Num() < 3) { return "error:incorrectNumberOfParameters"; }
	int WhichNum = FCString::Atoi(*Args[2]);
	TArray<FString> ArrPath = UUAutoFunctionLibrary::GetUserWidgetByText(Args[1]);
	FString JsonStr = "out of index OR Not Find Text!!";
	if (ArrPath.Num() > WhichNum)
	{
		TSharedPtr<FJsonObject> RootObject = MakeShareable(new FJsonObject());
		auto JsonReader = TJsonReaderFactory<>::Create(ArrPath[WhichNum]);
		if (FJsonSerializer::Deserialize(JsonReader, RootObject))
		{
			JsonStr = ArrPath[WhichNum];
			UUAutoFunctionLibrary::ClickScreen(FVector2D(FCString::Atof(*RootObject->GetStringField("x")), FCString::Atof(*RootObject->GetStringField("y"))),0.01,false);
		}
		
	}
	return JsonStr;
}

FString UAutoAPI::FindActorByNameHandler(TArray<FString> Args)
{
	if (Args.Num() < 2) { return "error:incorrectNumberOfParameters"; }
	FString ActorName = Args[1];
	TArray<AActor*> FoundActors;
	FoundActors.Reset();

	if (UWorld* World = GEngine->GetWorldFromContextObject(GWorld, EGetWorldErrorMode::LogAndReturnNull))
	{
		for (TActorIterator<AActor> It(World,AActor::StaticClass()); It; ++It)
		{
			AActor* Actor = *It;
			if (UKismetSystemLibrary::GetDisplayName(Actor) == ActorName)
			{
				FoundActors.Add(Actor);
			}
		}
	}
	FString JsonStr;
	TSharedRef<TJsonWriter<TCHAR, TCondensedJsonPrintPolicy<TCHAR>>> JsonWriter = TJsonWriterFactory<TCHAR,TCondensedJsonPrintPolicy<TCHAR>>::Create(&JsonStr);
	JsonWriter->WriteArrayStart();

	for (AActor* Actor : FoundActors)
	{
		JsonWriter->WriteValue(Actor->GetName());
	}

	JsonWriter->WriteArrayEnd();

	JsonWriter->Close();
	return JsonStr;
}


FString UAutoAPI::MemReportHandler(TArray<FString> Args)
{
	if (UAutoRunner::CheckIsShipping())
	{
		return "error:BuildIsShipping";
	}

#if !UE_BUILD_SHIPPING

	UKismetSystemLibrary::ExecuteConsoleCommand(UUAutoCore::Instance()->GetGameWorld(), "MemReportDeferred -full");

	TArray<FString> allFilePath;
	IFileManager::Get().FindFilesRecursive(allFilePath, *FPaths::Combine(FPaths::ProfilingDir(), FString("MemReports")),TEXT("*.memreport"), true, false);
	FDateTime LastTime=NULL;
	FString FilePath = "";
	for (FString Path : allFilePath)
	{
		FFileStatData FileStat= IFileManager::Get().GetStatData(*Path);
		if (LastTime== NULL || FileStat.CreationTime > LastTime)
		{
			LastTime = FileStat.CreationTime;
			FilePath = Path;
		}
	}
	if (FilePath!="")
	{
		FilePath = FPaths::ConvertRelativePathToFull(*FilePath);
	}
	return FilePath;
#else
	return "";
#endif

}

FString UAutoAPI::LogHandler(TArray<FString> Args)
{
	if (Args.Num() < 2) { return "error:incorrectNumberOfParameters"; }
	// 默认使用 Log
	UE_LOG(LogUAuto, Log, TEXT("UAuto Log: %s"), *Args[1]);
	return "success";
}

FString UAutoAPI::SetScrollOffsetHandler(TArray<FString> Args)
{
	if (Args.Num() < 3) { return "error:incorrectNumberOfParameters"; }
	TSharedPtr<FJsonObject> RootObject = MakeShareable(new FJsonObject());
	auto JsonReader = TJsonReaderFactory<>::Create(Args[1]);
	if (FJsonSerializer::Deserialize(JsonReader, RootObject))
	{
#if UE_SLATE_WITH_WIDGET_UNIQUE_IDENTIFIER
		int WidgetID = FCString::Atoi(*RootObject->GetStringField("id"));
		auto WidgetPtr = UUAutoFunctionLibrary::FindWidgetById(WidgetID);
#else
		FString WidgetPath = RootObject->GetStringField(("name"));
		auto WidgetPtr = UUAutoFunctionLibrary::FindWidgetByPath(WidgetPath);
#endif
		if (WidgetPtr.IsValid())
		{
			if (UUAutoFunctionLibrary::SetScrollOffset(WidgetPtr, FCString::Atof(*Args[2])))
			{
				return "success";
			}

			return "fail";
		}
	}
	return "fail";
}

FString UAutoAPI::SwitchModeHandler(TArray<FString> Args)
{
	FGameAutoPluginModule::Development = !FGameAutoPluginModule::Development;
	if (FGameAutoPluginModule::Development)
	{
		return "Switch To Development";
	}
	else
	{
		return "Switch To Shipping";
	}
}

FString UAutoAPI::GetMapName(TArray<FString> Args)
{

	return UUAutoCore::Instance()->GetGameWorld()->GetMapName();
}




FString UAutoAPI::GetLogFileList(TArray<FString> Args)
{
	TArray<FString> allFilePath;
	FString  ProjectLogDirName = FPaths::ProjectLogDir();
	IFileManager::Get().FindFiles(allFilePath, *ProjectLogDirName);

	FString JsonStr;
	TSharedRef<TJsonWriter<TCHAR, TCondensedJsonPrintPolicy<TCHAR>>> JsonWriter = TJsonWriterFactory<TCHAR, TCondensedJsonPrintPolicy<TCHAR>>::Create(&JsonStr);
	JsonWriter->WriteArrayStart();

	for (FString Path : allFilePath)
	{
		//IFileManager::Get().GetStatData(*Path);
		JsonWriter->WriteValue(Path);
	}

	JsonWriter->WriteArrayEnd();

	JsonWriter->Close();


	return JsonStr;
}

FString UAutoAPI::GetLogFileInfo(TArray<FString> Args)
{
	//需要参数 文件名/行数/第几页
	FString LogFileName = Args[1];
	int32 PagesNumber = FCString::Atoi(*Args[2]);
	int32 PagesCapacity = FCString::Atoi(*Args[3]);
	FString  ProjectLogFileName = FPaths::Combine(FPaths::ProjectLogDir(), LogFileName);
	if (!FPaths::FileExists(ProjectLogFileName))
	{
		return "Not Found LOG File";
	}
	FString TxtInfo;
	int32 Length=0;
	int32 pages=0;

	if (!FFileHelper::LoadFileToString(TxtInfo, *ProjectLogFileName))
	{
		return "LoadFileToString False";
	};
	Length = TxtInfo.Len();
	pages = (Length + PagesCapacity - 1) / PagesCapacity;
	if (pages >= PagesNumber && PagesNumber != 0)
	{
		TxtInfo = TxtInfo.Mid((PagesNumber - 1) * PagesCapacity, PagesCapacity);
	}
	else {
		//PagesNumber 为0时候/PagesNumber超出范围时 截取最后的日志
		PagesNumber = pages;
		TxtInfo = TxtInfo.Mid(Length - PagesCapacity, PagesCapacity);
	}
	
	FString JsonStr;
	TSharedRef<TJsonWriter<TCHAR, TCondensedJsonPrintPolicy<TCHAR>>> JsonWriter = TJsonWriterFactory<TCHAR, TCondensedJsonPrintPolicy<TCHAR>>::Create(&JsonStr);
	JsonWriter->WriteObjectStart();
	JsonWriter->WriteValue(TEXT("Info"), TxtInfo);
	JsonWriter->WriteValue(TEXT("pages"), PagesNumber);
	JsonWriter->WriteValue(TEXT("totalPages"), pages);
	JsonWriter->WriteValue(TEXT("len"), Length);
	JsonWriter->WriteObjectEnd();
	JsonWriter->Close();
	return JsonStr;
}

FString UAutoAPI::GetLogFileContent(TArray<FString> Args)
{
	FString LogFileName = Args[1];
	FString  ProjectLogFileName = FPaths::Combine(FPaths::ProjectLogDir(), LogFileName);
	if (!FPaths::FileExists(ProjectLogFileName))
	{
		return "Not Found LOG File";
	}
	FString TxtInfo;

	if (!FFileHelper::LoadFileToString(TxtInfo, *ProjectLogFileName))
	{
		return "LoadFileToString False";
	};
	return TxtInfo;
}

FString UAutoAPI::GetLogFileTail(TArray<FString> Args)
{
	//需要参数 文件名/读取字节数
	if (Args.Num() < 2)
	{
		return "error:incorrectNumberOfParameters";
	}
	FString LogFileName = FPaths::GetCleanFilename(Args[1]);
	if (LogFileName != Args[1])
	{
		return "error:invalidLogFileName";
	}
	FString  ProjectLogFileName = FPaths::Combine(FPaths::ProjectLogDir(), LogFileName);
	if (!FPaths::FileExists(ProjectLogFileName))
	{
		return "Not Found LOG File";
	}

	int64 ReadBytes = 64 * 1024;
	if (Args.Num() > 2)
	{
		ReadBytes = FCString::Atoi64(*Args[2]);
	}
	if (ReadBytes <= 0)
	{
		ReadBytes = 64 * 1024;
	}
	if (ReadBytes > 512 * 1024)
	{
		ReadBytes = 512 * 1024;
	}

	IPlatformFile& PlatformFile = FPlatformFileManager::Get().GetPlatformFile();
	IFileHandle* FileHandle = PlatformFile.OpenRead(*ProjectLogFileName, true);
	if (FileHandle == nullptr)
	{
		return "OpenRead False";
	}

	int64 FileSize = FileHandle->Size();
	int64 Offset = FMath::Max<int64>(0, FileSize - ReadBytes);
	int64 RealReadBytes = FileSize - Offset;
	FString TxtInfo;

	if (RealReadBytes > 0)
	{
		TArray<uint8> Buffer;
		Buffer.SetNumUninitialized((int32)RealReadBytes);
		if (!FileHandle->Seek(Offset))
		{
			delete FileHandle;
			return "Seek False";
		}
		if (!FileHandle->Read(Buffer.GetData(), RealReadBytes))
		{
			delete FileHandle;
			return "Read False";
		}
		FUTF8ToTCHAR ConvertData((const ANSICHAR*)Buffer.GetData(), Buffer.Num());
		TxtInfo = FString(ConvertData.Length(), ConvertData.Get());
	}
	delete FileHandle;

	FString JsonStr;
	TSharedRef<TJsonWriter<TCHAR, TCondensedJsonPrintPolicy<TCHAR>>> JsonWriter = TJsonWriterFactory<TCHAR, TCondensedJsonPrintPolicy<TCHAR>>::Create(&JsonStr);
	JsonWriter->WriteObjectStart();
	JsonWriter->WriteValue(TEXT("Info"), TxtInfo);
	JsonWriter->WriteValue(TEXT("start"), Offset);
	JsonWriter->WriteValue(TEXT("size"), RealReadBytes);
	JsonWriter->WriteValue(TEXT("len"), FileSize);
	JsonWriter->WriteObjectEnd();
	JsonWriter->Close();
	return JsonStr;
}

FString UAutoAPI::GetLogFileChunk(TArray<FString> Args)
{
	//需要参数 文件名/偏移量/读取字节数
	if (Args.Num() < 4)
	{
		return "error:incorrectNumberOfParameters";
	}
	FString LogFileName = FPaths::GetCleanFilename(Args[1]);
	if (LogFileName != Args[1])
	{
		return "error:invalidLogFileName";
	}
	FString  ProjectLogFileName = FPaths::Combine(FPaths::ProjectLogDir(), LogFileName);
	if (!FPaths::FileExists(ProjectLogFileName))
	{
		return "Not Found LOG File";
	}

	int64 Offset = FCString::Atoi64(*Args[2]);
	int64 ReadBytes = FCString::Atoi64(*Args[3]);
	if (Offset < 0)
	{
		Offset = 0;
	}
	if (ReadBytes <= 0)
	{
		ReadBytes = 64 * 1024;
	}
	if (ReadBytes > 512 * 1024)
	{
		ReadBytes = 512 * 1024;
	}

	IPlatformFile& PlatformFile = FPlatformFileManager::Get().GetPlatformFile();
	IFileHandle* FileHandle = PlatformFile.OpenRead(*ProjectLogFileName, true);
	if (FileHandle == nullptr)
	{
		return "OpenRead False";
	}

	int64 FileSize = FileHandle->Size();
	if (Offset > FileSize)
	{
		Offset = FileSize;
	}
	int64 RealReadBytes = FMath::Min<int64>(ReadBytes, FileSize - Offset);
	FString TxtInfo;

	if (RealReadBytes > 0)
	{
		TArray<uint8> Buffer;
		Buffer.SetNumUninitialized((int32)RealReadBytes);
		if (!FileHandle->Seek(Offset))
		{
			delete FileHandle;
			return "Seek False";
		}
		if (!FileHandle->Read(Buffer.GetData(), RealReadBytes))
		{
			delete FileHandle;
			return "Read False";
		}
		FUTF8ToTCHAR ConvertData((const ANSICHAR*)Buffer.GetData(), Buffer.Num());
		TxtInfo = FString(ConvertData.Length(), ConvertData.Get());
	}
	delete FileHandle;

	FString JsonStr;
	TSharedRef<TJsonWriter<TCHAR, TCondensedJsonPrintPolicy<TCHAR>>> JsonWriter = TJsonWriterFactory<TCHAR, TCondensedJsonPrintPolicy<TCHAR>>::Create(&JsonStr);
	JsonWriter->WriteObjectStart();
	JsonWriter->WriteValue(TEXT("Info"), TxtInfo);
	JsonWriter->WriteValue(TEXT("start"), Offset);
	JsonWriter->WriteValue(TEXT("size"), RealReadBytes);
	JsonWriter->WriteValue(TEXT("len"), FileSize);
	JsonWriter->WriteObjectEnd();
	JsonWriter->Close();
	return JsonStr;
}

FString UAutoAPI::InputKeys(TArray<FString> Args) {
	TArray<FString> KeyArray;
	Args[1].ParseIntoArray(KeyArray,TEXT(","), true);
	bool CPlayer = false;
	if (Args.Num()>=2 && Args[3]=="1")
	{
		CPlayer = true;
	}
	if (KeyArray.Num()>1 && Args[2] == "click")
	{
		for (FString var : KeyArray)
		{
			UUAutoFunctionLibrary::InputKey(var, "press", CPlayer);
			FPlatformProcess::Sleep(0.01f);
		}
		for (FString var : KeyArray)
		{
			UUAutoFunctionLibrary::InputKey(var, "release", CPlayer);
			FPlatformProcess::Sleep(0.01f);
		}
	}
	else {
		for (FString var : KeyArray)
		{
			UUAutoFunctionLibrary::InputKey(var, Args[2], CPlayer);
			FPlatformProcess::Sleep(0.01f);
		}
	}
	
	return "Success";
}

FString UAutoAPI::InputAxis(TArray<FString> Args) {
	UUAutoFunctionLibrary::InputAxis(Args[1], Args[2]);
	return "Success";
}

FString UAutoAPI::TestHandler(TArray<FString> Args)
{
	/*FString JsonStr;
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
	return JsonStr;*/
	/*FString name = Args[1];
	UWorld* World = UUAutoCore::Instance()->GetGameWorld();
	if (World) {
		APlayerController* playerController = UGameplayStatics::GetPlayerController(World, 0);
		if (playerController)
		{
			EInputEvent event = IE_Pressed;
			playerController->InputKey(FKey(FName(*name)), event, 1, false);
		}
	}*/
	return "";
}
