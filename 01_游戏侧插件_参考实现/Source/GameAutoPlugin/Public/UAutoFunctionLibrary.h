// Fill out your copyright notice in the Description page of Project Settings.

#pragma once

#include "CoreMinimal.h"
#include "Components/Widget.h"
#include "HttpModule.h"
#include "Interfaces/IHttpResponse.h"
#include "UAutoFunctionLibrary.generated.h"
/**
 * 
 */
UCLASS()
class GAMEAUTOPLUGIN_API UUAutoFunctionLibrary : public UObject
{
	GENERATED_BODY()
public:
    static  FString UrlPath;

    static bool NewWays;

    static bool ExcludeNotVisible;

    static void NameAddIndex(FString& Name, const SWidget* Widget, bool IsUserWidget = false);

    static FString GetPath(UWidget* Widget);
    static FString GetPath(SWidget* Widget);

    static AActor* FindActorByIDName(FString IDName);
#if UE_SLATE_WITH_WIDGET_UNIQUE_IDENTIFIER
    static FString GetID(SWidget* Widget);
#endif
    static void TapScreen(FVector2D Cursor, FString Action);

    static void ClickScreen(FVector2D Cursor, float Delay = 0.01f, bool right = false);

    static FString callRegister(FName& funcname);

    bool PositionInRect(const FGeometry& geometry, float x, float y);

    const UWidget* FindUWidgetObjectByPos(float x, float y);
    static void POSTSendData(FString SendData, FString api);
    static void InputKey(FString name, FString type, bool CPlayer=false);
    static void InputAxis(FString name, FString value);
    /**
     * @brief 根据传入文本找到包含文本的文本框控件
     * @param text
     * @return
     */
    static TArray<FString> GetUserWidgetByText(FString text);

    /**
     * @brief 遍历所有控件，并将包含指定文本的文本框控件信息记录下来
     * @param RetWidgetName
     * @param RetWidgetID
     * @param RetWidgetText
     * @param Children
     * @param text
     */
    static void WidgetIterText(TArray<FString>& RetWidgetName, TArray<FString>& RetWidgetID, TArray<FString>& RetWidgetText, TArray<FVector2D>& Center, TArray<int>& Visible, FChildren* Children, FString text);

    static TSharedPtr<SWidget> GetSConstraintCanvaWidget();

    static TSharedPtr<SWidget> FindWidgetByPathBase(FString Path, TSharedPtr<SWidget> StartWidget);

    static TSharedPtr<SWidget> FindWidgetByPath(FString Path);

    static TSharedPtr<SWidget> FindWidgetById(uint32 Id);

    static void TapWidget(TSharedPtr<SWidget> WidgetPtr);

    static TSharedPtr<SWidget> GetChildByNameAndIndex(TSharedPtr<SWidget> Parent, FString SWidgetName);

    /**
     * @brief 尝试从指定的 SWidget 上获取文本，
     * 目前支持 UE4 中 6 个内置文本组件，如果项目中使用了自定义的文本组件，需要在这里进行相应修改，以支持自定义组件
     * @param Widget
     * @param Text FString 引用，获取到的文本将会写入到该参数中
     * @return 获取文本是否成功
     */
    static bool GetText(TSharedPtr<SWidget> Widget, FString& Text);

    /**
     * @brief 尝试在指定的 SWidget 上设置文本，
     * 目前支持 UE4 中 6 个内置文本组件，如果项目中使用了自定义的文本组件，需要在这里进行相应修改，以支持自定义组件
     * @param Widget
     * @param Text 设置的新文本值
     */
    static void SetText(TSharedPtr<SWidget> Widget, FString Text);

    static bool SetScrollOffset(TSharedPtr<SWidget> Widget, float Value);

private:
    static TSet<FKey> PressedKeys;
    static TSharedPtr<SWidget> SConstraintCanvaWidget;
    //static FTimerHandle UAutoTimerHandle;
};
