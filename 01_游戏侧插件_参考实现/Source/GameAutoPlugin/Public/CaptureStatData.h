// Fill out your copyright notice in the Description page of Project Settings.

#pragma once

#include "CoreMinimal.h"
#include "CoreGlobals.h"
#include "Kismet/GameplayStatics.h"
/**
 * 
 */

class GAMEAUTOPLUGIN_API CaptureStatData
{
protected:
	
	FString ReportPath="";
	TArray<FString> StatItemName;
	bool Is_Running=false;
	int FrameInterval = 1;
	UGameViewportClient* ViewportClient=nullptr;
	
	//TArray<TSharedPtr<FJsonValue>> ReportData;
	FString ReportContent ="";
	//TSharedPtr<TJsonWriter<TCHAR, TCondensedJsonPrintPolicy<TCHAR>>> ReportData;
	int TimeDifference = 0;
	double second = 0;
	const FStatUnitData* statUnitData;
	TArray<double> StatItemData;


public:
	FString LabelName = "null";
	static CaptureStatData* Get();
	//准备采集(开启采集)
	void Prepare(TArray<FString> Args);

	//启动采集
	void Start();


	//停止采集
	void Stop();
	
	//保存数据
	void SaveReport();

	//tick
	void Tick(float DeltaTime);

	//获取保存的文件路径
	FString GetReportFile();


};
