// Fill out your copyright notice in the Description page of Project Settings.


#include "ScenePerfCheck.h"
#include "Particles/ParticleSystemManager.h"
#include "Kismet/KismetRenderingLibrary.h"
#include "GameFunctionLibrary.h"
#include "GameFramework/Character.h"
#include "GameFramework/CheatManager.h"
#include "RHI.h"
#include <AI/EMRecastNavMesh.h>
#include <UObject/ConstructorHelpers.h>
#include "Materials/MaterialInstanceDynamic.h"


ScenePerfCheck* ScenePerfCheck::Get()
{
    static TUniquePtr<ScenePerfCheck> Instance = MakeUnique<ScenePerfCheck>();
    return Instance.Get();
}


void ScenePerfCheck::Start()
{
    if (!Is_Running)
    {
        ReportPath = FPaths::ProfilingDir();
       /* ReportPath = FPaths::Combine(FPaths::ProjectSavedDir(), FGuid::NewGuid().ToString());
        if (!FPaths::DirectoryExists(ReportPath))
        {
            FPlatformFileManager::Get().GetPlatformFile().CreateDirectoryTree(*ReportPath);
        }*/
        LocationOutPoints.Empty();
        LocationIndex = 0;
        RotationIndex = 0;
        CurrentFrameDelay = FrameInterval;
        UWorld* World = UUAutoCore::Instance()->GetGameWorld();
        PlayerController = UGameplayStatics::GetPlayerController(World, 0);
        

        if (!PlayerController)
        {
            UE_LOG(LogUAuto, Log, TEXT("获取控制器失败"));
            Is_Running = false;
            return ;
        }
        
        ACharacter* CharacterOwner = PlayerController->GetCharacter();
        if (CharacterOwner == nullptr) {
            Is_Running = false;
            return;
        }

        //开启幽灵模式
        PlayerController->CheatManager->Ghost();
            
        AEMRecastNavMesh* NavData = Cast<AEMRecastNavMesh>(FNavigationSystem::GetNavDataForActor(*CharacterOwner));
        if (NavData ==nullptr)
        {
            UE_LOG(LogUAuto, Log, TEXT("获取导航系统失败"));
            return ;
        }
        //获取导航bounds
        FBox NavBounds = NavData->GetBounds();
        FVector Min = NavBounds.Min;
        FVector Max = NavBounds.Max;
        
        FVector Extent(0, 0, Max.Z - Min.Z);
        bool StartLeft = true;
        FNavLocation NavLocation;
        //获取所有需要的点
        for (float X = Min.X; X <= Max.X; X += DistanceIntervals)
        {
            for (float Y = Min.Y; Y <= Max.Y; Y += DistanceIntervals)
            {
                float RY = Y;
                if (StartLeft) { RY = Max.Y - Y + Min.Y; }
                for (float H = Min.Z; H <= Max.Z; H += 500)
                {
                    if (NavData->ProjectPointConsiderZAxis(FVector(X, RY, H), NavLocation, 300, nullptr))
                    {
                        NavLocation.Location.Z += 180;
                        LocationOutPoints.Add(NavLocation.Location);
                        break;
                    }
                }
            }
            StartLeft = !StartLeft;
        }
        //UKismetSystemLibrary::ExecuteConsoleCommand(UUAutoCore::Instance()->GetGameWorld(), "EM.BlockOnLevelStreaming 1");
        ReportContent = "Location,Rotation,FPS,RenderThreadTime,GameThreadTime,FrameTime,RHITTime,NiagaraNumSystems,NiagaraNumParticles,NiagaraNumMeshVerts,NiagaraIndirectDraws,RHITriangles,RHIDrawPrimitiveCalls,MeshDrawCalls,SceneLights,RHIDrawCalls,RHIPrimitivesDrawn\n";
        //FString::Printf(TEXT("%.1f_%.1f_%.1f,%.1f_%.1f_%.1f,%s\n"), Min.X, Min.Y, Min.Z, Max.X, Max.Y, Max.Z, *World->GetMapName())
        ViewportClient = World->GetGameViewport();
        GEngine->ExecEngineStat(World, ViewportClient, TEXT("Unit -nodisplay"));
        GEngine->ExecEngineStat(World, ViewportClient, TEXT("Niagara -nodisplay"));
        GEngine->ExecEngineStat(World, ViewportClient, TEXT("RHI -nodisplay"));
        GEngine->ExecEngineStat(World, ViewportClient, TEXT("SceneRendering -nodisplay"));
        GEngine->ExecEngineStat(World, ViewportClient, TEXT("Particles -nodisplay"));
        Is_Running = true;
    }

}


void ScenePerfCheck::Stop()
{
    if (Is_Running)
    {
        Is_Running = false;
        //UKismetSystemLibrary::ExecuteConsoleCommand(UUAutoCore::Instance()->GetGameWorld(), "EM.BlockOnLevelStreaming 0");
        //关闭幽灵模式
        PlayerController->CheatManager->Walk();
        SaveReport();
        ReportContent = "";
        UWorld* World = UUAutoCore::Instance()->GetGameWorld();
        GEngine->ExecEngineStat(World, ViewportClient, TEXT("Unit"));
        GEngine->ExecEngineStat(World, ViewportClient, TEXT("Niagara"));
        GEngine->ExecEngineStat(World, ViewportClient, TEXT("RHI"));
        GEngine->ExecEngineStat(World, ViewportClient, TEXT("SceneRendering"));
        GEngine->ExecEngineStat(World, ViewportClient, TEXT("Particles"));
        
    }

}

void ScenePerfCheck::SaveReport()
{
    //保存数据
    FString inpath = FDateTime::Now().ToString(TEXT("%Y%m%d_%H%M%S"))+ FString::Printf(TEXT("_%s_ScenePerfData.csv"), *UUAutoCore::Instance()->GetGameWorld()->GetMapName());
    ReportPath = FPaths::Combine(ReportPath, inpath);
    FFileHelper::SaveStringToFile(ReportContent, *ReportPath, FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM);
}

void ScenePerfCheck::Tick(float DeltaTime)
{
    if (!Is_Running) return;
    
    CumulativeTime += DeltaTime;
    ++FrameCount;
    if (FrameCount >= FrameInterval+1) // 取固定帧数为FrameInterval帧
    {
        FPS = FrameCount / CumulativeTime;
        CumulativeTime = 0;
        FrameCount = 0;
    }
    //等待缓冲帧数
    if (WaitFrame > 1)
    {
        WaitFrame--;
        return;
    }
    if (CurrentFrameDelay == FrameInterval)
    {
        if (!Move())//旋转视角或者坐标
        {
            return;
        }
    }

    if (CurrentFrameDelay == 0)
    {
        //记录性能数据
        Record();
        //增加旋转位置
        RotationIndex++;
        //重置掉间隔
        CurrentFrameDelay = FrameInterval;
        return;
    }
#if STATS
    else if (CurrentFrameDelay <= 1)
    {
        NumPrimitivesDrawn = GNumPrimitivesDrawnRHI[0];
        NumDrawCalls = GNumDrawCallsRHI[0];
    }
#endif
    if (CurrentFrameDelay != 0)
    {
        CurrentFrameDelay--;
    }
}
bool ScenePerfCheck::Move()
{
    if (LocationIndex==0 || RotationIndex>= RotationCount)//当旋转结束后 移动位置并重置掉旋转
    {
        if ( LocationIndex < LocationOutPoints.Num())
        {
            //这里移动一下loc位置
            PlayerController->GetPawn()->SetActorLocation(LocationOutPoints[LocationIndex]);
            LocationIndex++;
            RotationIndex = 0;
            WaitFrame = 40;
        }
        else
        {
            //这里应该遍历结束了
            Stop();
            UE_LOG(LogUAuto, Log, TEXT("结束了"));
            return false;
        }
    }
    //这里旋转一下视角
    PlayerController->SetControlRotation(FRotator(25,RotationIndex*90,0));
    return true;
}

void ScenePerfCheck::Record()
{
    //获取 性能数据并记录一下
    if (ViewportClient != nullptr) {
        TArray<double> StatItemData;
        StatItemData.Init(0.0, 14);
        const FStatUnitData* statUnitData = ViewportClient->GetStatUnitData(); // 来自stat unit命令的计算结果
        StatItemData[0] = statUnitData->RawRenderThreadTime;
        StatItemData[1] = statUnitData->RawGameThreadTime;
        StatItemData[2] = statUnitData->RawFrameTime;
        StatItemData[3] =  statUnitData->RawRHITTime;
        
#if STATS
        
        FGameThreadStatsData* ViewData = FLatestGameThreadStatsData::Get().Latest;
        
        if (ViewData != nullptr) {
            double StatData = 0.0;
            FString StatName = "";
            for (int n = 0; n < ViewData->GroupNames.Num(); n++) {
                const FActiveStatGroupInfo& StatGroup = ViewData->ActiveStatGroups[n];
                if (ViewData->GroupNames[n] == "STATGROUP_Niagara") {
                    for (int m = 0; m < StatGroup.CountersAggregate.Num(); m++) {
                        StatData= StatGroup.CountersAggregate[m].GetValue_double(EComplexStatField::IncAve);
                        StatName = StatGroup.CountersAggregate[m].GetShortName().ToString();
                        if (StatName == TEXT("STAT_NiagaraNumSystems")) {
                            StatItemData[4] = StatData;
                        }
                        else if (StatName == TEXT("STAT_NiagaraNumParticles")) {
                            StatItemData[5] = StatData;
                        }
                        else if (StatName == TEXT("STAT_NiagaraNumMeshVerts")) {
                            StatItemData[6] = StatData;
                        }
                        else if (StatName == TEXT("STAT_NiagaraIndirectDraws")) {
                            StatItemData[7] = StatData;
                        }
                    }
                }
                if (ViewData->GroupNames[n] == "STATGROUP_RHI") {

                    for (int m = 0; m < StatGroup.CountersAggregate.Num(); m++) {
                        StatName = StatGroup.CountersAggregate[m].GetShortName().ToString();
                        StatData = StatGroup.CountersAggregate[m].GetValue_double(EComplexStatField::IncAve);
                        if (StatName == TEXT("STAT_RHITriangles"))
                        {
                            StatItemData[8] = StatData;
                        }
                        else if (StatName == TEXT("STAT_RHIDrawPrimitiveCalls")) {
                            StatItemData[9] = StatData;
                        }
                    }
                }
                if (ViewData->GroupNames[n] == "STATGROUP_SceneRendering") {

                    for (int m = 0; m < StatGroup.CountersAggregate.Num(); m++) {
                        StatName = StatGroup.CountersAggregate[m].GetShortName().ToString();
                        StatData = StatGroup.CountersAggregate[m].GetValue_double(EComplexStatField::IncAve);
                        if (StatName == TEXT("STAT_MeshDrawCalls"))
                        {
                            StatItemData[10] = StatData;
                        }
                        else if (StatName == TEXT("STAT_SceneLights")) {
                            StatItemData[11] = StatData;
                        }
                    }
                }
                
            }
        }

        StatItemData[12] = NumDrawCalls;
        StatItemData[13] = NumPrimitivesDrawn;
        
#endif
        FString Result;
        for (int32 Index = 0; Index < StatItemData.Num(); ++Index)
        {
            Result += FString::Printf(TEXT("%.2f"), StatItemData[Index]);
            if (Index < StatItemData.Num() - 1)
            {
                Result += TEXT(",");
            }
        }
        //截图
        /*FString ScreenshotName = FString::Printf(TEXT("Screenshot_%s_%d.png"), *FDateTime::Now().ToString(TEXT("%Y%m%d_%H%M%S")), GFrameNumber);
        FString ScreenshotFilePath = FPaths::Combine(ReportPath, ScreenshotName);

        UKismetSystemLibrary::ExecuteConsoleCommand(UUAutoCore::Instance()->GetGameWorld(), "HighResShot 640x360  filename="+ ScreenshotFilePath);*/
        ReportContent.Append(FString::Printf(TEXT("%.1f_%.1f_%.1f,%d,%d,%s\n"), LocationOutPoints[LocationIndex-1].X, LocationOutPoints[LocationIndex-1].Y, LocationOutPoints[LocationIndex-1].Z,RotationIndex * 90, FPS ,*Result));
    }
}

FString ScenePerfCheck::GetReportFile()
{
    return FPaths::ConvertRelativePathToFull(*ReportPath);
}
int ScenePerfCheck::GetProgress()
{
    return LocationOutPoints.Num()- LocationIndex;

}

