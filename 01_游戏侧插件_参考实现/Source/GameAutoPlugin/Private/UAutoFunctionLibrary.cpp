// Fill out your copyright notice in the Description page of Project Settings.


#include "UAutoFunctionLibrary.h"
#include "Serialization/JsonWriter.h"
#include "Types/ReflectionMetadata.h"
#include "Policies/CondensedJsonPrintPolicy.h"
#include "Widgets/SViewport.h"

#include "Widgets/Input/SEditableText.h"
#include "Widgets/Input/SEditableTextBox.h"
#include "Widgets/Input/SMultiLineEditableTextBox.h"

#include "Widgets/Text/SMultiLineEditableText.h"
#include "Widgets/Text/SRichTextBlock.h"

#include "Widgets/Layout/SScrollBox.h"

#include "UAutoRunner.h"
#include "GameAutoPlugin.h"
#include "Kismet/GameplayStatics.h"
#include "UAutoCore.h"
#include "EngineUtils.h"

#include "Blueprint/UserWidget.h"
#include "Blueprint/WidgetTree.h"

#include "HttpModule.h"
#include "UI/EditableText/SEMEditableText.h"
#include <Interfaces/IHttpRequest.h>


TSet<FKey> UUAutoFunctionLibrary::PressedKeys;

FString UUAutoFunctionLibrary::UrlPath = "http://127.0.0.1:8101/";

TSharedPtr<SWidget> UUAutoFunctionLibrary::SConstraintCanvaWidget;

bool UUAutoFunctionLibrary::NewWays = true;

bool UUAutoFunctionLibrary::ExcludeNotVisible = true;

//FTimerHandle UUAutoFunctionLibrary::UAutoTimerHandle ;

AActor* UUAutoFunctionLibrary::FindActorByIDName(FString IDName)
{

	if (UWorld* World = GEngine->GetWorldFromContextObject(UUAutoCore::Instance()->GetGameWorld(), EGetWorldErrorMode::LogAndReturnNull))
	{
		for (TActorIterator<AActor> It(World, AActor::StaticClass()); It; ++It)
		{
			AActor* Actor = *It;
			if (Actor->GetName() == IDName)
			{
				return Actor;
			}
		}
	}
	return nullptr;
}

void UUAutoFunctionLibrary::NameAddIndex(FString& Name, const SWidget* Widget, bool IsUserWidget)
{
	if (!Widget->IsParentValid())
	{
		return;
	}
	FChildren* Child = Widget->GetParentWidget()->GetAllChildren();
	int Index = 0;
	for (int j = 0; j < Child->Num(); ++j)
	{
		SWidget* Item = &Child->GetChildAt(j).Get();

		if (Item == Widget)
		{
			// 在最后的位置添加下标
			Name.Append(TEXT("_") + FString::FromInt(Index));
			break;
		}

		// 针对 UserWidgetBP，使用跟查找那里一样的逻辑判断是否同名
		if (IsUserWidget)
		{

			FString ItemName = Item->GetMetaData<FReflectionMetaData>()->Name.ToString();
			if (ItemName.StartsWith(Name))
			{
				FString UserWidgetID = ItemName.RightChop(Name.Len());
				if (UserWidgetID.Len() > 0)
				{
					UserWidgetID.RemoveAt(0);
					if (UserWidgetID.IsNumeric())
					{
						++Index;
					}
				}
			}
		}
		else
		{
			// 对于 UserWidgetBP 的父级，都是 UE 默认 SWidget，可以理解为固定的，使用类型进行判断
			if (Item->GetType() == Widget->GetType())
			{
				++Index;
			}
		}
	}
}

FString UUAutoFunctionLibrary::GetPath(UWidget* Widget)
{
	SWidget* CurrentWidget = &Widget->TakeWidget().Get();
	return GetPath(CurrentWidget);
}

FString UUAutoFunctionLibrary::GetPath(SWidget* Widget)
{

	TArray<FString> PathList;

	while (Widget)
	{
		TSharedPtr<FReflectionMetaData> MetaData = Widget->GetMetaData<FReflectionMetaData>();

		if (FGameAutoPluginModule::Development && MetaData.IsValid())
		{
			FString Name = MetaData->Name.ToString();

			TSharedPtr<SWidget> Parent = Widget->GetParentWidget();                  

			// 到达 UserWidget 根，开始这里开始使用名字和下标标记 SWidget
			if (!Parent->GetMetaData<FReflectionMetaData>().IsValid())
			{
				// 由于在打包以后，UserWidget 根的名字会被添加上 ID，这里将 ID 标记去掉，使用下标做替代
				TArray<FString> Items;
				Name.ParseIntoArray(Items, TEXT("_"), true);

				if (Items.Num() > 1)
				{
					Items.RemoveAt(Items.Num() - 1);
					Name = FString::Join(Items, TEXT("_"));
				}

				NameAddIndex(Name, Widget, true);
				PathList.Insert(Name, 0);

			}
			else
			{
				PathList.Insert(Name, 0);
			}
		}
		else
		{
			FString TypeName = Widget->GetType().ToString();
			FString SaveName(TypeName);

			NameAddIndex(SaveName, Widget);
			PathList.Insert(SaveName, 0);
			// 搜索到 Viewport 就停下来
			if (TypeName == "SViewport")
			{
				break;
			}
			
			if (NewWays && TypeName == "SGameLayerManager") {
				if (PathList.Num()>=6)
				{
					for (int32 i = 0; i <= 6; i++)
					{
						PathList.RemoveAt(0);
					}
					break;
				}
				
			}
		}

		Widget = Widget->GetParentWidget().Get();
	}

	//UE_LOG(LogUAuto, Log, TEXT("%s"), *Path);
	FString Path = FString::Join(PathList, TEXT("/"));
	return "/" + Path;
}

#if UE_SLATE_WITH_WIDGET_UNIQUE_IDENTIFIER
FString UUAutoFunctionLibrary::GetID(SWidget* Widget)
{
	FString ID;

	if (Widget)
	{
		// TSharedPtr<FReflectionMetaData> MetaData = Widget->GetMetaData<FReflectionMetaData>();
		// ID = FString::FromInt( MetaData.Get()->SourceObject->GetUniqueID());
#if UE_SLATE_WITH_WIDGET_UNIQUE_IDENTIFIER
		ID = FString::FromInt(Widget->GetId());
#endif

	}

	return ID;
}
#endif

TArray<FString> UUAutoFunctionLibrary::GetUserWidgetByText(FString text)
{
	TArray<FString> ret;
	SWidget* Widget = FSlateApplication::Get().GetGameViewport().Get();
	if (Widget==nullptr)
	{
		return ret;
	}
	TArray<FString> RetWidgetName;
	TArray<FString> RetWidgetID;
	TArray<FString> RetWidgetText;
	TArray<FVector2D> Center;
	TArray<int> Visible;
	FChildren* Children = Widget->GetAllChildren();
	bool hasFound = false;
	WidgetIterText(RetWidgetName, RetWidgetID, RetWidgetText, Center, Visible, Children, text);
	if (text == "&")
	{
		for (auto i = 0; i < RetWidgetName.Num(); i++)
		{
			if (RetWidgetText[i]!="" && Visible[i]==1 && !Center[i].IsZero())
			{
				ret.Add(RetWidgetText[i]);
			}
		}
	}
	else
	{
		for (auto i = 0; i < RetWidgetName.Num(); i++)
		{
			FString JsonStr;

			TSharedRef<TJsonWriter<TCHAR, TCondensedJsonPrintPolicy<TCHAR>>> JsonWriter = TJsonWriterFactory<TCHAR, TCondensedJsonPrintPolicy<TCHAR>>::Create(&JsonStr);
			JsonWriter->WriteObjectStart();
			JsonWriter->WriteValue("name", RetWidgetName[i]);
#if UE_SLATE_WITH_WIDGET_UNIQUE_IDENTIFIER
			JsonWriter->WriteValue("id", RetWidgetID[i]);
#endif
			JsonWriter->WriteValue("text", RetWidgetText[i]);
			JsonWriter->WriteValue("x", Center[i].X);
			JsonWriter->WriteValue("y", Center[i].Y);
			JsonWriter->WriteValue("visible", Visible[i]);
			JsonWriter->WriteObjectEnd();
			JsonWriter->Close();

			ret.Add(JsonStr);
		}
	}
	
	return ret;
}

void UUAutoFunctionLibrary::WidgetIterText(TArray<FString>& RetWidgetName, TArray<FString>& RetWidgetID,
	TArray<FString>& RetWidgetText, TArray<FVector2D>& Center, TArray<int>& Visible, FChildren* Children, FString text)
{
	FString TextValue ;
	for (int j = 0; j < Children->Num(); ++j)
	{
		auto child = Children->GetChildAt(j);

		TextValue.Empty();
		if (GetText(child, TextValue))
		{
			if (text=="&" || TextValue.Contains(text))
			{
				RetWidgetName.Add(GetPath(&child.Get()));
#if UE_SLATE_WITH_WIDGET_UNIQUE_IDENTIFIER
				RetWidgetID.Add(GetID(&child.Get()));
#endif
				RetWidgetText.Add(TextValue);
				Center.Add(child->GetTickSpaceGeometry().GetRenderBoundingRect().GetCenter());
				Visible.Add(child->GetVisibility().IsVisible());
			}
		}

		WidgetIterText(RetWidgetName, RetWidgetID, RetWidgetText, Center, Visible, child->GetAllChildren(), text);
	}
}

TSharedPtr<SWidget> UUAutoFunctionLibrary::GetSConstraintCanvaWidget()
{
	FString ConstraintCanvaPath = "SViewport_0/SGameLayerManager_0/SDPIScaler_0/SVerticalBox_0/SOverlay_0/SOverlay_0";
#if WITH_EDITOR
	ConstraintCanvaPath= "SViewport_0/SOverlay_0/SGameLayerManager_0/SDPIScaler_0/SVerticalBox_0/SOverlay_0/SOverlay_0";
#endif
	TArray<FString> PathList;
	ConstraintCanvaPath.ParseIntoArray(PathList, TEXT("/"), true);
	auto ViewportPtr = FSlateApplication::Get().GetGameViewport();
	TSharedPtr<SWidget> Widget;
	if (ViewportPtr.IsValid())
	{
		Widget = ViewportPtr.Get()->GetParentWidget();
		for (FString PathItem : PathList)
		{
			Widget = GetChildByNameAndIndex(Widget, PathItem);

		}
		if (Widget.IsValid())
		{
			return Widget;
		}
	}
	return nullptr;

}

TSharedPtr<SWidget> UUAutoFunctionLibrary::FindWidgetByPathBase(FString Path, TSharedPtr<SWidget> StartWidget)
{
	if (ExcludeNotVisible && StartWidget->GetVisibility() == EVisibility::Collapsed) return nullptr;
	TSharedPtr<SWidget> EndWidget;
	TSharedPtr<SWidget> Widget = StartWidget;
	int indexIndex;
	FString WidgetName = "";
	while (Path.Len() > 0)
	{
		if (Path.StartsWith(TEXT("/"))) Path = Path.RightChop(1);
		Path.FindChar('/', indexIndex);
		WidgetName = Path;
		if (indexIndex > 0) WidgetName = Path.Left(indexIndex);
		Widget = GetChildByNameAndIndex(Widget, WidgetName);
		if (!Widget.IsValid())
		{
			EndWidget.Reset();
			break;
		}
		EndWidget = Widget;
		if (indexIndex <= 0) break;
		Path = Path.RightChop(indexIndex);
	}
	if (!EndWidget.IsValid() || (ExcludeNotVisible && !EndWidget->GetVisibility().IsVisible()))  return nullptr;
	return EndWidget;
}

TSharedPtr<SWidget> UUAutoFunctionLibrary::FindWidgetByPath(FString Path)
{
	TSharedPtr<SWidget> WidgetPtr;
	
	if (NewWays)
	{
		if (!SConstraintCanvaWidget)
		{
			SConstraintCanvaWidget = UUAutoFunctionLibrary::GetSConstraintCanvaWidget();
		}
		WidgetPtr = SConstraintCanvaWidget;
	}
	else 
	{
		auto ViewportPtr = FSlateApplication::Get().GetGameViewport();
		if (ViewportPtr.IsValid())
		{
			SWidget* Viewport = ViewportPtr.Get();
			WidgetPtr = Viewport->GetParentWidget();
		}
	}
	
	if (WidgetPtr.IsValid())
	{
		if (NewWays)
		{
			FChildren* Children = WidgetPtr->GetAllChildren();
			TSharedPtr<SWidget> Widget;
			for (int i = Children->Num() - 1; i >= 0; --i)
			{
				Widget=GetChildByNameAndIndex(Children->GetChildAt(i), "SObjectWidget_0");
				if (Widget.IsValid())
				{
					TSharedPtr<SWidget> FindWidgetPtr = FindWidgetByPathBase(Path, Widget);
					if (FindWidgetPtr.IsValid())
					{
						return FindWidgetPtr;
					}
				}
				
			}
		}
		else 
		{
			return  FindWidgetByPathBase(Path, WidgetPtr);
		}
	}
	//UE_LOG(LogUAuto, Error, TEXT("[UAuto] Not Found Error: %s"), *Path);
	return nullptr;
}

TSharedPtr<SWidget> UUAutoFunctionLibrary::FindWidgetById(uint32 Id)
{
	TMap<uint64, TWeakPtr<SWidget>>* WidgetCache = UAutoRunner::Get()->GetWidgetChache();
	if (WidgetCache->Contains(Id))
	{
		TWeakPtr<SWidget>* Widget = WidgetCache->Find(Id);
		if (Widget && Widget->IsValid() && Widget->Pin()->GetVisibility().IsVisible())
		{
			return Widget->Pin();
		}
	}
	return nullptr;
}

void UUAutoFunctionLibrary::TapWidget(TSharedPtr<SWidget> WidgetPtr)
{
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

		if (!WidgetPtr->GetType().ToString().Contains("Button")) {
			WidgetPtr->OnTouchStarted(Geometry, TouchEvent);
			if (WidgetPtr.IsValid())
			{
				WidgetPtr->OnTouchEnded(Geometry, TouchEvent);
			}
			
		}
		else
		{
			WidgetPtr->OnKeyDown(Geometry, InKeyEvent);
			WidgetPtr->OnKeyUp(Geometry, InKeyEvent);
		}


	}
}

TSharedPtr<SWidget> UUAutoFunctionLibrary::GetChildByNameAndIndex(TSharedPtr<SWidget> Parent, FString SWidgetName)
{
	TSharedPtr<SWidget> Widget = nullptr;

	if (Parent.IsValid())
	{
		TArray<FString> Items;
		SWidgetName.ParseIntoArray(Items, TEXT("_"), true);
		FChildren* Children = Parent->GetAllChildren();
		if (Items.Num() == 0 || Children == nullptr)
		{
			return nullptr;
		}
		int Index = FCString::Atoi(*Items[Items.Num() - 1]);
		int CurIndex = 0;

		// 移除自己添加的下标，还原成原本的名字
		Items.RemoveAt(Items.Num() - 1);
		FString OriginName = FString::Join(Items, TEXT("_"));
		for (int i = 0; i < Children->Num(); ++i)
		{
			TSharedPtr<SWidget> ChildPtr = Children->GetChildAt(i);
			if (ChildPtr.IsValid())
			{
				SWidget* Child = ChildPtr.Get();
				TSharedPtr<FReflectionMetaData> MetaData = Child->GetMetaData<FReflectionMetaData>();
				FString SlateName = Child->GetType().ToString();
				FString UmgName;
				if (MetaData.IsValid())
				{
					UmgName = MetaData->Name.ToString();
				}

				if (UmgName == OriginName || SlateName == OriginName)
				{
					if (CurIndex == Index)
					{
						Widget = ChildPtr;
						// 只有确保了找到对应下标的控件才返回
						return Widget;
					}
					++CurIndex;
				}

				FString Name;
				if (UmgName.StartsWith(OriginName))
				{
					Name = UmgName;
				}
				else if (SlateName.StartsWith(OriginName))
				{
					Name = SlateName;
				}

				// 由于打包时会在 UserWidgetBP 的结尾处添加对应的ID，因此这里用前面部分进行判断
				if (Name.StartsWith(OriginName))
				{
					Name = Name.RightChop(OriginName.Len());
					if (Name.Len() > 0)
					{
						Name.RemoveAt(0);
						if (Name.IsNumeric())
						{
							if (CurIndex == Index)
							{
								Widget = ChildPtr;
								// 只有确保了找到对应下标的控件才返回
								return Widget;
							}
							++CurIndex;
						}
					}
				}
			}
		}
	}

	return nullptr;
}

bool UUAutoFunctionLibrary::GetText(TSharedPtr<SWidget> Widget, FString& Text)
{

	FName Type = Widget->GetType();

	if (Type == "STextBlock")
	{
		STextBlock* TextBlock = (STextBlock*)(Widget.Get());
		if (!TextBlock->IsVolatile())
		{
			FText TextInfo = TextBlock->GetText();
			if (!TextInfo.IsEmptyOrWhitespace())
			{
				Text = TextInfo.ToString();
			}
			else
			{
				return false;
			}
		}
		
		return true;
	}
	else if (Type == "SEMEditableText")
	{
		SEMEditableText* EMEditableText = (SEMEditableText*)(Widget.Get());
		FText TextInfo = EMEditableText->GetText();
		if (!TextInfo.IsEmptyOrWhitespace())
		{
			Text = TextInfo.ToString();
		}
		else
		{
			return false;
		}
		return true;
	}
	else if (Type == "SRichTextBlock")
	{
		SRichTextBlock* RichTextBlock = (SRichTextBlock*)(Widget.Get());
		FText TextInfo = RichTextBlock->GetText();
		if (!TextInfo.IsEmptyOrWhitespace())
		{
			Text = TextInfo.ToString();
		}
		else
		{
			return false;
		}
		return true;
	}
	else if (Type == "SEditableText")
	{
		SEditableText* EditableText = (SEditableText*)(Widget.Get());
		FText TextInfo = EditableText->GetText();
		if (!TextInfo.IsEmptyOrWhitespace())
		{
			Text = TextInfo.ToString();
		}
		else
		{
			return false;
		}
		return true;
	}
	else if (Type == "SEditableTextBox")
	{
		SEditableTextBox* EditableTextBox = (SEditableTextBox*)(Widget.Get());
		FText TextInfo = EditableTextBox->GetText();
		if (!TextInfo.IsEmptyOrWhitespace())
		{
			Text = TextInfo.ToString();
		}
		else
		{
			return false;
		}
		return true;
	}
	else if (Type == "SMultiLineEditableText")
	{
		SMultiLineEditableText* MultiLineEditableText = (SMultiLineEditableText*)(Widget.Get());
		FText TextInfo = MultiLineEditableText->GetText();
		if (!TextInfo.IsEmptyOrWhitespace())
		{
			Text = TextInfo.ToString();
		}
		else
		{
			return false;
		}
		return true;
	}
	else if (Type == "SMultiLineEditableTextBox")
	{
		SMultiLineEditableTextBox* MultiLineEditableTextBox = (SMultiLineEditableTextBox*)(Widget.Get());
		FText TextInfo = MultiLineEditableTextBox->GetText();
		if (!TextInfo.IsEmptyOrWhitespace())
		{
			Text = TextInfo.ToString();
		}
		else
		{
			return false;
		}
		return true;
	}
	// 如果都不是使用原生 TextSWidget，尝试通过 UWidget 来获取文本
	else
	{
		TSharedPtr<FReflectionMetaData> MetaData = Widget->GetMetaData<FReflectionMetaData>();
		if (MetaData.IsValid())
		{
			auto obj = MetaData.Get() ? Widget->GetMetaData<FReflectionMetaData>()->SourceObject : nullptr;
			if (obj.IsValid())
			{
				UFunction* GetText = obj->FindFunction("GetText");
				if (GetText)
				{
					struct GetText_Func_Params   //定义一个结构用来包装参数和返回值
					{
						FText ReturnValue;
					};
					GetText_Func_Params Params;

					obj->ProcessEvent(GetText, &Params);
					Text = Params.ReturnValue.ToString();
					return true;
				}
			}
		}
	}

	Text = Type.ToString();
	return false;
}

void UUAutoFunctionLibrary::SetText(TSharedPtr<SWidget> Widget, FString Text)
{
	FName Type = Widget->GetType();
	FText NewText = FText::FromString(Text);

	FSlateApplication& SlateApplication = FSlateApplication::Get();

	// 设置焦点，以便能够正常触发 OnCommit 事件
	SlateApplication.SetUserFocus(0, Widget, EFocusCause::Mouse);

	if (Type == "STextBlock")
	{
		STextBlock* TextBlock = (STextBlock*)(Widget.Get());
		TextBlock->SetText(NewText);
	}
	else if (Type == "SEMEditableText")
	{
		SEMEditableText* EMEditableText = (SEMEditableText*)(Widget.Get());
		EMEditableText->SetText(NewText);
	}
	else if (Type == "SRichTextBlock")
	{
		SRichTextBlock* RichTextBlock = (SRichTextBlock*)(Widget.Get());
		RichTextBlock->SetText(NewText);
	}
	else if (Type == "SEditableText")
	{
		SEditableText* EditableText = (SEditableText*)(Widget.Get());
		EditableText->SetText(NewText);
	}
	else if (Type == "SEditableTextBox")
	{
		SEditableTextBox* EditableTextBox = (SEditableTextBox*)(Widget.Get());
		EditableTextBox->SetText(NewText);
	}
	else if (Type == "SMultiLineEditableText")
	{
		SMultiLineEditableText* MultiLineEditableText = (SMultiLineEditableText*)(Widget.Get());
		MultiLineEditableText->SetText(NewText);
	}
	else if (Type == "SMultiLineEditableTextBox")
	{
		SMultiLineEditableTextBox* MultiLineEditableTextBox = (SMultiLineEditableTextBox*)(Widget.Get());
		MultiLineEditableTextBox->SetText(NewText);
	}
	// 如果不是使用 UE 自带 Text SWidget，尝试通过 UWidget 来设置文本
	else
	{
		auto MetaData = Widget->GetMetaData<FReflectionMetaData>();
		if (MetaData.IsValid())
		{
			auto WidgetObject = MetaData->SourceObject;
			// 目前看到的 UE4 原生的文本框类型，都带有对应的可以反射的 SetText 函数
			// 因此使用反射获取对应的函数
			UFunction* SetText = WidgetObject->FindFunction("SetText");
			if (SetText)
			{
				struct SetText_Func_Params   //定义一个结构用来包装参数和返回值
				{
					FText InText;
				};
				SetText_Func_Params Params;
				Params.InText = FText::FromString(Text);

				WidgetObject->ProcessEvent(SetText, &Params);
			}
		}
	}

	// 设置焦点，以便能够正常触发 OnCommit 事件
	SlateApplication.ClearUserFocus(0, EFocusCause::Mouse);
}

bool UUAutoFunctionLibrary::SetScrollOffset(TSharedPtr<SWidget> Widget, float Value)
{


	FString Type = Widget->GetType().ToString();

	if (Type == "SScrollBox" || Type == "SEMScrollBox")
	{
		SScrollBox* ScrollBox = static_cast<SScrollBox*>(Widget.Get());
		if (ScrollBox)
		{
			float End = ScrollBox->GetScrollOffsetOfEnd();
			UE_LOG(LogUAuto, Warning, TEXT("End is %f"), End);
			ScrollBox->SetScrollOffset(Value);
			return true;
		}
	}
	else if(Type == "ListViewT<ItemType>")
	{
		STableViewBase* TableViewBase = static_cast<STableViewBase*>(Widget.Get());

		if (TableViewBase)
		{
			TableViewBase->SetScrollOffset(Value);
			return true;
		}
	}
	else if (Type == "TileViewT<ItemType>")
	{
		STableViewBase* TableViewBase = static_cast<STableViewBase*>(Widget.Get());

		if (TableViewBase)
		{
			TableViewBase->SetScrollOffset(Value);
			return true;
		}
	}

	return false;
}

void UUAutoFunctionLibrary::TapScreen(FVector2D Cursor, FString Action)
{
#if WITH_EDITOR || PLATFORM_WINDOWS || PLATFORM_MAC

	FSlateApplication& SlateApplication = FSlateApplication::Get();
	SlateApplication.SetCursorPos(Cursor);

	FKey Key = EKeys::LeftMouseButton;
	if (Action == "down")
	{
		if (PressedKeys.Contains(Key))
		{
			return;
		}

		GEngine->AddOnScreenDebugMessage(-1, 5, FColor::Red, "Mouse Down");
		PressedKeys.Add(Key);
		FPointerEvent PointerDownEvent(
			0,
			0,
			Cursor,
			Cursor,
			PressedKeys,
			EKeys::LeftMouseButton,
			0.0f,
			FModifierKeysState());


		// 获取 widget path
		FWidgetPath WidgetUnderCursor = SlateApplication.LocateWindowUnderMouse(
			PointerDownEvent.GetScreenSpacePosition(),
			SlateApplication.GetInteractiveTopLevelWindows(),
			false,
			0);

		// 处理事件
		FReply Reply = SlateApplication.RoutePointerDownEvent(WidgetUnderCursor, PointerDownEvent);
	}
	else if (Action == "up")
	{
		if (PressedKeys.Contains(Key))
		{
			PressedKeys.Remove(Key);
		}

		FPointerEvent PointerUpEvent(
			0,
			0,
			Cursor,
			Cursor,
			PressedKeys,
			EKeys::LeftMouseButton,
			0.0f,
			FModifierKeysState());

		// 获取 widget path
		FWidgetPath WidgetUnderCursor = SlateApplication.LocateWindowUnderMouse(
			PointerUpEvent.GetScreenSpacePosition(),
			SlateApplication.GetInteractiveTopLevelWindows(),
			false,
			0);

		GEngine->AddOnScreenDebugMessage(-1, 5, FColor::Red, "Mouse Up");
		// 处理事件
		FReply Reply = SlateApplication.RoutePointerUpEvent(WidgetUnderCursor, PointerUpEvent);
	}


#elif PLATFORM_ANDROID || PLATFORM_IOS || PLATFORM_OPENHARMONY

	FSlateApplication& SlateApplication = FSlateApplication::Get();
	if (Action == "down")
	{

		GEngine->AddOnScreenDebugMessage(-1, 5, FColor::Red, "Touch Down");
		FPointerEvent PointerDownEvent(
			0,
			0,
			Cursor,
			Cursor,
			1,
			true);

		// 获取 widget path
		FWidgetPath WidgetUnderCursor = SlateApplication.LocateWindowUnderMouse(
			PointerDownEvent.GetScreenSpacePosition(),
			SlateApplication.GetInteractiveTopLevelWindows(),
			false,
			0);

		// 处理事件
		FReply Reply = SlateApplication.RoutePointerDownEvent(WidgetUnderCursor, PointerDownEvent);
	}
	else if (Action == "up")
	{
		GEngine->AddOnScreenDebugMessage(-1, 5, FColor::Red, "Touch Up");
		FPointerEvent PointerUpEvent(
			0,
			0,
			Cursor,
			Cursor,
			0,
			true);


		// 获取 widget path
		FWidgetPath EmptyWidgetPath;

		// 处理事件
		FReply UpReply = SlateApplication.RoutePointerUpEvent(EmptyWidgetPath, PointerUpEvent);
	}

#endif

}

void UUAutoFunctionLibrary::ClickScreen(FVector2D Cursor, float Delay, bool right)
{
	
	//FTimerDelegate OnMouseUpDelegate;
	//OnMouseUpDelegate.BindLambda([](FVector2D Cursor) {
	//	GEngine->AddOnScreenDebugMessage(-1, 5, FColor::Red, "Mouse Up");
	//	FSlateApplication::Get().OnMouseUp(EMouseButtons::Left, Cursor);
	//	}, Cursor);
	//UWorld* World = UUAutoCore::Instance()->GetGameWorld();
	//if (Delay==0)
	//{
	//	Delay = 0.05;
	//}
	//World->GetTimerManager().SetTimer(UUAutoFunctionLibrary::UAutoTimerHandle, OnMouseUpDelegate, Delay, false);
	if (right)
	{
		FSlateApplication::Get().OnMouseDown(GEngine->GameViewport->GetWindow()->GetNativeWindow(), EMouseButtons::Right, Cursor);
		FPlatformProcess::Sleep(Delay);
		FSlateApplication::Get().OnMouseUp(EMouseButtons::Right, Cursor);
	}
	else
	{
		FSlateApplication::Get().OnMouseDown(GEngine->GameViewport->GetWindow()->GetNativeWindow(), EMouseButtons::Left, Cursor);
		FPlatformProcess::Sleep(Delay);
		FSlateApplication::Get().OnMouseUp(EMouseButtons::Left, Cursor);
	}

//#if WITH_EDITOR || PLATFORM_WINDOWS || PLATFORM_MAC
//
//	FSlateApplication& SlateApplication = FSlateApplication::Get();
//	SlateApplication.SetCursorPos(Cursor);
//	FKey Key = EKeys::LeftMouseButton;
//	PressedKeys.Empty();
//	PressedKeys.Add(Key);
//	FPointerEvent PointerDownEvent(0,0,Cursor,Cursor,PressedKeys,EKeys::LeftMouseButton,0.0f,FModifierKeysState());
//
//	// 获取 widget path
//	FWidgetPath WidgetUnderCursor = SlateApplication.LocateWindowUnderMouse(
//		PointerDownEvent.GetScreenSpacePosition(),
//		SlateApplication.GetInteractiveTopLevelWindows(),
//		false,
//		0);
//
//	// 处理事件
//	SlateApplication.RoutePointerDownEvent(WidgetUnderCursor, PointerDownEvent);
//	FPlatformProcess::Sleep(Delay);
//	SlateApplication.RoutePointerUpEvent(WidgetUnderCursor, PointerDownEvent);
//
//
//#elif PLATFORM_ANDROID || PLATFORM_IOS
//
//	FSlateApplication& SlateApplication = FSlateApplication::Get();
//	FPointerEvent PointerDownEvent(0,0,Cursor,Cursor,1,true);
//
//	// 获取 widget path
//	FWidgetPath WidgetUnderCursor = SlateApplication.LocateWindowUnderMouse(
//		PointerDownEvent.GetScreenSpacePosition(),
//		SlateApplication.GetInteractiveTopLevelWindows(),
//		false,
//		0);
//	FWidgetPath EmptyWidgetPath;
//	
//	FPointerEvent PointerUpEvent(0,0,Cursor,Cursor,0,true);
//	
//	// 处理事件
//	SlateApplication.RoutePointerDownEvent(WidgetUnderCursor, PointerDownEvent);
//	FPlatformProcess::Sleep(Delay);
//	SlateApplication.RoutePointerUpEvent(EmptyWidgetPath, PointerUpEvent);
//
//#endif

}

bool UUAutoFunctionLibrary::PositionInRect(const FGeometry& geometry, float x, float y)
{
	FVector2D Position = geometry.GetAbsolutePosition();
	FVector2D Size = geometry.GetAbsoluteSize();

	if (x >= Position.X && y >= Position.Y && x <= (Position.X + Size.X) && y <= (Position.Y + Size.Y))
	{
		return true;
	}
	return false;
}

const UWidget* UUAutoFunctionLibrary::FindUWidgetObjectByPos(float x, float y)
{
	auto world = GEngine->GameViewport->Viewport->GetSizeXY();
	float GeometryX = x * world.X;
	float GeometryY = y * world.Y;
	UWidget* ContainPosWidget = nullptr;

	UUAutoCore::Instance()->GetGameWorld();

	for (TObjectIterator<UUserWidget> Itr; Itr; ++Itr)
	{
		UUserWidget* UserWidget = *Itr;

		if (UserWidget == nullptr || !UserWidget->GetIsVisible() || UserWidget->WidgetTree == nullptr) {
			UE_LOG(LogUAuto, Log, TEXT("UUserWidget Iterator get a null(unvisible) UUserWidget"));
			continue;
		}

		UserWidget->WidgetTree->ForEachWidgetAndDescendants([&ContainPosWidget, this, GeometryX, GeometryY](UWidget* WidgetPtr) {
			if (WidgetPtr == nullptr || !WidgetPtr->IsVisible()) {
				return;
			}
			const FGeometry geometry = WidgetPtr->GetCachedGeometry();

			if (this->PositionInRect(geometry, GeometryX, GeometryY))
			{
				ContainPosWidget = WidgetPtr;
				return;
			}
			});
		}
	return ContainPosWidget;
}


void UUAutoFunctionLibrary::POSTSendData(FString SendData, FString api) {

	//创建Http 请求
	TSharedRef<IHttpRequest, ESPMode::ThreadSafe> HttpRequest = FHttpModule::Get().CreateRequest();

	//设置Header
	HttpRequest->SetHeader("Content-Type", "application/json;charset=UTF-8");

	HttpRequest->SetVerb("POST");
	//设置请求地址
	HttpRequest->SetURL(UrlPath+"game_control/"+ api);
	//设置请求发送的数据
	HttpRequest->SetContentAsString(SendData);

	//绑定回调
	//HttpRequest->OnProcessRequestComplete().BindUObject(this, &UUAutoFunctionLibrary::ProcessRequestComplete);
	//发送请求
	HttpRequest->ProcessRequest();
}

void UUAutoFunctionLibrary::InputKey(FString name, FString type,bool CPlayer) {
	if (CPlayer)
	{
		UWorld* World = UUAutoCore::Instance()->GetGameWorld();
		if (World) {
			APlayerController* playerController = UGameplayStatics::GetPlayerController(World, 0);
			if (playerController)
			{
				EInputEvent event = IE_Pressed;
				if (type == "press")
					event = IE_Pressed;
				else if (type == "release")
					event = IE_Released;
				playerController->InputKey(FKey(*name), event, 1, false);
				if (type == "click")
				{
					FPlatformProcess::Sleep(0.01);
					playerController->InputKey(FKey(*name), IE_Released, 1, false);
				}
			}
		
		}
	}
	else {
		int32 InputKeyCode = 0;
		const uint32* KeyCode;
		const uint32* CharCode;
		FInputKeyManager::Get().GetCodesFromKey(FKey(*name), KeyCode, CharCode);
		if (KeyCode)
		{
			InputKeyCode = static_cast<int32>(*KeyCode);
		}
		if (CharCode)
		{
			InputKeyCode = static_cast<int32>(*CharCode);
		}
		if (type == "press")
			FSlateApplication::Get().OnKeyDown(InputKeyCode, InputKeyCode, false);
		else if (type == "release")
			FSlateApplication::Get().OnKeyUp(InputKeyCode, InputKeyCode, false);
		if (type == "click") {
			FSlateApplication::Get().OnKeyDown(InputKeyCode, InputKeyCode, false);
			FSlateApplication::Get().OnKeyUp(InputKeyCode, InputKeyCode, false);
		}
	}
	
}

void UUAutoFunctionLibrary::InputAxis(FString name, FString value) {
	UWorld* World = UUAutoCore::Instance()->GetGameWorld();
	if (World) {
		APlayerController* playerController = UGameplayStatics::GetPlayerController(World, 0);
		if (playerController)
		{
			float delta = FCString::Atof(*value);
			if (name == "MouseY")
			{
				playerController->InputAxis(EKeys::MouseY, delta, 0.1, 1, false);
			}
			else
			{
				playerController->InputAxis(EKeys::MouseX, delta, 0.1, 1, false);
			}
		}

	}
}

//基于反射调用Api 待完善
FString UUAutoFunctionLibrary::callRegister(FName& funcname)
{
	UClass* ActorRef = FindObject<UClass>((UObject*)ANY_PACKAGE, *FString("MyObject"));
	if (ActorRef)
	{
		UFunction* func = ActorRef->FindFunctionByName(funcname);
		if (func != nullptr)
		{
			ActorRef->ProcessEvent(func, NULL);
			UE_LOG(LogUAuto, Log, TEXT("ProcessEvent Success!: %s"), *funcname.GetPlainNameString());
			return "Success";

		}
	}
	return "Null";

}
