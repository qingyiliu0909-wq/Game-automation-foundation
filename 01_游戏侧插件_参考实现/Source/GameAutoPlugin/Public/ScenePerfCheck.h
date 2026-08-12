// Fill out your copyright notice in the Description page of Project Settings.

#pragma once

#include "CoreMinimal.h"
#include "GameAutoPlugin.h"

class UGameViewportClient;
class APlayerController;
class UNavigationSystemV1;
/**
 * 
 */
class GAMEAUTOPLUGIN_API ScenePerfCheck
{
protected:
	FString ReportPath = "没有数据";
	UGameViewportClient* ViewportClient = nullptr;
	APlayerController* PlayerController = nullptr;
	UNavigationSystemV1* NavSys = nullptr;
	FString ReportContent = "";
	int TimeDifference = 0;
	int WaitFrame = 120;
	int CurrentFrameDelay = 20;
	
	int RotationCount = 4;
	int RotationIndex = 0;


	TArray<FVector> LocationOutPoints;
	int LocationIndex = -1;

	int FrameCount = 0;
	float CumulativeTime = 0;
	int FPS = 0;

	int32 NumPrimitivesDrawn = 0;
	int32 NumDrawCalls = 0;

public:
	int FrameInterval = 20;
	float DistanceIntervals = 1000;

	static ScenePerfCheck* Get();

	bool Is_Running = false;

	//启动采集
	void Start();


	//强制停止采集
	void Stop();

	//保存数据
	void SaveReport();

	//tick
	void Tick(float DeltaTime);

	bool Move();

	void Record();

	//获取保存的文件路径
	FString GetReportFile();

	int GetProgress();

};
