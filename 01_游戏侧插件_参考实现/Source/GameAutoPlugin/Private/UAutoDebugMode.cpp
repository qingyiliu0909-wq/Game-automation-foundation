// Fill out your copyright notice in the Description page of Project Settings.


#include "UAutoDebugMode.h"
#include "Components/Button.h"
#include "Serialization/JsonWriter.h"
#include "Policies/CondensedJsonPrintPolicy.h"
#include "Kismet/GameplayStatics.h"
#include "Types/ReflectionMetadata.h"
#include "UAutoFunctionLibrary.h"
#include <GameAutoPlugin.h>

UAutoDebugMode* UAutoDebugMode::Get()
{
	static TUniquePtr<UAutoDebugMode> Instance = MakeUnique<UAutoDebugMode>();
	return Instance.Get();
}

bool UAutoDebugMode::Tick(float DeltaTime, TArray<FString>& Results)
{
	bool needSend = false;

	if (bDebugMode)
	{
		Timedelay += DeltaTime;
		TSet<FKey> Keys = FSlateApplication::Get().GetPressedMouseButtons();

		if (Keys.Contains(EKeys::LeftMouseButton))
		{
			PressTime += DeltaTime;
			// 第一次按下，尝试获取对应指向 Widget，并计算路径
			if (bIsPressing == false)
			{
				bool hasWidget;
				TSharedPtr<SWidget> Widget = nullptr;
#if WITH_EDITOR
				hasWidget = GetCurWidget(Widget);
#else
				APlayerController* PlayerController = UGameplayStatics::GetPlayerController(GWorld, 0);

				// 这里针对移动端和PC端使用不同的方式获取点击位置
#if PLATFORM_IOS || PLATFORM_ANDROID || PLATFORM_OPENHARMONY
				float x, y;
				PlayerController->GetMousePosition(x, y);
				FVector2D Position(x, y);
#elif PLATFORM_WINDOWS || PLATFORM_MAC
				FVector2D Position = FSlateApplication::Get().GetCursorPos();
#else
				float x, y;
				PlayerController->GetMousePosition(x, y);
				FVector2D Position(x, y);
#endif

				hasWidget = GetCurWidget(Widget, Position);
#endif

				if (hasWidget && Widget.IsValid())
				{
					FString Path = GetWidgetPath(Widget.Get());

					if (LastWidget.IsValid() && Widget.IsValid() && LastWidget != Widget)
					{
						// 切换了焦点控件，尝试获取可输入文本框的文本
						FString TextValue;
						if (UUAutoFunctionLibrary::GetText(LastWidget, TextValue))
						{
							FString EditableTextPath = GetWidgetPath(LastWidget.Get());

							FString JsonStr;
							TSharedRef<TJsonWriter<TCHAR, TCondensedJsonPrintPolicy<TCHAR>>> JsonWriter = TJsonWriterFactory<TCHAR, TCondensedJsonPrintPolicy<TCHAR>>::Create(&JsonStr);
							JsonWriter->WriteObjectStart();

							JsonWriter->WriteValue(TEXT("name"), EditableTextPath);
							JsonWriter->WriteValue(TEXT("type"), LastWidget->GetType().ToString());
							JsonWriter->WriteValue(TEXT("value"), TextValue);
							JsonWriter->WriteValue(TEXT("time"), FString::SanitizeFloat(Timedelay));

							JsonWriter->WriteObjectEnd();

							JsonWriter->Close();

							Results.Add(JsonStr);
							needSend = true;
						}
					}

					// 如果控件是按钮，录制出 tap 的脚本
					FString Type = Widget->GetType().ToString();

					// GEngine->AddOnScreenDebugMessage(-1, 5, FColor::Red, Type);

					if (Type.Contains("Button") || Type == "SCheckBox" || Type == "SComboBox< TSharedPtr<FString> >")
					{
						FString JsonStr;
						TSharedRef<TJsonWriter<TCHAR, TCondensedJsonPrintPolicy<TCHAR>>> JsonWriter = TJsonWriterFactory<TCHAR, TCondensedJsonPrintPolicy<TCHAR>>::Create(&JsonStr);
						JsonWriter->WriteObjectStart();

						JsonWriter->WriteValue(TEXT("name"), Path);
						JsonWriter->WriteValue(TEXT("type"), Type);
						JsonWriter->WriteValue(TEXT("time"), FString::SanitizeFloat(Timedelay));

						JsonWriter->WriteObjectEnd();

						JsonWriter->Close();

						Results.Add(JsonStr);
						needSend = true;
					}
					else
					{
						UE_LOG(LogUAuto, Log, TEXT("UAuto DebugModel Type is: %s not Button"), *Type);
					}

					LastWidget = Widget;

				}
				else
				{

					if (LastWidget.IsValid() && LastWidget != Widget)
					{
						// 切换了焦点控件，尝试获取可输入文本框的文本
						FString TextValue;
						if (UUAutoFunctionLibrary::GetText(LastWidget, TextValue))
						{
							FString EditableTextPath = GetWidgetPath(LastWidget.Get());

							FString JsonStr;
							TSharedRef<TJsonWriter<TCHAR, TCondensedJsonPrintPolicy<TCHAR>>> JsonWriter = TJsonWriterFactory<TCHAR, TCondensedJsonPrintPolicy<TCHAR>>::Create(&JsonStr);
							JsonWriter->WriteObjectStart();

							JsonWriter->WriteValue(TEXT("name"), EditableTextPath);
							JsonWriter->WriteValue(TEXT("type"), LastWidget->GetType().ToString());
							JsonWriter->WriteValue(TEXT("value"), TextValue);
							JsonWriter->WriteValue(TEXT("time"), FString::SanitizeFloat(Timedelay));

							JsonWriter->WriteObjectEnd();

							JsonWriter->Close();

							Results.Add(JsonStr);
							needSend = true;
						}

					}
				}

				// 获取到一个不是可交互的 Widget，如果不是 ViewPort，直接发送路径回去
				if (Widget.IsValid() && !hasWidget)
				{
					if (Widget->GetType() != "SViewport" && Widget->GetType()!="SVirtualJoystick")
					{
						LastWidget = Widget;
						FString Path = GetWidgetPath(Widget.Get());
						FString Type = Widget->GetType().ToString();

						FString JsonStr;
						TSharedRef<TJsonWriter<TCHAR, TCondensedJsonPrintPolicy<TCHAR>>> JsonWriter = TJsonWriterFactory<TCHAR,TCondensedJsonPrintPolicy<TCHAR>>::Create(&JsonStr);
						JsonWriter->WriteObjectStart();

						JsonWriter->WriteValue(TEXT("name"), Path);
						JsonWriter->WriteValue(TEXT("type"), Type);
						JsonWriter->WriteValue(TEXT("time"), FString::SanitizeFloat(Timedelay));

						JsonWriter->WriteObjectEnd();

						JsonWriter->Close();

						Results.Add(JsonStr);
						needSend = true;
					}
				}
			}

			bIsPressing = true;


			if (needSend)
			{
				Timedelay = 0.0f;
			}

			// 长按 5 秒结束 DebugMode
			if (PressTime > 5.0)
			{
				Results.Add(Stop());
				needSend = true;
			}
		}
		else
		{
			PressTime = 0;
			bIsPressing = false;
		}
	}
	return needSend;
}

bool UAutoDebugMode::GetCurWidget(TSharedPtr<SWidget>& WidgetPtr)
{
	return GetCurWidget(WidgetPtr, FSlateApplication::Get().GetCursorPos());
}

bool UAutoDebugMode::GetCurWidget(TSharedPtr<SWidget>& WidgetPtr, FVector2D Position)
{
	FWidgetPath WidgetPath = FSlateApplication::Get().LocateWindowUnderMouse(Position,
		FSlateApplication::Get().GetInteractiveTopLevelWindows(), true);

	if (WidgetPath.IsValid())
	{
		FArrangedChildren Paths = WidgetPath.Widgets;
		WidgetPtr = Paths[Paths.Num() - 1].Widget;
		for (int i = Paths.Num() - 1; i >= 0; --i)
		{
			TSharedRef<SWidget> Widget = Paths[i].Widget;
			// 判断是否可以进行交互
			if (Widget->GetVisibility().IsVisible() && Widget->IsInteractable())
			{
				TSharedPtr<SWidget> Parent = Widget;

#if UE_BUILD_SHIPPING
				WidgetPtr = Widget;
				return true;
#else
				while (Parent)
				{
					TSharedPtr<FReflectionMetaData> MetaData = Parent->GetMetaData<FReflectionMetaData>();
					if (MetaData.IsValid())
					{
						WidgetPtr = Parent;
						return true;
					}
					Parent = Parent->GetParentWidget();
				}
#endif
			}
		}
	}
	return false;
}

FString UAutoDebugMode::GetWidgetPath(SWidget* Widget)
{
	FString Path = UUAutoFunctionLibrary::GetPath(Widget);
	return Path;
}

FString UAutoDebugMode::Start()
{
	PressTime = 0.0f;
	Timedelay = 0.0f;
	bDebugMode = true;
	return "Open Debug Mode";
}

FString UAutoDebugMode::Stop()
{
	bDebugMode = false;
	return "Close Debug Mode";
}

