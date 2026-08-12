// Fill out your copyright notice in the Description page of Project Settings.

#pragma once

#include "CoreMinimal.h"

/**
 * 
 */
class GAMEAUTOPLUGIN_API UAutoDebugMode
{
public:
	static UAutoDebugMode* Get();
	bool Tick(float DeltaTime, TArray<FString>& Result);

	bool GetCurWidget(TSharedPtr<SWidget>& WidgetPtr);
	bool GetCurWidget(TSharedPtr<SWidget>& WidgetPtr, FVector2D Position);

	FString GetWidgetPath(SWidget* Widget);

	FString Start();

	FString Stop();

protected:
	bool bDebugMode = false;

	bool bIsPressing = false;

	float PressTime = 0.0f;

	float Timedelay = 0.0f;

	TSharedPtr<SWidget> LastWidget;
};
