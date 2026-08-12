// Fill out your copyright notice in the Description page of Project Settings.


#include "CaptureStatData.h"
#include <UAutoCore.h>
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"
#include <Stats/StatsData.h>
#include "Kismet/GameplayStatics.h"
#include <Misc/FileHelper.h>
#include "GameAutoPlugin.h"

CaptureStatData* CaptureStatData::Get()
{
    static TUniquePtr<CaptureStatData> Instance = MakeUnique<CaptureStatData>();
    return Instance.Get();
}

void CaptureStatData::Prepare(TArray<FString> Args)
{
    if (!Is_Running)
    {
        
        UWorld* World = UUAutoCore::Instance()->GetGameWorld();
        ViewportClient = World->GetGameViewport();
        StatItemName.Empty();
        if (ViewportClient != nullptr)
        {
            statUnitData = ViewportClient->GetStatUnitData();
            FrameInterval = FCString::Atoi(*Args[2]);
            if (statUnitData->RawGameThreadTime == 0)
            {
                UKismetSystemLibrary::ExecuteConsoleCommand(World, TEXT("Stat Unit -nodisplay"));
            }
            for (int i = 3; i < Args.Num() - 1; i++)
            {
                StatItemName.Add(Args[i]);
                UKismetSystemLibrary::ExecuteConsoleCommand(World, +TEXT("Stat "+ Args[i] + " -nodisplay"));
            }
        }
    }

}

void CaptureStatData::Start()
{
    if (!Is_Running)
    {
        TimeDifference = 0;
        Is_Running = true;
    }
}

void CaptureStatData::Stop()
{
    if (Is_Running)
    {
        Is_Running = false;
        SaveReport();
        UWorld* World = UUAutoCore::Instance()->GetGameWorld();
        GEngine->ExecEngineStat(World, ViewportClient, TEXT("Unit"));
        for (FString Name : StatItemName)
        {
            GEngine->ExecEngineStat(World, ViewportClient, *Name);
        }
        StatItemName.Empty();
        ReportContent = "";
    }
    
}

void CaptureStatData::SaveReport()
{
    //整理表头
    FString HeaderTable = "";
#if STATS
    FGameThreadStatsData* ViewData = FLatestGameThreadStatsData::Get().Latest;
    FString ShortName = "";
    if (ViewData != nullptr) {
        for (FActiveStatGroupInfo& StatGroup : ViewData->ActiveStatGroups)
        {
            for (FComplexStatMessage StatMessage : StatGroup.CountersAggregate)
            {
                ShortName = StatMessage.GetShortName().ToString();
                HeaderTable += "," + ShortName;
            }
            for (FComplexStatMessage StatMessage : StatGroup.MemoryAggregate)
            {
                ShortName = StatMessage.GetShortName().ToString();
                HeaderTable += "," + ShortName;
            }
            for (FComplexStatMessage StatMessage : StatGroup.FlatAggregate)
            {
                ShortName = StatMessage.GetShortName().ToString();
                HeaderTable += "," + ShortName + "," + ShortName + "_Calls";
            }
            
            
        }
    }
#endif
    ReportContent = "Label,Timestamp,FrameIndex,FrameTime,GameThreadTime,RenderThreadTime,GPUFrameTime,RHITTime,DrawCalls,Primitives" + HeaderTable + "\n" + ReportContent;
    //保存数据
    ReportPath = FPaths::Combine(FPaths::ProfilingDir(), FDateTime::Now().ToString(TEXT("%Y%m%d_%H%M%S_StatData.csv")));
    ReportPath = FPaths::ConvertRelativePathToFull(*ReportPath);
    FFileHelper::SaveStringToFile(ReportContent, * ReportPath, FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM); 
}

void CaptureStatData::Tick(float DeltaTime)
{
    if (Is_Running)
    {
        if (FrameInterval!=0 && GFrameNumber% FrameInterval !=0) return;

        if (ViewportClient != nullptr) { 
            StatItemData.Empty();
#if STATS
            FGameThreadStatsData* ViewData = FLatestGameThreadStatsData::Get().Latest;
            if (ViewData != nullptr) {
                
                for ( FActiveStatGroupInfo& StatGroup : ViewData->ActiveStatGroups)
                {
                    for ( FComplexStatMessage StatMessage: StatGroup.CountersAggregate)
                    {
                        StatItemData.Add(StatMessage.GetValue_double(EComplexStatField::IncMax));
                    }
                    for (FComplexStatMessage StatMessage : StatGroup.MemoryAggregate)
                    {
                        StatItemData.Add(StatMessage.GetValue_double(EComplexStatField::IncMax));
                    }
                    for (FComplexStatMessage StatMessage : StatGroup.FlatAggregate)
                    {
                        StatItemData.Add(FPlatformTime::ToMilliseconds(StatMessage.GetValue_Duration(EComplexStatField::IncMax)));
                        StatItemData.Add(StatMessage.GetValue_CallCount(EComplexStatField::IncMax));
                    }
                    
                }
            }
#endif
            FString Result="";
            for (int32 Index = 0; Index < StatItemData.Num(); ++Index)
            {
                Result +=","+ FString::Printf(TEXT("%.2f"), StatItemData[Index]);
            }
            //计算
            second = FPlatformTime::Seconds();
            if (TimeDifference == 0) {
                TimeDifference = FDateTime::Now().ToUnixTimestamp() - 28800 - static_cast<int>(second);
            }
            statUnitData = ViewportClient->GetStatUnitData(); // 来自stat unit命令的计算结果
            ReportContent.Append(FString::Printf(TEXT("%s,%.3f,%d,%.2f,%.2f,%.2f,%.2f,%.2f,%d,%d%s\n"), *LabelName, second+ TimeDifference, GFrameNumber, statUnitData->RawFrameTime, statUnitData->RawGameThreadTime, statUnitData->RawRenderThreadTime, statUnitData->RawGPUFrameTime[0], statUnitData->RawRHITTime, GNumDrawCallsRHI[0], GNumPrimitivesDrawnRHI[0], *Result));
        }
    }
}

FString CaptureStatData::GetReportFile()
{
    return ReportPath;
}
